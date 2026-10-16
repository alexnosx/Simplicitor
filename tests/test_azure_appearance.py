"""Azure presentation keeps the existing workspace actions and ownership."""
import pytest
from PySide6.QtCore import QPoint, Qt

from tests.test_main_window_extraction import window


def test_azure_name_and_subtitle_form_one_brand_block(qtbot, qapp):
    from app.version import __version__
    from app.widgets.status_bar import TopBar
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.resize(1024, bar.sizeHint().height())
    qapp.processEvents()
    assert bar._powered_label.text() == "Powered by your local LLM"
    assert bar._tagline_label.text() == "Your documents. Your computer. Your control."
    assert bar._version_label.text() == __version__
    assert not bar._brand_icon.pixmap().isNull()
    title = bar._title_label.mapTo(bar, QPoint(0, 0))
    powered = bar._powered_label.mapTo(bar, QPoint(0, 0))
    assert powered.x() == title.x()
    assert powered.y() >= title.y() + bar._title_label.height()


@pytest.mark.parametrize("width", [1024, 1280])
def test_header_navigation_has_its_own_row_and_fits(qtbot, qapp, width):
    from app.widgets.status_bar import TopBar
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.resize(width, bar.sizeHint().height())
    qapp.processEvents()
    assert bar._brand_row.objectName() == "azureBrandRow"
    assert bar._navigation_row.objectName() == "azureNavigationRow"
    assert bar._navigation_row.y() >= bar._brand_row.geometry().bottom()
    for widget in (bar._create_mode_btn, bar._edit_mode_btn, bar._settings_btn,
                   bar._status_text, bar._tagline_label):
        point = widget.mapTo(bar, QPoint(0, 0))
        assert 0 <= point.x() and point.x() + widget.width() <= width
        assert widget.width() >= widget.fontMetrics().horizontalAdvance(widget.text())
    assert bar._model_combo.isHidden()


def test_shared_azure_palette_and_scoped_styles():
    from app.config import defaults, styles
    expected = {
        "AZURE_HEADER_BG_COLOR": "#1457C6", "BACKGROUND_COLOR": "#F1F4F8",
        "BODY_TEXT_COLOR": "#183049", "MUTED_TEXT_COLOR": "#52667B",
        "BORDER_COLOR": "#C2CEDD", "PRIMARY_ACCENT_COLOR": "#1762DC",
        "CHOICE_SELECTED_COLOR": "#EAF2FF", "CHOICE_HOVER_COLOR": "#F2F7FF",
        "SECONDARY_PRESSED_COLOR": "#D6E6FF", "INFO_BANNER_BG_COLOR": "#EAF2FF",
        "SUCCESS_COLOR": "#156343", "SUCCESS_BG_COLOR": "#E7F6EE",
        "WARNING_TEXT_COLOR": "#764B08", "WARNING_BG_COLOR": "#FFF6DE",
        "ERROR_COLOR": "#A82E3F", "ERROR_BG_COLOR": "#FFE6E9",
    }
    for name, value in expected.items():
        assert getattr(defaults, name, None) == value
    assert defaults.BORDER_RADIUS_PX == 8
    assert defaults.FONT_SIZE_BODY_PT >= 11
    assert "QWidget#azureBrandRow" in styles.header_styles()
    assert "QWidget#azureNavigationRow" in styles.header_styles()
    assert "QFrame#documentCard" in styles.workspace_styles()
    assert "QWidget { background" not in styles.workspace_styles()


def test_main_window_uses_header_size_hint(window, qapp):
    window.resize(1024, 640)
    qapp.processEvents()
    assert window._top_bar.height() >= window._top_bar.sizeHint().height() > 48


