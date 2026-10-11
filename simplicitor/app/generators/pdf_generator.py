# simplicitor/app/generators/pdf_generator.py
"""Render a parsed Word response to PDF with Qt's bundled PDF writer."""
import html
import logging
import os
import tempfile
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

logger = logging.getLogger(__name__)


def _print_document(document: QTextDocument, writer: QPdfWriter) -> None:
    """Separate seam so tests can simulate a write failure."""
    document.print_(writer)


def _validate_pdf(path: Path) -> None:
    """Reject empty or truncated output before it replaces anything."""
    try:
        if not PdfReader(str(path)).pages:
            raise OSError("PDF output has no pages.")
    except PyPdfError as exc:
        raise OSError("PDF output is incomplete.") from exc


def _split_row(line: str) -> list[str]:
    if "|" in line:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]
    return [cell.strip() for cell in line.split("\t")]


def _escape(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


class PdfGenerator:
    """Generates .pdf files from the same parsed structure as WordGenerator."""

    def generate(self, parsed: dict, output_path: Path) -> Path:
        """Write and validate a PDF before replacing the destination."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document = QTextDocument()
        document.setHtml(self._html(parsed))
        descriptor, name = tempfile.mkstemp(prefix=".simplicitor-", suffix=".pdf",
                                            dir=output_path.parent)
        os.close(descriptor)
        temporary = Path(name)
        writer = None
        try:
            writer = QPdfWriter(str(temporary))
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
            _print_document(document, writer)
            writer = None  # Releases the writer and closes the file before validation.
            _validate_pdf(temporary)
            os.replace(temporary, output_path)
        except OSError as exc:
            # Metadata only: the filename can contain confidential prompt words.
            logger.error("PDF generation failed: %s", type(exc).__name__)
            raise
        finally:
            writer = None
            temporary.unlink(missing_ok=True)
        return output_path

    def _html(self, parsed: dict) -> str:
        parts = [f"<h1>{_escape(parsed.get('title', ''))}</h1>"]
        for section in parsed.get("sections", []):
            heading = section.get("heading", "")
            if heading:
                parts.append(f"<h2>{_escape(heading)}</h2>")
            content = section.get("content", "")
            kind = section.get("type", "text")
            if kind == "list":
                items = [ln.strip() for ln in content.replace("\n\n", "\n").split("\n") if ln.strip()]
                parts.append("<ul>" + "".join(f"<li>{_escape(i)}</li>" for i in items) + "</ul>")
            elif kind == "table":
                rows = [_split_row(ln) for ln in content.split("\n") if ln.strip()]
                if rows:
                    head = "".join(f"<th>{_escape(c)}</th>" for c in rows[0])
                    body = "".join("<tr>" + "".join(f"<td>{_escape(c)}</td>" for c in r) + "</tr>"
                                   for r in rows[1:])
                    parts.append("<table border='1' cellspacing='0' cellpadding='4'>"
                                 f"<tr>{head}</tr>{body}</table>")
            else:
                for chunk in content.split("\n\n"):
                    if chunk.strip():
                        parts.append(f"<p>{_escape(chunk.strip())}</p>")
        return "".join(parts)
