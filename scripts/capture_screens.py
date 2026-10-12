# scripts/capture_screens.py
"""Render each 2.1.0 screen offscreen at 1280x800 with synthetic data and an
isolated profile under .venv. Installs nothing and touches no real user folders."""
import os
import sys
from datetime import datetime
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

from app.config.settings import Settings  # noqa: E402
from app.config.defaults import (  # noqa: E402
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, BORDER_COLOR, PRIMARY_ACCENT_COLOR,
    BODY_TEXT_COLOR, DISABLED_COLOR, WHITE, BORDER_RADIUS_PX,
    BACKGROUND_COLOR,
)
import app.main_window as main_window  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from extraction.models import Candidate, ColumnSpec, Issue, ReviewCell
from extraction.source_readers import read_sources  # noqa: E402

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
            "_template_thread", "_manipulate_thread")


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    # Match the existing application entry point, including its input styles.
    app.setStyleSheet(
        f"QLineEdit, QPlainTextEdit, QListWidget, QComboBox {{"
        f"    background-color: {WHITE};"
        f"    border: 1px solid {BORDER_COLOR};"
        f"    border-radius: {BORDER_RADIUS_PX}px;"
        f"    padding: 6px 8px;"
        f"    font-family: 'Segoe UI';"
        f"    font-size: 13px;"
        f"    color: {BODY_TEXT_COLOR};"
        f"}}"
        f"QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{"
        f"    border: 1px solid {PRIMARY_ACCENT_COLOR};"
        f"    outline: none;"
        f"}}"
        f"QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{"
        f"    background-color: #F9FAFB;"
        f"    color: {DISABLED_COLOR};"
        f"}}"
        f"QListWidget::item {{"
        f"    padding: 6px 8px;"
        f"    border-radius: 2px;"
        f"}}"
        f"QListWidget::item:selected {{"
        f"    background-color: {PRIMARY_ACCENT_COLOR};"
        f"    color: {WHITE};"
        f"}}"
        f"QListWidget::item:hover:!selected {{"
        f"    background-color: #EFF6FF;"
        f"}}"
    )
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
    checks = []

    def shot(name: str) -> None:
        app.processEvents()
        image = window.grab()
        assert image.width() == 1280 and image.height() == 800
        pixels = image.toImage()
        checked = 0
        for card in screen.findChildren(QFrame):
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
    fixtures = ROOT / "tests" / "extraction" / "fixtures"
    screen._prompt_edit.setPlainText("Invoice number, customer, total and due date")
    screen.set_paths((fixtures / "invoice-01.docx", fixtures / "narrative-invoice-02.pdf"))
    screen.show_inspection(read_sources(screen._paths))
    shot("2-create-with-files.png")
    screen.set_columns((ColumnSpec("c1", "Invoice number", "The invoice number", "text"),
                        ColumnSpec("c2", "Customer", "The customer name", "text"),
                        ColumnSpec("c3", "Total", "The amount to pay", "decimal"),
                        ColumnSpec("c4", "Due date", "The payment due date", "date")))
    shot("3-choose-columns.png")
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
    candidate = Candidate("job", PROFILE / "candidate.xlsx", (fixtures / "invoice-01.docx",),
                          (Issue("flagged_field", "source-1", "E2", "review"),
                           Issue("request_failed", "source-1", "source-1#p:9", "reading")))
    screen.show_candidate(candidate, cells)
    screen._grid.setCurrentCell(0, 3)
    screen._grid.clearSelection()  # Keep the evidence visible and show its yellow review fill.
    shot("4-review-and-save.png")
    window._top_bar._edit_mode_btn.click()
    shot("5-edit-document.png")
    window._show_mode("create")
    screen.show_open_file_btn(str(PROFILE / "extracted-information.xlsx"))
    shot("6-saved-file.png")
    print(f"Saved six screenshots to {out}")
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
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".venv" / "screens")