def test_footer_tracks_selected_model_without_extra_selection_signals(window, qapp):
    seen = []
    window._top_bar.model_changed.connect(seen.append)
    model = "synthetic:" + "long-model-" * 20
    window._on_ollama_connected([model, "other"], model)
    qapp.processEvents()
    label = window._footer_model
    assert label.textFormat() == Qt.TextFormat.PlainText
    assert label.toolTip() == model
    assert label.fontMetrics().horizontalAdvance(label.text()) <= 220
    assert label.text() != model and model.startswith(label.text().rstrip("\u2026"))
    window._on_ollama_connected([model, "other"], model)
    assert seen == [model]
    window._top_bar._model_combo.setCurrentText("other")
    assert label.text() == label.toolTip() == "other"
    assert seen == [model, "other"]
    window._on_ollama_disconnected()
    assert label.text() == label.toolTip() == ""
    assert seen == [model, "other"]


def test_footer_model_is_literal_and_empty_without_a_selection(window):
    assert window._footer_model.text() == window._footer_model.toolTip() == ""
    window._on_ollama_connected(["<b>local</b>"], "")
    assert window._footer_model.text() == "<b>local</b>"
    assert window._footer_model.textFormat() == Qt.TextFormat.PlainText


def test_write_layout_uses_approved_copy_and_one_common_action(qtbot, isolated_profile):
    from PySide6.QtWidgets import QLabel
    from tests.test_create_screen import _screen
    screen = _screen(qtbot, isolated_profile)
    assert screen._caption.text() == "What would you like to work on?"
    labels = {label.text() for label in screen.findChildren(QLabel)}
    assert {"Local processing", "Only your description is used.",
            "Be specific about the content, sections and length.", "File type"} <= labels
    assert screen._pull_option._title_label.text() == "Pull information into Excel"
    assert screen._describe_actions.indexOf(screen._primary_btn) == 0
    assert screen._primary_btn.parentWidget() is screen._describe_page
    screen.set_route("pull")
    assert not screen._file_type_picker.isVisible()
    screen.set_route("write")
    assert screen._describe_actions.indexOf(screen._primary_btn) == 0


def test_new_file_choice_keeps_signals_and_routes_separate(window, tmp_path, monkeypatch):
    monkeypatch.setattr(window, "_on_generate_requested", lambda *args: None)
    window._connect_create_screen()
    monkeypatch.setattr(window, "_start_extraction", lambda *args, **kwargs: None)
    panel = window._create_screen
    window._on_ollama_connected(["synthetic"], "synthetic")
    panel._prompt_edit.setPlainText("Synthetic summary")
    chosen = []
    panel.file_type_changed.connect(chosen.append)
    panel._file_type_picker.button_for("PDF (.pdf)").click()
    assert chosen == ["PDF (.pdf)"]
    writes = []
    panel.generate_requested.connect(lambda *args: writes.append(args))
    panel._primary_btn.click()
    assert writes == [("PDF (.pdf)", panel._save_dir, "Synthetic summary")]
    panel.set_route("pull")
    panel._prompt_edit.setPlainText("Synthetic fields")
    panel.set_paths((tmp_path / "source.docx",))
    panel.show_inspection(())
    panel.set_route("write")
    assert panel._prompt_edit.toPlainText() == "Synthetic summary"
    assert panel.file_type() == "PDF (.pdf)"
    panel.set_generating(True)
    panel._file_type_picker.button_for("Word (.docx)").click()
    assert panel.file_type() == "PDF (.pdf)"


@pytest.mark.parametrize("name", ["_create_screen", "_edit_page"])
def test_document_screens_use_shared_azure_styles(window, name):
    from app.config.styles import workspace_styles
    screen = getattr(window, name)
    assert workspace_styles() in screen.styleSheet()
    assert screen.font().pointSize() >= 11
    assert "#FFF8E9" not in screen.styleSheet()


