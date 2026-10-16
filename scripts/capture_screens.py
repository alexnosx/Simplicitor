# scripts/capture_screens.py
"""Render Create new and Edit for Word states offscreen at 1280x800 with synthetic data and an
isolated profile under .venv. Installs nothing and touches no real user folders."""
import argparse
import hashlib
import json
import os
import subprocess
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

from PySide6.QtCore import QEvent, QPoint, QRect, QThread  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication, QFrame, QLabel, QScrollArea, QStyle, QStyleOptionButton,
)

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


STATE_NAMES = (
    "1-create-describe", "1b-write-template", "2a-files-reading", "2-create-with-files",
    "2b-files-partly-read", "3-choose-columns", "3b-pull-busy", "4-review-and-save",
    "4b-highlighted-values", "4c-reading-problems", "4d-clean-review", "5-edit-document",
    "5b-edit-selected", "5c-edit-review", "5d-edit-saved", "6-saved-file",
    "7-settings", "7b-built-in-template", "8-disconnected", "8b-create-error",
    "8c-edit-no-model", "8d-edit-busy", "9-edit-deletion-review", "9b-edit-save",
)


def parse_size(value: str) -> tuple[int, int]:
    """Accept logical window dimensions at or above the application's minimum."""
    parts = value.lower().split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise argparse.ArgumentTypeError("size must be WIDTHxHEIGHT")
    width, height = map(int, parts)
    if width < 1024 or height < 640:
        raise argparse.ArgumentTypeError("size must be at least 1024x640")
    return width, height


