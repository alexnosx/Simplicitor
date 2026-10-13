# scripts/capture_screens.py
"""Render Create new and Edit for Word states offscreen at 1280x800 with synthetic data and an
isolated profile under .venv. Installs nothing and touches no real user folders."""
import os
import sys
from datetime import datetime
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / ".venv" / "screens-profile"
for name, path in (("USERPROFILE", PROFILE), ("APPDATA", PROFILE / "AppData" / "Roaming"),
                   ("LOCALAPPDATA", PROFILE / "AppData" / "Local")):
    path.mkdir(parents=True, exist_ok=True)
    os.environ[name] = str(path)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
sys.path.insert(0, str(ROOT / "simplicitor"))

from PySide6.QtCore import QPoint, QThread  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication, QFrame, QLabel  # noqa: E402

from app.config.styles import input_styles  # noqa: E402
from app.config.settings import Settings  # noqa: E402
from app.config.defaults import (  # noqa: E402
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT,
    BACKGROUND_COLOR,
)
import app.main_window as main_window  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from extraction.models import Candidate, ColumnSpec, Issue, ReviewCell
from extraction.source_readers import read_sources  # noqa: E402
from editing import reading_view  # noqa: E402
from editing.models import Proposal, ProposedParagraph  # noqa: E402
from editing.package import open_document  # noqa: E402
from editing.patch import build_candidate  # noqa: E402

# Synthetic discovery and staged screens are deterministic and send no network requests.
# The real local-Ollama extraction walkthrough is a separate integration check.
_RealClient = main_window.OllamaClient


def _offline_client(*args, **kwargs):
    client = _RealClient(*args, **kwargs)
    client.check_connection = lambda: True
    client.get_models = lambda **kw: ["qwen3:8b"]
    client.get_running_model = lambda **kw: "qwen3:8b"
    client.get_model_params = lambda *a, **k: 8_000_000_000
    return client


