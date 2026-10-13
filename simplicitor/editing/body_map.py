"""Byte-exact map of the main document body: blocks, runs, markers and editability."""
import re
from xml.parsers import expat

from editing.models import Block, BookmarkMarker, EditError, Marker, Run

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
UNREADABLE = "This Word file could not be read."
PREPARE_FAILED = "This document could not be prepared for editing."
STANDARD_ONLY = "Simplicitor can edit standard Word documents (.docx) only."

_P_CHILDREN = {"pPr", "r", "proofErr", "bookmarkStart", "bookmarkEnd"}
_R_CHILDREN = {"rPr", "t", "tab", "br", "lastRenderedPageBreak"}
_BODY_MARKERS = {"bookmarkStart", "bookmarkEnd", "proofErr", "permStart", "permEnd"}
_REASONS = {
    "hyperlink": "a link", "fldSimple": "a field", "fldChar": "a field", "instrText": "a field",
    "ins": "tracked changes", "del": "tracked changes", "moveFrom": "tracked changes",
    "moveTo": "tracked changes", "pPrChange": "tracked changes", "rPrChange": "tracked changes",
    "sdt": "a form field", "commentRangeStart": "a comment", "commentRangeEnd": "a comment",
    "commentReference": "a comment", "drawing": "a picture", "pict": "a picture",
    "object": "a picture", "footnoteReference": "a footnote", "endnoteReference": "a footnote",
    "sectPr": "a section break",
}
_UNSUPPORTED = "content this version cannot edit"
_PREFIX = re.compile(rb"<([^\s/>:]+:)?p[\s/>]")


def tag_end(xml: bytes, start: int) -> int:
    """Index just past the tag that starts at xml[start] == '<'; '>' inside quotes is text."""
    quote = None
    for i in range(start + 1, len(xml)):
        c = xml[i]
        if quote is not None:
            if c == quote:
                quote = None
        elif c in (0x22, 0x27):
            quote = c
        elif c == 0x3E:
            return i + 1
    raise EditError(UNREADABLE)


def _split(name: str) -> tuple[str, str]:
    ns, _, local = name.rpartition(" ")
    return ns, local


def _parse(parser, xml: bytes) -> None:
    try:
        parser.Parse(xml, True)
    except expat.ExpatError:
        raise EditError(UNREADABLE) from None


def _paired_comments(xml: bytes) -> set[str]:
    """IDs with one comment range start followed by one end. Lone markers are point anchors."""
    starts: dict[str, int] = {}
    ends: dict[str, int] = {}
    parser = expat.ParserCreate(namespace_separator=" ")

    def start(name, attrs):
        ns, local = _split(name)
        if ns == W and local in ("commentRangeStart", "commentRangeEnd"):
            seen = starts if local == "commentRangeStart" else ends
            key = attrs.get(W + " id", "")
            if key in seen:
                raise EditError(PREPARE_FAILED)
            seen[key] = len(starts) + len(ends)

    parser.StartElementHandler = start
    _parse(parser, xml)
    for key in starts.keys() & ends.keys():
        if ends[key] < starts[key]:
            raise EditError(PREPARE_FAILED)
    return starts.keys() & ends.keys()


