"""Splice a validated proposal into the original bytes and verify the result in memory."""
from difflib import SequenceMatcher
import io
import logging
import re
import zipfile
from xml.parsers import expat
from xml.sax.saxutils import escape

from docx import Document

from editing.body_map import scan
from editing.models import Block, EditCandidate, EditError, OpenedDocument, Proposal
from editing.package import rebuild, sha256

logger = logging.getLogger(__name__)
UNSAFE = "Simplicitor could not apply this change safely. Your document was not changed."
# Paragraph properties a new (non-continuation) paragraph may copy; everything else stays behind.
NEW_PARAGRAPH_PROPERTIES = ("pStyle", "keepNext", "keepLines", "widowControl", "numPr", "pBdr",
                            "shd", "tabs", "spacing", "ind", "contextualSpacing", "jc",
                            "outlineLvl", "rPr")
_TOKEN = re.compile(r"\w+|\s+|[^\w\s]")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text)


def char_formats(block: Block) -> list[bytes]:
    """The w:rPr bytes of each character of the paragraph text."""
    formats: list[bytes] = []
    for run in block.runs:
        formats.extend([run.rpr] * len(run.text))
    return formats


def new_formats(old_text: str, old: list[bytes], new_text: str) -> tuple[list[bytes], tuple[tuple[int, int], ...]]:
    """Formatting per new character and the changed character ranges (for the After highlight)."""
    a, b = _tokens(old_text), _tokens(new_text)
    offsets = [0]
    for token in a:
        offsets.append(offsets[-1] + len(token))
    formats: list[bytes] = []
    changed: list[tuple[int, int]] = []
    for op, a1, a2, b1, b2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        size = sum(len(t) for t in b[b1:b2])
        if op == "equal":
            formats.extend(old[offsets[a1]:offsets[a2]])
            continue
        if op == "delete":
            continue
        if not old:
            source = b""
        elif op == "replace":
            source = old[offsets[a1]]
        else:
            source = old[offsets[a1] - 1] if offsets[a1] > 0 else old[0]
        formats.extend([source] * size)
        if size:
            changed.append((len(formats) - size, len(formats)))
    return formats, tuple(changed)


def _name(prefix: bytes, local: str) -> bytes:
    return prefix + local.encode()


def _runs(prefix: bytes, text: str, formats: list[bytes]) -> bytes:
    out, i = [], 0
    while i < len(text):
        j = i
        while j < len(text) and formats[j] == formats[i]:
            j += 1
        parts = []
        for piece in re.split(r"(\t|\n)", text[i:j]):
            if piece == "\t":
                parts.append(b"<" + _name(prefix, "tab") + b"/>")
            elif piece == "\n":
                parts.append(b"<" + _name(prefix, "br") + b"/>")
            elif piece:
                parts.append(b"<" + _name(prefix, "t") + b' xml:space="preserve">'
                             + escape(piece).encode("utf-8") + b"</" + _name(prefix, "t") + b">")
        out.append(b"<" + _name(prefix, "r") + b">" + formats[i] + b"".join(parts)
                   + b"</" + _name(prefix, "r") + b">")
        i = j
    return b"".join(out)


def _properties(xml: bytes, block: Block, continuation: bool) -> bytes:
    if block.ppr is None:
        return b""
    start, end = block.ppr
    if continuation:
        return xml[start:end]
    kept = [xml[s:e] for tag, s, e in block.ppr_children if tag in NEW_PARAGRAPH_PROPERTIES]
    if not kept:
        return b""
    opening = xml[start:block.ppr_children[0][1]] if block.ppr_children else b""
    return opening + b"".join(kept) + b"</" + _name(block.prefix, "pPr") + b">"


def _paragraph(xml: bytes, block: Block, text: str, continuation: bool) -> tuple[bytes, tuple]:
    prefix = block.prefix
    if continuation:
        opening = block.start_tag
        if opening.endswith(b"/>"):
            opening = opening[:-2].rstrip() + b">"
    else:
        opening = b"<" + _name(prefix, "p") + b">"
    lead = b"".join(m.raw for m in block.markers if m.place == "lead") if continuation else b""
    trail = b"".join(m.raw for m in block.markers if m.place == "trail") if continuation else b""
    formats, changed = new_formats(block.text, char_formats(block), text)
    body = _runs(prefix, text, formats)
    return (opening + _properties(xml, block, continuation) + lead + body + trail
            + b"</" + _name(prefix, "p") + b">"), changed


