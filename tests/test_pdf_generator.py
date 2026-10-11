# tests/test_pdf_generator.py
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.generators import pdf_generator
from app.generators.pdf_generator import PdfGenerator

PARSED = {
    "title": "Q3 status & risks",
    "sections": [
        {"heading": "Summary", "content": "Revenue grew <5%>.\nCosts fell.\n\nOutlook stable.",
         "type": "text"},
        {"heading": "Risks", "content": "Hiring\nSupplier =SUM(A1)", "type": "list"},
        {"heading": "Budget", "content": "Item | Cost\nCloud | 1,200.00", "type": "table"},
    ],
}


def _text(path: Path) -> str:
    raw = " ".join(page.extract_text() for page in PdfReader(str(path)).pages)
    return " ".join(raw.split())


def test_fonts_are_available_for_offscreen_rendering(qapp):
    from PySide6.QtGui import QFontDatabase
    assert QFontDatabase.families()


def test_pdf_contains_title_headings_lists_and_table(qapp, tmp_path):
    out = PdfGenerator().generate(PARSED, tmp_path / "report.pdf")
    assert out == tmp_path / "report.pdf"
    text = _text(out)
    for expected in ("Q3 status & risks", "Summary", "Revenue grew <5%>.", "Costs fell.",
                     "Outlook stable.", "Hiring", "Supplier =SUM(A1)", "Item", "Cost",
                     "Cloud", "1,200.00"):
        assert expected in text


def test_single_line_breaks_stay_line_breaks(qapp, tmp_path):
    out = PdfGenerator().generate(PARSED, tmp_path / "report.pdf")
    lines = [" ".join(line.split()) for line in
             PdfReader(str(out)).pages[0].extract_text().splitlines()]
    assert "Revenue grew <5%>." in lines and "Costs fell." in lines


def test_long_document_spans_pages_and_keeps_the_end(qapp, tmp_path):
    parsed = {"title": "Long", "sections": [
        {"heading": f"Part {i}", "content": "Lorem ipsum dolor sit amet. " * 20, "type": "text"}
        for i in range(60)] + [{"heading": "Closing", "content": "End of document.", "type": "text"}]}
    out = PdfGenerator().generate(parsed, tmp_path / "long.pdf")
    reader = PdfReader(str(out))
    assert len(reader.pages) > 1
    assert "End of document." in " ".join(reader.pages[-1].extract_text().split())


def test_write_failure_leaves_no_file(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(pdf_generator, "_print_document",
                        lambda document, writer: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        PdfGenerator().generate(PARSED, tmp_path / "report.pdf")
    assert list(tmp_path.iterdir()) == []


def test_incomplete_pdf_is_rejected_and_existing_file_kept(qapp, tmp_path, monkeypatch):
    target = tmp_path / "report.pdf"
    target.write_bytes(b"previous")
    monkeypatch.setattr(pdf_generator, "_validate_pdf",
                        lambda path: (_ for _ in ()).throw(OSError("PDF output is incomplete.")))
    with pytest.raises(OSError):
        PdfGenerator().generate(PARSED, target)
    assert target.read_bytes() == b"previous"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["report.pdf"]


def test_validate_pdf_rejects_truncated_bytes(tmp_path):
    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"%PDF-1.4\n1 0 obj\n")
    with pytest.raises(OSError):
        pdf_generator._validate_pdf(broken)


def test_failure_log_contains_no_path(qapp, tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(pdf_generator, "_print_document",
                        lambda document, writer: (_ for _ in ()).throw(OSError("disk full")))
    secret = tmp_path / "Salary review for Jane.pdf"
    with pytest.raises(OSError):
        PdfGenerator().generate(PARSED, secret)
    assert "Jane" not in caplog.text and str(tmp_path) not in caplog.text