def scan(xml: bytes) -> tuple[tuple[Block, ...], tuple[BookmarkMarker, ...]]:
    """Map every direct child of w:body; raise EditError for unreadable or unbalanced XML."""
    paired = _paired_comments(xml)
    parser = expat.ParserCreate(namespace_separator=" ")
    stack: list[tuple[str, str, int]] = []
    blocks: list[dict] = []
    bookmarks: list[BookmarkMarker] = []
    story = {"field": 0, "comments": set(), "paragraphs": 0}

    def current():
        if blocks and blocks[-1]["kind"] == "p" and "end" not in blocks[-1]:
            return blocks[-1]
        return None

    def read_only(block, reason):
        if block is not None and reason and block["reason"] is None:
            block["reason"] = reason

    def story_open():
        return "a field" if story["field"] else "a comment" if story["comments"] else None

    def start(name, attrs):
        ns, local = _split(name)
        at = parser.CurrentByteIndex
        stop = tag_end(xml, at)
        stack.append((ns, local, at))
        depth = len(stack)
        if depth == 1 and (ns != W or local != "document"):
            raise EditError(STANDARD_ONLY)
        key = attrs.get(W + " id", "")
        if ns == W and local == "fldChar":
            kind = attrs.get(W + " fldCharType")
            story["field"] += 1 if kind == "begin" else -1 if kind == "end" else 0
            if story["field"] < 0:
                raise EditError(PREPARE_FAILED)
        elif ns == W and local == "commentRangeStart" and key in paired:
            story["comments"].add(key)
        elif ns == W and local == "commentRangeEnd":
            story["comments"].discard(key)
        elif ns == W and local in ("bookmarkStart", "bookmarkEnd"):
            bookmarks.append(BookmarkMarker(local, at, stop, key))
        if depth == 3 and stack[1][1] == "body":
            kind = local if ns == W and local in ("p", "tbl", "sdt", "sectPr") else "other"
            if ns == W and local in _BODY_MARKERS:
                kind = "marker"
            block = {"kind": kind, "start": at, "start_tag": xml[at:stop], "reason": None,
                     "runs": [], "markers": [], "ppr": None, "ppr_children": [], "index": -1,
                     "prefix": b""}
            if kind == "p":
                block["index"] = story["paragraphs"]
                story["paragraphs"] += 1
                block["prefix"] = _PREFIX.match(xml, at).group(1) or b""
                read_only(block, story_open())
                if b"xmlns" in xml[at:stop]:
                    read_only(block, _UNSUPPORTED)
            elif kind not in ("marker", "sectPr"):
                block["reason"] = {"tbl": "a table", "sdt": "a form field"}.get(kind, _UNSUPPORTED)
            blocks.append(block)
            return
        block = current()
        if block is None or depth < 4:
            return
        read_only(block, story_open())
        if b"xmlns" in xml[at:stop]:
            read_only(block, _UNSUPPORTED)
        if ns == W and local in _REASONS:
            read_only(block, _REASONS[local])
        if ns == M:
            read_only(block, "an equation")
        parent = stack[-2][1]
        if depth == 4:
            if ns != W or local not in _P_CHILDREN:
                read_only(block, _UNSUPPORTED)
            if local == "r":
                block["runs"].append([b"", []])
            elif local in ("bookmarkStart", "bookmarkEnd"):
                block["markers"].append([local, xml[at:stop], key, attrs.get(W + " name", ""),
                                         len(block["runs"])])
        elif depth == 5 and parent == "pPr":
            block["ppr_children"].append([local, at, at])
        elif depth == 5 and parent == "r":
            if ns != W or local not in _R_CHILDREN:
                read_only(block, _UNSUPPORTED)
            if local == "br" and attrs.get(W + " type", "textWrapping") != "textWrapping":
                read_only(block, "a page break")
            if local == "tab":
                block["runs"][-1][1].append("\t")
            elif local == "br":
                block["runs"][-1][1].append("\n")
        elif depth == 6 and stack[-2][1] == "rPr" and stack[-3][1] == "pPr" and local in ("ins", "del"):
            read_only(block, "tracked changes")

    def end(name):
        ns, local, at = stack.pop()
        start_end = tag_end(xml, at)
        stop = start_end if xml[start_end - 2:start_end] == b"/>" else tag_end(xml, parser.CurrentByteIndex)
        depth = len(stack) + 1
        block = current()
        if depth == 3 and stack[1][1] == "body":
            read_only(block, story_open())
            blocks[-1]["end"] = stop
        elif block is not None:
            if depth == 4 and local == "pPr":
                block["ppr"] = (at, stop)
            elif depth == 5 and stack[-1][1] == "pPr":
                block["ppr_children"][-1][2] = stop
            elif depth == 5 and stack[-1][1] == "r" and local == "rPr":
                block["runs"][-1][0] = xml[at:stop]

    def chars(data):
        block = current()
        if block is not None and len(stack) == 5 and stack[-1][1] == "t" and stack[-2][1] == "r":
            block["runs"][-1][1].append(data)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = chars
    parser.buffer_text = True
    _parse(parser, xml)
    if story["field"] or story["comments"]:
        raise EditError(PREPARE_FAILED)
    return tuple(_freeze(b) for b in blocks), tuple(bookmarks)


def _freeze(block: dict) -> Block:
    if block["kind"] != "p":
        return Block(block["kind"], block["start"], block["end"], reason=block["reason"],
                     start_tag=block["start_tag"])
    runs = tuple(Run(rpr, "".join(text)) for rpr, text in block["runs"])
    markers = [Marker(tag, raw, key, name,
                      "lead" if before == 0 else "trail" if before == len(runs) else "inline")
               for tag, raw, key, name, before in block["markers"]]
    reason = block["reason"]
    inline = [i for i, m in enumerate(markers) if m.place == "inline"]
    if inline:
        first = markers[inline[0]]
        goback = (len(inline) == 2 and inline[1] == inline[0] + 1 and first.tag == "bookmarkStart"
                  and first.name == "_GoBack" and markers[inline[1]].tag == "bookmarkEnd"
                  and markers[inline[1]].bookmark_id == first.bookmark_id)
        if goback:
            # Word's collapsed last-edit position; keeping it with the leading markers keeps order.
            for i in inline:
                m = markers[i]
                markers[i] = Marker(m.tag, m.raw, m.bookmark_id, m.name, "lead")
        elif reason is None:
            reason = "a bookmark inside the text"
    return Block("p", block["start"], block["end"], block["index"], block["start_tag"],
                 block["prefix"], block["ppr"], tuple(tuple(c) for c in block["ppr_children"]),
                 runs, tuple(markers), "".join(r.text for r in runs), reason)


def selection_problem(blocks: tuple[Block, ...], first: int, last: int) -> str | None:
    """None when body paragraphs first..last form a valid selection, else the message."""
    paragraphs = [b for b in blocks if b.kind == "p"]
    if not 0 <= first <= last < len(paragraphs):
        return "Select one or more paragraphs."
    start, end = paragraphs[first].start, paragraphs[last].end
    inside = [b for b in blocks if start <= b.start < end]
    if any(b.kind == "tbl" for b in inside):
        return "A selection cannot cross a table. Select paragraphs on one side of the table."
    if any(b.kind not in ("p", "marker") or b.reason for b in inside):
        return "This range includes a read-only paragraph. Select editable paragraphs on one side of it."
    return None