def test_pull_ready_reading_and_partial_states_keep_words_and_shared_colours(
        window, tmp_path, monkeypatch):
    from dataclasses import replace
    from docx import Document
    from PySide6.QtWidgets import QLabel
    from app.config.defaults import (
        INFO_BANNER_BG_COLOR, SUCCESS_BG_COLOR, WARNING_BG_COLOR,
    )
    from extraction.models import Issue
    from extraction.source_readers import read_sources
    monkeypatch.setattr(window, "_start_extraction", lambda *args, **kwargs: None)
    panel = window._create_screen
    panel.set_route("pull")
    path = tmp_path / ("long-synthetic-source-" * 4 + ".docx")
    document = Document()
    document.add_paragraph("Synthetic source text")
    document.save(path)
    panel.set_paths((path,))
    state = panel._source_list.itemWidget(panel._source_list.item(0)).findChild(QLabel, "fileState")
    assert state.text() == "Reading" and INFO_BANNER_BG_COLOR in state.styleSheet()
    docs = read_sources((path,))
    panel.show_inspection(docs)
    assert state.text() == "Ready" and SUCCESS_BG_COLOR in state.styleSheet()
    issue = Issue("skipped_text_box", docs[0].source_id, docs[0].source_id + "#", "unread")
    panel.show_inspection((replace(docs[0], issues=(issue,)),))
    assert state.text() == "Partly read" and WARNING_BG_COLOR in state.styleSheet()
    assert panel._source_coverage.toPlainText().startswith(
        "Some information may be missing from the table. Check these problems before you use it:")
    assert "Source files are kept unchanged" in {
        label.text() for label in panel.findChildren(QLabel)}


def test_status_paths_are_literal_readable_and_dismissible(qtbot):
    from app.widgets.status_banner import StatusBanner
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("Synthetic success", secondary="<b>synthetic</b>")
    assert banner._secondary_label.textFormat() == Qt.TextFormat.PlainText
    assert banner._secondary_label.font().pointSize() >= 11
    banner._dismiss_btn.click()
    assert not banner.isVisible()


@pytest.mark.parametrize("kind", ["settings", "templates"])
def test_owned_dialogs_share_controls_and_readable_type(qtbot, isolated_profile, kind):
    from app.config.styles import workspace_styles
    if kind == "settings":
        from app.widgets.settings_dialog import SettingsDialog
        dialog = SettingsDialog(isolated_profile, models=["synthetic"], current_model="synthetic")
        assert dialog.selected_model() == "synthetic"
    else:
        from app.widgets.template_dialog import TemplateDialog
        dialog = TemplateDialog(isolated_profile.templates_dir)
    qtbot.addWidget(dialog)
    assert workspace_styles() in dialog.styleSheet()
    assert dialog.font().pointSize() >= 11


def _pull_review(window, tmp_path, kind):
    """Stage saved-output UI data, without a model request or a save."""
    from extraction.models import Candidate, Issue, ReviewCell
    panel = window._create_screen
    panel.set_route("pull")
    flagged = kind in ("highlighted", "combined")
    reading = kind in ("reading", "combined")
    issues = tuple(issue for issue, present in (
        (Issue("flagged_field", "source-1", "C2", "review"), flagged),
        (Issue("request_failed", "source-1", "source-1#p:0", "reading"), reading)) if present)
    evidence = ({"Data cell": "C2", "Record": "source-1", "File": "synthetic.docx",
                 "Field": "Total", "Value": "12,500.00", "Quote": "Total: 12,500.00",
                 "Anchor": "source-1#p:0", "Status": "flagged" if flagged else "verified",
                 "Issue": "sectioned_source" if flagged else ""},)
    candidate = Candidate("synthetic", tmp_path / "candidate.xlsx",
                          (tmp_path / "synthetic.docx",), issues)
    panel.show_candidate(candidate, (ReviewCell(2, 3, 12500.0, "n", evidence, "0.00"),))
    return panel


def _reach(widget, window, qapp):
    """Prove the whole action is inside the window and its scroll viewports."""
    from PySide6.QtWidgets import QScrollArea
    areas = []
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea):
            areas.append(parent)
            parent.ensureWidgetVisible(widget, 4, 4)
        parent = parent.parentWidget()
    qapp.processEvents()
    point = widget.mapTo(window, QPoint(0, 0))
    assert window.rect().contains(point)
    assert window.rect().contains(point + widget.rect().bottomRight())
    for area in areas:
        point = widget.mapTo(area.viewport(), QPoint(0, 0))
        assert area.viewport().rect().contains(point)
        assert area.viewport().rect().contains(point + widget.rect().bottomRight())


