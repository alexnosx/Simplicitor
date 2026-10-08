"""Anchored DOCX body and PDF page readers; never write to source files."""
from math import ceil
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree

import pdfplumber
from docx import Document
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from app.config.defaults import (
    EXTRACTION_DOCX_CHARS_PER_PAGE,
    EXTRACTION_MAX_FILE_BYTES,
    EXTRACTION_MAX_JOB_PAGES,
    EXTRACTION_PDF_MIN_TEXT_CHARS,
)
from extraction.models import Issue, SourceDocument, SourceUnit

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class SourceReadError(ValueError):
    """A safe reader failure, optionally carrying page/structure issues."""

    def __init__(self, message: str, issues: tuple[Issue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues


def read_source(path: Path, source_id: str) -> SourceDocument:
    """Read the complete supported source with stable, job-local anchors."""
    path = Path(path)
    try:
        if path.stat().st_size > EXTRACTION_MAX_FILE_BYTES:
            raise SourceReadError("Input exceeds the 50 MiB per-file limit.")
        if path.suffix.lower() == ".docx":
            document = _read_docx(path, source_id)
        elif path.suffix.lower() == ".pdf":
            document = _read_pdf(path, source_id)
        else:
            raise SourceReadError("Choose a DOCX or text-layer PDF file.")
        if document.page_cost > EXTRACTION_MAX_JOB_PAGES:
            raise SourceReadError("Source exceeds the 300-page job limit.")
        return document
    except SourceReadError:
        raise
    except Exception:
        raise SourceReadError("Could not read source. Check its format or password protection.") from None


def read_sources(paths: Sequence[Path]) -> tuple[SourceDocument, ...]:
    """Read attachments independently and enforce the aggregate page budget."""
    documents = []
    pages = 0
    for index, path in enumerate(paths, 1):
        document = read_source(path, f"source-{index}")
        pages += document.page_cost
        if pages > EXTRACTION_MAX_JOB_PAGES:
            raise SourceReadError("Attachments exceed the 300-page job limit.")
        documents.append(document)
    return tuple(documents)


def _read_docx(path: Path, source_id: str) -> SourceDocument:
    doc = Document(path)
    units, issues = [], []
    paragraph_index = table_index = 0
    for block in doc.iter_inner_content():
        if isinstance(block, Paragraph):
            anchor = f"{source_id}#p:{paragraph_index}"
            units.append(SourceUnit(anchor, block.text, "paragraph", len(units), anchor))
            paragraph_index += 1
        elif isinstance(block, Table):
            for row_index, row in enumerate(block.rows):
                group = f"{source_id}#t:{table_index}:r:{row_index}"
                for cell_index, tc in enumerate(row._tr.tc_lst):
                    cell = _Cell(tc, block)
                    text = "\n".join(p.text for p in cell.paragraphs)
                    anchor = f"{group}:c:{cell_index}"
                    units.append(SourceUnit(anchor, text, "cell", len(units), group))
                    if cell.tables:
                        issues.append(Issue("unsupported_structure", source_id, anchor,
                                            "Nested tables are outside supported body reading."))
            table_index += 1
    if any(list(doc.element.body.iter(_W + tag))
           for tag in ("sdt", "ins", "del", "txbxContent", "altChunk", "fldSimple")):
        issues.append(Issue("unsupported_structure", source_id, source_id,
                            "Content controls, revisions, fields, or embedded text need review."))
    for part in doc.part.package.parts:
        name = str(part.partname)
        if any(token in name for token in ("/header", "/footer", "/footnotes", "/endnotes")):
            root = ElementTree.fromstring(part.blob)
            if any((n.text or "").strip() for n in root.iter(_W + "t")):
                issues.append(Issue("unsupported_structure", source_id, source_id,
                                    "Headers, footers, and notes are outside supported body reading."))
                break
    count = sum(len(u.text) for u in units)
    if not any(u.text.strip() for u in units):
        raise SourceReadError("DOCX has no readable supported body text.", tuple(issues))
    cost = max(1, ceil(count / EXTRACTION_DOCX_CHARS_PER_PAGE))
    return SourceDocument(source_id, path.resolve(), path.name, tuple(units), cost, tuple(issues))


def _read_pdf(path: Path, source_id: str) -> SourceDocument:
    units, issues = [], []
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > EXTRACTION_MAX_JOB_PAGES:
            raise SourceReadError("Source exceeds the 300-page job limit.")
        for number, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            anchor = f"{source_id}#page:{number}"
            units.append(SourceUnit(anchor, text, "page", number - 1, anchor))
            if sum(not ch.isspace() for ch in text) < EXTRACTION_PDF_MIN_TEXT_CHARS:
                issues.append(Issue("unreadable_page", source_id, anchor,
                                    "Page has too little extracted text; coverage is incomplete."))
    if not units or len(issues) == len(units):
        raise SourceReadError("PDF has no usable text layer.", tuple(issues))
    return SourceDocument(source_id, path.resolve(), path.name, tuple(units),
                          len(units), tuple(issues))
