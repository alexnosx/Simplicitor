"""Read a .docx once, refuse what the first editor cannot handle, rebuild with one part replaced."""
import hashlib
import io
from math import ceil
from pathlib import Path
import posixpath
import re
import zipfile
from xml.etree import ElementTree

from docx import Document
from docx.table import _Cell
from docx.text.paragraph import Paragraph

from app.config.defaults import (
    EXTRACTION_DOCX_CHARS_PER_PAGE, EXTRACTION_MAX_FILE_BYTES, EXTRACTION_MAX_JOB_PAGES,
)
from editing.body_map import PREPARE_FAILED, STANDARD_ONLY, UNREADABLE, W, scan
from editing.models import EditError, OpenedDocument

_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
_OFFICE_DOCUMENT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
_SETTINGS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings"
_SIGNATURE_ORIGIN = ("http://schemas.openxmlformats.org/package/2006/relationships/"
                     "digital-signature/origin")
_MAIN_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_OLE = b"\xd0\xcf\x11\xe0"
_ON = {"true", "1", "on"}
_OFF = {"false", "0", "off"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rels(zf: zipfile.ZipFile, part: str) -> list[tuple[str, str]]:
    """(type, target part name) for the package ("") or a part; [] when it has none."""
    folder = posixpath.dirname(part)
    name = posixpath.join(folder, "_rels", posixpath.basename(part) + ".rels") if part else "_rels/.rels"
    if name not in zf.namelist():
        return []
    out = []
    for rel in ElementTree.fromstring(zf.read(name)).iter(f"{{{_REL}}}Relationship"):
        if rel.get("TargetMode") == "External":
            continue
        target = rel.get("Target", "")
        full = target[1:] if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
        out.append((rel.get("Type", ""), full))
    return out


def _on(element, attribute: str = "val", absent: bool = True) -> bool:
    """OOXML on/off value of element's w:<attribute>; an absent attribute gives `absent`."""
    value = element.get(f"{{{W}}}{attribute}")
    if value is None:
        return absent
    return value.lower() in _ON


def _settings_flags(zf: zipfile.ZipFile, main: str) -> tuple[bool, bool]:
    """(document protection enforced, track changes on) from the settings part."""
    targets = [t for kind, t in _rels(zf, main) if kind == _SETTINGS]
    if not targets or targets[0] not in zf.namelist():
        return False, False
    root = ElementTree.fromstring(zf.read(targets[0]))
    protection = root.find(f"{{{W}}}documentProtection")
    track = root.find(f"{{{W}}}trackRevisions")
    # Word treats an omitted enforcement attribute as enforced; keep that conservative reading.
    enforced = protection is not None and _on(protection, "enforcement", absent=True)
    return enforced, track is not None and _on(track)


def _check_package(path: Path, data: bytes) -> tuple[zipfile.ZipFile, str]:
    if path.suffix.lower() != ".docx" or data[:4] == _OLE:
        raise EditError("Choose a Word document (.docx). Password-protected files cannot be edited.")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
    except (zipfile.BadZipFile, OSError):
        raise EditError(UNREADABLE) from None
    if len(names) != len(set(names)) or any(i.flag_bits & 0x1 for i in zf.infolist()):
        raise EditError(UNREADABLE)
    try:
        mains = [t for kind, t in _rels(zf, "") if kind == _OFFICE_DOCUMENT]
        types = ElementTree.fromstring(zf.read("[Content_Types].xml"))
    except (KeyError, ElementTree.ParseError):
        raise EditError(UNREADABLE) from None
    if len(mains) != 1 or mains[0] not in names:
        raise EditError(STANDARD_ONLY)
    main = mains[0]
    overrides = {o.get("PartName", "").lstrip("/"): o.get("ContentType")
                 for o in types.iter(f"{{{_CT}}}Override")}
    if overrides.get(main) != _MAIN_TYPE:
        raise EditError(STANDARD_ONLY)
    if (any(n.startswith("_xmlsignatures/") for n in names)
            or any(kind == _SIGNATURE_ORIGIN for kind, _ in _rels(zf, ""))):
        raise EditError("This document is digitally signed. Editing would break the signature.")
    return zf, main


def _encoding_ok(xml: bytes) -> bool:
    if xml.startswith(b"\xef\xbb\xbf"):
        xml = xml[3:]
    if not xml.startswith(b"<?xml"):
        return not xml.startswith((b"\xff\xfe", b"\xfe\xff"))
    declared = re.match(rb"<\?xml[^>]*encoding=[\"']([^\"']+)[\"']", xml)
    return declared is None or declared.group(1).lower() in (b"utf-8", b"utf8")


def open_document(path: Path) -> OpenedDocument:
    """Read the file once and return its map; raise EditError with a plain message."""
    path = Path(path)
    try:
        if path.stat().st_size > EXTRACTION_MAX_FILE_BYTES:
            raise EditError("This document is larger than 50 MiB and cannot be edited.")
        data = path.read_bytes()
    except OSError:
        raise EditError(UNREADABLE) from None
    zf, main = _check_package(path, data)
    try:
        enforced, track = _settings_flags(zf, main)
    except (KeyError, ElementTree.ParseError):
        raise EditError(UNREADABLE) from None
    if enforced:
        raise EditError("This document is protected in Word. Remove the protection in Word first.")
    xml = zf.read(main)
    if not _encoding_ok(xml):
        raise EditError(UNREADABLE)
    blocks, bookmarks = scan(xml)
    try:
        document = Document(io.BytesIO(data))
    except Exception:
        raise EditError(UNREADABLE) from None
    if _page_cost(document) > EXTRACTION_MAX_JOB_PAGES:
        raise EditError("This document is too long to edit (over 300 pages).")
    paragraphs = [b for b in blocks if b.kind == "p"]
    texts = [p.text for p in document.paragraphs]
    if len(texts) != len(paragraphs) or any(
            b.reason is None and b.text != texts[b.index] for b in paragraphs):
        raise EditError(PREPARE_FAILED)
    return OpenedDocument(path.resolve(), data, sha256(data), main, xml, blocks, bookmarks, track)


def _page_cost(document) -> int:
    """Page equivalents counted exactly as extraction.source_readers._read_docx counts them:
    the body and each distinct header/footer part (all variants), paragraph text and the text
    of each physical table cell (its paragraphs joined by newlines)."""
    containers = [document]
    seen = set()
    for section in document.sections:
        for kind in ("header", "footer"):
            for variant in (kind, "first_page_" + kind, "even_page_" + kind):
                container = getattr(section, variant)
                if container.is_linked_to_previous or container.part.partname in seen:
                    continue
                seen.add(container.part.partname)
                containers.append(container)
    chars = 0
    for container in containers:
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                chars += len(block.text)
                continue
            for row in block.rows:
                for tc in row._tr.tc_lst:
                    chars += len("\n".join(p.text for p in _Cell(tc, block).paragraphs))
    return max(1, ceil(chars / EXTRACTION_DOCX_CHARS_PER_PAGE))


def rebuild(data: bytes, part: str, content: bytes) -> bytes:
    """Same entries, order, names, times and compression; only `part` gets new content."""
    source = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for info in source.infolist():
            copy = zipfile.ZipInfo(info.filename, info.date_time)
            copy.compress_type = info.compress_type
            copy.external_attr = info.external_attr
            copy.create_system = info.create_system
            target.writestr(copy, content if info.filename == part else source.read(info))
    return out.getvalue()