main_window.OllamaClient = _offline_client
MainWindow._start_extraction = lambda self, *args, **kwargs: None
_THREADS = ("_ollama_thread", "_extraction_thread", "_generate_thread",
            "_template_thread", "_manipulate_thread", "_edit_thread")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    # Match the existing application entry point, including its input styles.
    app.setStyleSheet(input_styles())

    config = PROFILE / "AppData" / "Roaming" / "Simplicitor"
    config.mkdir(parents=True, exist_ok=True)
    window = MainWindow(Settings(config))
    window.resize(1280, 800)
    window.show()
    screen = window._create_screen
    for _ in range(100):
        app.processEvents()
        if screen._connected:
            break
        QThread.msleep(10)
    assert screen._connected
    screen._folder_label.setText(r"Documents\Simplicitor\Generated")
    checks = []

    def shot(name: str) -> None:
        app.processEvents()
        image = window.grab()
        assert image.width() == 1280 and image.height() == 800
        pixels = image.toImage()
        checked = 0
        for card in window._modes.currentWidget().findChildren(QFrame):
            if card.objectName() != "documentCard" or not card.isVisible():
                continue
            for label in card.findChildren(QLabel):
                if not label.isVisible() or not label.text():
                    continue
                corner = label.mapTo(window, QPoint(label.width() - 2, label.height() - 2))
                assert pixels.pixelColor(corner).name().lower() != BACKGROUND_COLOR.lower(), (
                    "Grey card label background: " + label.text())
                checked += 1
        assert image.save(str(out / name))
        checks.append({"image": name, "card_labels_checked": checked,
                       "grey_label_backgrounds": 0})

    shot("1-create-describe.png")
    screen._prompt_edit.setPlainText(
        "Create a six-slide project update covering progress, risks and next steps.")
    screen.set_file_type("PowerPoint (.pptx)")
    screen.set_template_loaded(True, "business_pitch")
    shot("1b-write-template.png")
    screen.set_route("pull")
    fixtures = ROOT / "tests" / "extraction" / "fixtures"
    screen._prompt_edit.setPlainText("Invoice number, customer, total and due date")
    screen.set_paths((fixtures / "invoice-01.docx", fixtures / "narrative-invoice-02.pdf"))
    screen.set_busy(True, action="inspect")
    screen.show_progress("Reading sources...")
    shot("2a-files-reading.png")
    documents = read_sources(screen._paths)
    screen.show_inspection(documents)
    screen.set_busy(False)
    screen.clear_status()  # MainWindow clears finished progress after the real worker settles.
    shot("2-create-with-files.png")
    problem = Issue("skipped_text_box", documents[0].source_id,
                    documents[0].source_id + "#", "unread")
    partly = (replace(documents[0], issues=(problem,)),) + documents[1:]
    screen.show_inspection(partly)
    shot("2b-files-partly-read.png")
    screen.set_columns((ColumnSpec("c1", "Invoice number", "The invoice number", "text"),
                        ColumnSpec("c2", "Customer", "The customer name", "text"),
                        ColumnSpec("c3", "Total", "The amount to pay", "decimal"),
                        ColumnSpec("c4", "Due date", "The payment due date", "date")))
    shot("3-choose-columns.png")
    screen.set_busy(True, action="extract")
    screen.show_source_progress(documents[0].source_id, len(documents[0].units),
                                sum(len(doc.units) for doc in documents))
    shot("3b-pull-busy.png")
    screen.set_busy(False)
    cells = (
        ReviewCell(2, 3, "00123", "s", ({"Data cell": "C2", "Record": "source-1",
            "File": "invoice-01.docx", "Field": "Invoice number", "Value": "00123",
            "Quote": "Invoice number: 00123", "Anchor": "source-1#t:0:r:0:c:1",
            "Status": "verified", "Issue": ""},)),
        ReviewCell(2, 5, 12500.0, "n", ({"Data cell": "E2", "Record": "source-1",
            "File": "invoice-01.docx", "Field": "Total", "Value": "12,500.00",
            "Quote": "Gross total: USD 12,500.00", "Anchor": "source-1#p:7",
            "Status": "flagged", "Issue": "sectioned_source"},), "0.00"),
        ReviewCell(2, 4, "Example customer", "s", ({"Data cell": "D2", "Record": "source-1",
            "File": "invoice-01.docx", "Field": "Customer", "Value": "Example customer",
            "Quote": "Customer: Example customer", "Anchor": "source-1#p:1",
            "Status": "verified", "Issue": ""},)),
        ReviewCell(2, 6, datetime(2026, 3, 15), "d", ({"Data cell": "F2", "Record": "source-1",
            "File": "invoice-01.docx", "Field": "Due date", "Value": "15 March 2026",
            "Quote": "Due on 15 March 2026.", "Anchor": "source-1#p:8",
            "Status": "verified", "Issue": ""},), "yyyy-mm-dd"),
    )
    cells = tuple(sorted(cells, key=lambda cell: cell.column))
    # Stage one saved row per selected file; these are UI samples, not model evaluation.
    cells += tuple(replace(cell, row=3, evidence=tuple(dict(
        entry, **{"Data cell": entry["Data cell"][:-1] + "3", "Record": "source-2",
                  "File": documents[1].label, "Anchor": "source-2#page:1",
                  "Status": "verified", "Issue": ""}) for entry in cell.evidence))
                   for cell in cells)
    screen.show_inspection(documents)
    candidate = Candidate("job", PROFILE / "candidate.xlsx", screen._paths,
                          (Issue("flagged_field", "source-1", "E2", "review"),
                           Issue("request_failed", "source-1", "source-1#p:9", "reading")))
    screen.show_candidate(candidate, cells)
    assert screen._grid.rowCount() == len(candidate.source_paths)
    screen._grid.setCurrentCell(0, 3)
    screen._grid.clearSelection()  # Keep the evidence visible and show its yellow review fill.
    shot("4-review-and-save.png")
    clean_cells = tuple(replace(cell, evidence=tuple(
        dict(entry, Status="verified", Issue="") for entry in cell.evidence)) for cell in cells)
    for name, highlighted, reading in (
            ("4b-highlighted-values.png", True, False),
            ("4c-reading-problems.png", False, True),
            ("4d-clean-review.png", False, False)):
        issues = tuple(issue for issue in candidate.issues
                       if (issue.code == "flagged_field" and highlighted)
                       or (issue.code != "flagged_field" and reading))
        screen.show_candidate(replace(candidate, issues=issues),
                              cells if highlighted else clean_cells)
        shot(name)
    window._top_bar._edit_mode_btn.click()
    edit = window._edit_page
    opened = open_document(ROOT / "tests" / "editing" / "fixtures" / "word-basic.docx")
    edit.show_opened(opened, reading_view.build(opened))
    shot("5-edit-document.png")
    first = next(b.index for b in opened.paragraphs if b.text.startswith("Invoices are payable"))
    range_first = next(b.index for b in opened.paragraphs if b.text.startswith("The project includes"))
    edit.select_paragraph(range_first)
    edit.select_paragraph(range_first + 1, shift=True)
    # Keep the selected paragraphs in view while retaining the real whole-paragraph rule.
    row = next(i for i, block in enumerate(edit._view) if block.index == range_first)
    edit._reader.scrollTo(edit._reader.model().index(row, 0))
    shot("5b-edit-selected.png")
    edit.select_paragraph(first)
    edit._edit_part_btn.click()
    edit._description.setPlainText("Change the payment period from 30 days to 45 days.")
    proposal = Proposal((ProposedParagraph(0, "Invoices are payable within 45 days of receipt."),))
    edited = build_candidate(opened, first, first, proposal)
    edit.show_proposal(edited, reading_view.paragraphs(opened.data, first, 1),
                       reading_view.paragraphs(edited.data, first, edited.after_count))
    shot("5c-edit-review.png")
    edit.show_saved(PROFILE / "service-outline (edited).docx")
    shot("5d-edit-saved.png")
    window._show_mode("create")
    screen.show_open_file_btn(str(PROFILE / "extracted-information.xlsx"))
    shot("6-saved-file.png")
    print(f"Saved {len(checks)} synthetic screenshots")
    window.close()
    # Closing can wait for window-owned threads; drain them before exiting.
    for _ in range(300):
        app.processEvents()
        if all(getattr(window, name, None) is None for name in _THREADS):
            break
        window.close()
        QThread.msleep(50)
    assert all(getattr(window, name, None) is None for name in _THREADS), "Worker did not stop"
    import json
    (out / "label-background-checks.json").write_text(
        json.dumps(checks, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".venv" / "screens-part-d")