def _splice(opened: OpenedDocument, first: int, last: int, proposal: Proposal):
    xml = opened.xml
    selected = opened.paragraphs[first:last + 1]
    pieces, highlights = [], []
    for k, block in enumerate(selected):
        outputs = [p.text for p in proposal.paragraphs if p.source == k]
        for n, text in enumerate(outputs):
            raw, changed = _paragraph(xml, block, text, continuation=n == 0)
            pieces.append(raw)
            highlights.append(changed)
        if k < len(selected) - 1:
            pieces.append(xml[block.end:selected[k + 1].start])
    start, end = selected[0].start, selected[-1].end
    return xml[:start] + b"".join(pieces) + xml[end:], start, end, tuple(highlights)


def _markers_between(xml: bytes, bookmarks, start: int, end: int) -> list[bytes]:
    return [xml[m.start:m.end] for m in bookmarks if start <= m.start < end]


def _verify(opened: OpenedDocument, assembled: bytes, new_data: bytes, start: int, end: int,
            first: int, selected: int, proposal: Proposal) -> None:
    """The six checks on the packaged candidate; each failure logs only its name."""
    def fail(check: str) -> None:
        logger.warning("Edit candidate failed verification: %s", check)
        raise EditError(UNSAFE)

    old_zip = zipfile.ZipFile(io.BytesIO(opened.data))
    new_zip = zipfile.ZipFile(io.BytesIO(new_data))
    if [i.filename for i in old_zip.infolist()] != [i.filename for i in new_zip.infolist()]:
        fail("entry list")
    if any(old_zip.read(i) != new_zip.read(i.filename)
           for i in old_zip.infolist() if i.filename != opened.part_name):
        fail("other parts")
    # Every later check reads the main part from the package that will be saved.
    new_xml = new_zip.read(opened.part_name)
    if new_xml != assembled:
        fail("packaged main part")
    old = opened.xml
    tail = len(old) - end
    if new_xml[:start] != old[:start] or new_xml[len(new_xml) - tail:] != old[end:]:
        fail("outside bytes")
    try:
        expat.ParserCreate().Parse(new_xml, True)
    except expat.ExpatError:
        fail("well-formed")
    try:
        count = len(Document(io.BytesIO(new_data)).paragraphs)
    except Exception:
        count = -1
    if count != len(opened.paragraphs) - selected + len(proposal.paragraphs):
        fail("paragraph count")
    try:
        blocks, bookmarks = scan(new_xml)
    except EditError:
        fail("rescan")
    outputs = [b for b in blocks if b.kind == "p"][first:first + len(proposal.paragraphs)]
    if ([b.text for b in outputs] != [p.text for p in proposal.paragraphs]
            or any(b.reason for b in outputs)):
        fail("output paragraphs")
    if (_markers_between(old, opened.bookmarks, start, end)
            != _markers_between(new_xml, bookmarks, start, len(new_xml) - tail)):
        fail("bookmark order")
    touched = {m.bookmark_id for m in opened.bookmarks if start <= m.start < end}
    for key in touched:
        before = [m.tag for m in opened.bookmarks if m.bookmark_id == key]
        after = [m.tag for m in bookmarks if m.bookmark_id == key]
        if sorted(before) != sorted(after):
            fail("bookmark pairing")
        if before == ["bookmarkStart", "bookmarkEnd"] and after != before:
            fail("bookmark pairing")


def build_candidate(opened: OpenedDocument, first: int, last: int, proposal: Proposal) -> EditCandidate:
    """Return a verified in-memory candidate or raise EditError; never writes a file."""
    new_xml, start, end, highlights = _splice(opened, first, last, proposal)
    new_data = rebuild(opened.data, opened.part_name, new_xml)
    _verify(opened, new_xml, new_data, start, end, first, last - first + 1, proposal)
    return EditCandidate(new_data, sha256(new_data), opened.path, opened.sha256, first, last,
                         len(proposal.paragraphs), highlights)