@pytest.mark.parametrize("size", [(1024, 640), (1280, 800)])
@pytest.mark.parametrize("kind", ["highlighted", "reading", "combined"])
def test_pull_review_acknowledgement_and_save_are_reachable(window, qtbot, qapp, tmp_path, size, kind):
    panel = _pull_review(window, tmp_path, kind)
    window.resize(*size)
    qapp.processEvents()
    assert (window.width(), window.height()) == size
    assert panel._ack_checkbox.isVisible() and not panel._save_btn.isEnabled()
    _reach(panel._grid, window, qapp)
    assert panel._grid.viewport().height() >= panel._grid.rowHeight(0)
    if panel._review_note.isVisible():
        assert panel._review_note.height() >= panel._review_note.fontMetrics().height() + 20
    if panel._coverage_view.isVisible():
        assert panel._coverage_view.viewport().height() >= panel._coverage_view.fontMetrics().height()
    _reach(panel._ack_checkbox, window, qapp)
    qtbot.mouseClick(panel._ack_checkbox, Qt.MouseButton.LeftButton,
                     pos=QPoint(8, panel._ack_checkbox.height() // 2))
    assert panel._ack_checkbox.isChecked() and panel._save_btn.isEnabled()
    _reach(panel._save_btn, window, qapp)
    panel._ack_checkbox.setFocus()
    qtbot.keyClick(panel._ack_checkbox, Qt.Key.Key_Tab)
    assert panel._save_btn.hasFocus()


@pytest.mark.parametrize("size", [(1024, 640), (1280, 800)])
def test_edit_review_with_notice_and_actions_is_reachable(window, qapp, tmp_path, size):
    from tests.test_edit_screen import make_opened
    from editing import reading_view
    from editing.models import Proposal, ProposedParagraph
    from editing.patch import build_candidate
    opened = make_opened(tmp_path)
    window._show_mode("edit")
    panel = window._edit_page
    panel.show_opened(opened, reading_view.build(opened))
    proposal = Proposal((ProposedParagraph(0, "Payment is due within 45 days."),))
    candidate = build_candidate(opened, 1, 2, proposal)
    before = reading_view.paragraphs(opened.data, 1, 2)
    after = reading_view.paragraphs(candidate.data, 1, 1)
    candidate = reading_view.with_review_deletions(candidate, before, after,
                                                   tuple(p.source for p in proposal.paragraphs))
    panel.show_proposal(candidate, before, after)
    panel._deletion_notice.setText(panel._deletion_notice.text() + " Synthetic review note." * 8)
    window.resize(*size)
    qapp.processEvents()
    assert (window.width(), window.height()) == size
    assert panel._before.model().blocks == before and panel._after.model().blocks == after
    assert panel._deletion_notice.isVisible()
    assert panel._before.viewport().height() >= 64
    assert panel._after.viewport().height() >= 64
    for widget in (panel._use_btn, panel._try_btn, panel._cancel_review_btn):
        _reach(widget, window, qapp)
        widget.setFocus()
        assert widget.hasFocus()


@pytest.mark.parametrize("route", ["write", "pull", "columns"])
def test_describe_and_columns_actions_are_reachable_at_minimum(window, qapp, route):
    from extraction.models import ColumnSpec
    panel = window._create_screen
    panel.set_route("write" if route == "write" else "pull")
    if route == "columns":
        panel.set_columns(tuple(ColumnSpec(str(i), f"Column {i}", "Synthetic", "text")
                                for i in range(4)))
        action = panel._extract_btn
    else:
        action = panel._primary_btn
    window.resize(1024, 640)
    qapp.processEvents()
    assert (window.width(), window.height()) == (1024, 640)
    _reach(action, window, qapp)


def test_busy_columns_do_not_overlap_the_controls_at_minimum(window, qapp, monkeypatch):
    from pathlib import Path
    from extraction.models import ColumnSpec
    from tests.test_create_screen import _document
    monkeypatch.setattr(window, "_start_extraction", lambda *args, **kwargs: None)
    panel = window._create_screen
    panel.set_route("pull")
    path = Path("synthetic.docx")
    panel.set_paths((path,))
    panel.show_inspection((_document(path),))
    panel.set_columns(tuple(ColumnSpec(str(i), f"Column {i}", "Synthetic", "text")
                            for i in range(4)))
    panel.set_busy(True, action="extract")
    window.resize(1024, 640)
    qapp.processEvents()
    parent = panel._columns_table.parentWidget()
    assert panel._columns_table.geometry().bottom() < panel._add_column_btn.mapTo(parent, QPoint()).y()
    _reach(panel._extract_btn, window, qapp)


@pytest.mark.parametrize("option,value", [("--size", "not-a-size"), ("--state", "unknown")])
def test_capture_cli_rejects_unknown_size_and_state(tmp_path, option, value):
    import os
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / "scripts/capture_screens.py"),
                             str(tmp_path / "captures"), option, value],
                            env=os.environ.copy(), capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "usage: capture_screens.py" in result.stderr
    assert "error:" in result.stderr.lower()
    assert "Traceback" not in result.stderr