def main(out: Path, size: tuple[int, int] = (1280, 800), state: str | None = None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    # Match the existing application entry point, including its input styles.
    app.setStyleSheet(input_styles())

    config = PROFILE / "AppData" / "Roaming" / "Simplicitor"
    config.mkdir(parents=True, exist_ok=True)
    window = MainWindow(Settings(config))
    window.resize(*size)
    window.show()
    screen = window._create_screen
    edit = window._edit_page
    for _ in range(100):
        app.processEvents()
        if screen._connected:
            break
        QThread.msleep(10)
    assert screen._connected
    screen._folder_label.setText(r"C:\Users\Example\Documents\Simplicitor\Generated")
    checks = []

    def visible_rect(widget, surface=window):
        rect = QRect(widget.mapTo(surface, QPoint(0, 0)), widget.size())
        parent = widget.parentWidget()
        while parent is not None:
            rect = rect.intersected(QRect(parent.mapTo(surface, QPoint(0, 0)), parent.size()))
            if parent is surface:
                break
            parent = parent.parentWidget()
        return rect

    def reveal(widget):
        parent = widget.parentWidget()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                # A preceding review state may have changed the card's height.
                # Deliver its layout requests before consulting the scroll range.
                parent.widget().layout().activate()
                app.sendPostedEvents(None, QEvent.Type.LayoutRequest)
                app.processEvents()
                parent.ensureWidgetVisible(widget, 4, 4)
            parent = parent.parentWidget()
        app.processEvents()

    def shot(name: str, surface=None, actions=()) -> None:
        if state is not None and name.removesuffix(".png") != state:
            return
        surface = surface or window
        if surface is window:
            owner = window._modes.currentWidget()
            active = owner._pages.currentWidget()
            areas = active.findChildren(QScrollArea)
            if isinstance(active, QScrollArea):
                areas.append(active)
            for area in areas:
                area.verticalScrollBar().setValue(0)
        app.processEvents()
        # Discovery and route changes post layouts after the first event pass.
        app.sendPostedEvents(None, QEvent.Type.LayoutRequest)
        app.processEvents()
        image = surface.grab()
        ratio = image.devicePixelRatio()
        if surface is window:
            assert (window.width(), window.height()) == size
        assert abs(image.width() - surface.width() * ratio) <= 1
        assert abs(image.height() - surface.height() * ratio) <= 1
        pixels = image.toImage()
        checked = clipped = 0
        for card in surface.findChildren(QFrame):
            if card.objectName() != "documentCard" or not card.isVisible():
                continue
            for label in card.findChildren(QLabel):
                if not label.isVisible() or not label.text():
                    continue
                rect = visible_rect(label, surface)
                if rect.width() < 3 or rect.height() < 3:
                    clipped += 1
                    continue
                corner = rect.bottomRight() - QPoint(1, 1)
                pixel = QPoint(round(corner.x() * ratio), round(corner.y() * ratio))
                assert pixels.pixelColor(pixel).name().lower() != BACKGROUND_COLOR.lower(), (
                    "Grey card label background: " + label.text())
                checked += 1
        assert image.save(str(out / name))
        measured = {}
        if surface is window:
            buttons = []
            for button in (window._top_bar._create_mode_btn, window._top_bar._edit_mode_btn):
                option = QStyleOptionButton()
                button.initStyleOption(option)
                contents = button.style().subElementRect(
                    QStyle.SubElement.SE_PushButtonContents, option, button)
                text_width = button.fontMetrics().horizontalAdvance(button.text())
                assert contents.width() >= text_width, "Mode button text is clipped"
                buttons.append({"text": button.text(), "content_width": contents.width(),
                                "text_width": text_width, "focused": button.hasFocus(),
                                "checked": button.isChecked()})
            measured["mode_button_contents"] = buttons
        if surface is window and name in (
                "1-create-describe.png", "1b-write-template.png", "2a-files-reading.png",
                "2-create-with-files.png"):
            scroll = screen._describe_scroll
            measured["describe_layout"] = {
                "vertical_scroll_maximum": scroll.verticalScrollBar().maximum(),
                "horizontal_scroll_maximum": scroll.horizontalScrollBar().maximum(),
                "viewport_size": list(scroll.viewport().size().toTuple()),
                "body_size": list(scroll.widget().size().toTuple()),
            }
            if size == (1280, 800):
                assert scroll.verticalScrollBar().maximum() == 0, (
                    f"Describe needs scrolling: body={scroll.widget().size()}, "
                    f"viewport={scroll.viewport().size()}, minimum={scroll.widget().minimumSizeHint()}")
                assert scroll.horizontalScrollBar().maximum() == 0
            if screen.route() == "pull":
                note = screen._source_note
                note_width = note.fontMetrics().horizontalAdvance(note.text())
                hint = next(label for label in screen._source_card.findChildren(QLabel)
                            if label.text() == "DOCX and PDFs with selectable text. "
                            "Scanned PDFs are not supported.")
                hint_visible = visible_rect(hint).size() == hint.size()
                measured["describe_layout"].update({
                    "source_note_width": note.width(), "source_note_text_width": note_width,
                    "source_hint_fully_visible": hint_visible,
                })
                if size == (1280, 800):
                    assert hint_visible, "Source format and scanned-PDF hint is clipped"
                    assert note.width() >= note_width, "Source note wraps"
        checks.append({"image": name, "logical_size": [surface.width(), surface.height()],
                       "physical_size": [image.width(), image.height()], "device_pixel_ratio": ratio,
                       "card_labels_checked": checked, "clipped_labels_not_sampled": clipped,
                       "grey_label_backgrounds": 0, **measured})
        if surface is window and actions:
            for widget in actions:
                reveal(widget)
                rect = visible_rect(widget)
                assert rect.size() == widget.size(), (
                    f"Action is not fully reachable: {widget.text()}, visible={rect}, size={widget.size()}")
            action_image = window.grab()
            action_name = name.removesuffix(".png") + "-actions.png"
            assert action_image.save(str(out / action_name))
            checks.append({"image": action_name, "logical_size": list(size),
                           "physical_size": [action_image.width(), action_image.height()],
                           "device_pixel_ratio": action_image.devicePixelRatio(),
                           "reachable_controls": [w.accessibleName() or w.text() for w in actions]})

    try:
        shot("1-create-describe.png")
        screen._prompt_edit.setPlainText(
            "Create a six-slide project update covering progress, risks and next steps.")
        screen.set_file_type("PowerPoint (.pptx)")
        screen.set_template_loaded(True, "business_pitch")
        shot("1b-write-template.png", actions=(screen._change_folder_btn, screen._primary_btn))
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
        shot("4-review-and-save.png", actions=(screen._ack_checkbox, screen._save_btn))
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
            shot(name, actions=((screen._ack_checkbox, screen._save_btn) if highlighted or reading
                                else (screen._save_btn,)))
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
        before = reading_view.paragraphs(opened.data, first, 1)
        after = reading_view.paragraphs(edited.data, first, edited.after_count)
        reviewed = reading_view.with_review_deletions(
            edited, before, after, tuple(p.source for p in proposal.paragraphs))
        edit.show_proposal(reviewed, before, after)
        shot("5c-edit-review.png", actions=(edit._use_btn, edit._try_btn, edit._cancel_review_btn))
        edit.show_saved(PROFILE / "service-outline (edited).docx")
        shot("5d-edit-saved.png")
        window._show_mode("create")
        screen.show_open_file_btn(str(PROFILE / "extracted-information.xlsx"))
        shot("6-saved-file.png")
        # Owned dialogs use the same real widgets, without executing a modal loop.
        from app.widgets.settings_dialog import SettingsDialog
        from app.widgets.template_dialog import TemplateDialog
        settings_dialog = SettingsDialog(window._settings, models=["qwen3:8b"],
                                          current_model="qwen3:8b", parent=window)
        settings_dialog.show()
        shot("7-settings.png", surface=settings_dialog)
        settings_dialog.close()
        main_window.ensure_default_templates(Path(window._settings.templates_dir))
        template_dialog = TemplateDialog(window._settings.templates_dir, parent=window)
        assert template_dialog._template_list.count() == 2
        template_dialog._template_list.setCurrentRow(0)
        template_dialog.show()
        shot("7b-built-in-template.png", surface=template_dialog)
        template_dialog.close()
        screen._another_btn.click()
        window._on_ollama_disconnected()
        shot("8-disconnected.png")
        screen.show_status("Synthetic example: could not create the file.", True)
        shot("8b-create-error.png")
        screen.clear_status()
        window._ollama_client.get_models = lambda **kw: []
        window._ollama_client.get_running_model = lambda **kw: ""
        window._on_ollama_connected([], "")
        window._show_mode("edit")
        edit.show_opened(opened, reading_view.build(opened))
        edit.select_paragraph(first)
        edit._edit_part_btn.click()
        shot("8c-edit-no-model.png")
        window._ollama_client.get_models = lambda **kw: ["qwen3:8b"]
        window._ollama_client.get_running_model = lambda **kw: "qwen3:8b"
        window._on_ollama_connected(["qwen3:8b"], "qwen3:8b")
        edit._description.setPlainText("A synthetic change for this preview.")
        edit._action = "propose"
        edit.set_busy(True)
        shot("8d-edit-busy.png")
        edit.set_busy(False)
        # Only synthetic fixture paragraphs are used; this is not a model check.
        proposal = Proposal((ProposedParagraph(0, opened.paragraphs[range_first].text),))
        edited = build_candidate(opened, range_first, range_first + 1, proposal)
        before = reading_view.paragraphs(opened.data, range_first, 2)
        after = reading_view.paragraphs(edited.data, range_first, edited.after_count)
        reviewed = reading_view.with_review_deletions(
            edited, before, after, tuple(p.source for p in proposal.paragraphs))
        edit.show_proposal(reviewed, before, after)
        shot("9-edit-deletion-review.png", actions=(edit._use_btn, edit._try_btn, edit._cancel_review_btn))
        edit._use_btn.click()
        shot("9b-edit-save.png", actions=(edit._save_btn,))
        print(f"Saved {len(checks)} synthetic screenshots")
    finally:
        # Drop staged unsaved UI data; never enter a discard dialog in a capture.
        edit.set_busy(False)
        edit.reset()
        screen.set_busy(False)
        window.close()
        # Closing can wait for window-owned threads; drain them before exiting.
        for _ in range(300):
            app.processEvents()
            if all(getattr(window, name, None) is None for name in _THREADS):
                break
            window.close()
            QThread.msleep(50)
        assert all(getattr(window, name, None) is None for name in _THREADS), "Worker did not stop"
    (out / "label-background-checks.json").write_text(
        json.dumps(checks, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                  text=True).strip(),
        "built_in_templates": [template_dialog._template_list.item(i).text()
                               for i in range(template_dialog._template_list.count())],
        "capture_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_commit_is_base": bool(subprocess.check_output(
            ["git", "diff", "--name-only"], cwd=ROOT, text=True).strip()),
        "source_files_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(
            path.read_bytes()).hexdigest() for path in [
                ROOT / "scripts/capture_screens.py", ROOT / "simplicitor/app/main_window.py",
                ROOT / "simplicitor/app/config/defaults.py", ROOT / "simplicitor/app/config/styles.py",
                ROOT / "simplicitor/app/version.py",
                *sorted((ROOT / "simplicitor/app/widgets").glob("*.py"))]},
        "logical_window_size": list(size), "qt_scale_factor": os.environ.get("QT_SCALE_FACTOR", "1"),
        "platform": app.platformName(), "synthetic_only": True, "screens": checks,
    }
    (out / "capture-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", nargs="?", type=Path, default=ROOT / ".venv" / "screens-part-d")
    parser.add_argument("--size", type=parse_size, default=(1280, 800))
    parser.add_argument("--state", type=lambda value: value.removesuffix(".png"), choices=STATE_NAMES)
    args = parser.parse_args()
    main(args.out, args.size, args.state)
