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