def test_local_processing_is_an_informational_pill(window):
    from app.config.defaults import SUCCESS_BG_COLOR, SUCCESS_COLOR
    label = window._create_screen._local_label
    assert label.objectName() == "localProcessing"
    assert SUCCESS_BG_COLOR in label.styleSheet() and SUCCESS_COLOR in label.styleSheet()


def test_route_switch_starts_at_the_new_cards_without_losing_input(window, qapp):
    panel = window._create_screen
    panel.set_file_type("PowerPoint (.pptx)")
    panel.set_template_loaded(True, "business_pitch")
    panel._prompt_edit.setPlainText("Synthetic summary")
    window.resize(1024, 640)
    qapp.processEvents()
    bar = panel._describe_scroll.verticalScrollBar()
    bar.setValue(bar.maximum())
    assert bar.value() > 0
    panel.set_route("pull")
    qapp.processEvents()
    assert bar.value() == 0
    panel.set_route("write")
    assert panel._prompt_edit.toPlainText() == "Synthetic summary" and panel._template_loaded


def test_capture_cli_records_real_scaled_dimensions_and_one_state(tmp_path):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "captures"
    env = dict(os.environ, QT_SCALE_FACTOR="1.25", QT_AUTO_SCREEN_SCALE_FACTOR="0",
               QT_SCREEN_SCALE_FACTORS="1")
    result = subprocess.run([sys.executable, str(root / "scripts/capture_screens.py"), str(out),
                             "--size", "1024x640", "--state", "4-review-and-save"],
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert {p.name for p in out.glob("*.png")} == {
        "4-review-and-save.png", "4-review-and-save-actions.png"}
    data = json.loads((out / "capture-metadata.json").read_text(encoding="utf-8"))
    assert data["logical_window_size"] == [1024, 640]
    assert data["synthetic_only"] is True
    assert data["screens"][0]["physical_size"] == [1280, 800]
    assert data["screens"][0]["device_pixel_ratio"] == 1.25


def test_capture_cli_full_minimum_set_keeps_review_actions_reachable(tmp_path):
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "captures"
    env = dict(os.environ, QT_SCALE_FACTOR="1", QT_AUTO_SCREEN_SCALE_FACTOR="0",
               QT_SCREEN_SCALE_FACTORS="1")
    result = subprocess.run([sys.executable, str(root / "scripts/capture_screens.py"), str(out),
                             "--size", "1024x640"], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads((out / "capture-metadata.json").read_text(encoding="utf-8"))
    assert len(data["screens"]) == 32
    assert data["built_in_templates"] == ["business_pitch", "technical_overview"]
    names = {entry["image"] for entry in data["screens"]}
    assert {"4-review-and-save-actions.png", "4b-highlighted-values-actions.png",
            "4c-reading-problems-actions.png", "9-edit-deletion-review-actions.png"} <= names


@pytest.fixture
def capture_typography(qapp):
    """Match the application entry point's font and input style for layout checks."""
    from PySide6.QtGui import QFont
    from app.config.defaults import APP_FONT_FAMILY, FONT_SIZE_BODY_PT
    from app.config.styles import input_styles
    font, style = qapp.font(), qapp.styleSheet()
    qapp.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    qapp.setStyleSheet(input_styles())
    yield
    qapp.setFont(font)
    qapp.setStyleSheet(style)


@pytest.mark.parametrize("route,reading", [("write", False), ("pull", False), ("pull", True)])
def test_describe_cards_fit_without_scrolling_at_1280(
        capture_typography, window, qapp, monkeypatch, route, reading):
    from pathlib import Path
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QLabel
    from tests.test_create_screen import _document
    monkeypatch.setattr(window, "_start_extraction", lambda *args, **kwargs: None)
    window._on_ollama_connected(["synthetic"], "synthetic")
    panel = window._create_screen
    panel._folder_label.setText(r"C:\Users\Example\Documents\Simplicitor\Generated")
    panel.set_file_type("PowerPoint (.pptx)")
    panel.set_template_loaded(True, "business_pitch")
    panel.set_route(route)
    panel._prompt_edit.setPlainText("Synthetic request")
    if route == "pull":
        paths = (Path("invoice-01.docx"), Path("narrative-invoice-02.pdf"))
        panel.set_paths(paths)
        if reading:
            panel.set_busy(True, action="inspect")
            panel.show_progress("Reading sources...")
        else:
            panel.show_inspection(tuple(_document(path) for path in paths))
    window.resize(1280, 800)
    qapp.processEvents()
    qapp.sendPostedEvents(None, QEvent.Type.LayoutRequest)
    qapp.processEvents()
    scroll = panel._describe_scroll
    assert scroll.verticalScrollBar().maximum() == 0, (
        f"{route}: body={scroll.widget().size()}, viewport={scroll.viewport().size()}")
    assert scroll.horizontalScrollBar().maximum() == 0
    if route == "pull":
        hint = next(label for label in panel._source_card.findChildren(QLabel) if label.text() ==
                    "DOCX and PDFs with selectable text. Scanned PDFs are not supported.")
        corner = hint.mapTo(scroll.viewport(), hint.rect().bottomRight())
        assert scroll.viewport().rect().contains(corner)
        assert hint.height() >= hint.heightForWidth(hint.width())


def test_source_unchanged_note_stays_on_one_line_at_1280(capture_typography, window, qapp):
    panel = window._create_screen
    panel.set_route("pull")
    window.resize(1280, 800)
    qapp.processEvents()
    note = panel._source_note
    assert note.width() >= note.fontMetrics().horizontalAdvance(note.text())
    assert note.height() < 2 * note.fontMetrics().lineSpacing()


@pytest.mark.parametrize("state", ["focused", "focused_checked", "hover_checked"])
def test_top_bar_mode_text_fits_inside_styled_contents(capture_typography, qtbot, qapp, state):
    from PySide6.QtWidgets import QStyle, QStyleOptionButton
    from app.widgets.status_bar import TopBar
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.resize(1280, bar.sizeHint().height())
    button = bar._create_mode_btn
    if state == "focused":
        bar._edit_mode_btn.setChecked(True)
    if state.startswith("focused"):
        button.setFocus()
    else:
        bar._settings_btn.setFocus()
        qtbot.mouseMove(button, button.rect().center())
    qapp.processEvents()
    option = QStyleOptionButton()
    button.initStyleOption(option)
    assert button.isChecked() == (state != "focused")
    assert bool(option.state & QStyle.StateFlag.State_HasFocus) == state.startswith("focused")
    if state.startswith("hover"):
        assert option.state & QStyle.StateFlag.State_MouseOver
    content = button.style().subElementRect(QStyle.SubElement.SE_PushButtonContents, option, button)
    assert content.width() >= button.fontMetrics().horizontalAdvance(button.text()), (
        f"{state}: text needs {button.fontMetrics().horizontalAdvance(button.text())}, "
        f"styled content width={content.width()}")
