"""Approved mockup affordances, without changing document processing."""
from PySide6.QtWidgets import QLabel
import pytest

from tests.test_create_screen import _screen
from tests.test_main_window_extraction import window


def test_numbered_cards_show_only_the_chosen_inputs(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    assert screen._describe_title.text() == "1. Describe the document you need"
    assert screen._output_card.isVisible() and not screen._source_card.isVisible()
    assert screen._primary_btn.parentWidget() is screen._output_card
    screen.set_route("pull")
    assert screen._describe_title.text() == "1. Describe the information you need"
    assert not screen._output_card.isVisible() and screen._source_card.isVisible()
    assert not screen._type_combo.isVisible()
    assert screen._primary_btn.parentWidget() is screen._description_card
    titles = {label.text() for label in screen.findChildren(QLabel)}
    assert {"2. Choose the output", "2. Add your source files", "3. Choose columns",
            "4. Review your table", "5. Where this value came from"} <= titles


def test_body_borders_dropdown_and_focus_styles(qtbot, isolated_profile):
    from app.config.defaults import FONT_SIZE_BODY_PT, BORDER_COLOR, PRIMARY_ACCENT_COLOR
    screen = _screen(qtbot, isolated_profile)
    assert FONT_SIZE_BODY_PT >= 11
    assert BORDER_COLOR == "#9CA8B7"
    style = screen.styleSheet()
    assert "font-size: 11pt" in style
    assert "QComboBox:focus" in style and PRIMARY_ACCENT_COLOR in style
    assert "QComboBox QAbstractItemView::item:hover" in style
    assert "QComboBox QAbstractItemView::item:selected" in style
    assert "#E6F0FF" in style and "#DBEAFE" in style


def test_template_button_chosen_clear_and_busy_states(window):
    panel = window._create_screen
    window._on_ollama_connected(["qwen3:8b"], "")
    panel.set_file_type("PowerPoint (.pptx)")
    assert panel._template_btn.property("secondary") is True
    assert panel._template_btn.property("chosen") is False
    assert not panel._clear_template_btn.isVisible()
    window._on_template_selected({}, "synthetic-template", "business_pitch")
    assert panel._template_btn.property("chosen") is True
    assert panel._template_name.text() == "Template: business_pitch"
    assert panel._clear_template_btn.isVisible()
    panel.set_busy(True)
    assert not panel._clear_template_btn.isEnabled()
    panel.set_busy(False)
    panel._clear_template_btn.click()
    assert window._loaded_template is None and not panel._template_loaded
    assert panel._template_btn.property("chosen") is False
    assert not panel._clear_template_btn.isVisible()
    assert "QPushButton[secondary='true']:hover" in panel.styleSheet()
    assert "QPushButton[secondary='true']:pressed" in panel.styleSheet()
    assert "QPushButton[secondary='true'][chosen='true']" in panel.styleSheet()


def test_template_is_kept_across_routes_but_not_a_real_type_change(window):
    panel = window._create_screen
    panel.set_file_type("PowerPoint (.pptx)")
    window._on_template_selected({}, "synthetic-template", "business_pitch")
    panel.set_route("pull")
    assert not panel._template_btn.isVisible()
    panel.set_route("write")
    assert panel._template_loaded and window._loaded_template is not None
    panel.set_file_type("PDF (.pdf)")
    assert not panel._template_loaded and window._loaded_template is None


def test_clicking_active_option_keeps_its_selected_state(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen._write_option.click()
    assert screen.route() == "write" and screen._write_option.isChecked()
    screen._pull_option.click()
    screen._pull_option.click()
    assert screen.route() == "pull" and screen._pull_option.isChecked()
    assert not screen._write_option.isChecked()


def test_route_round_trip_keeps_the_action_at_the_left(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    screen.set_route("write")
    assert screen._write_actions.indexOf(screen._primary_btn) == 0


@pytest.mark.parametrize("check", ["height", "selection"])
def test_busy_columns_keep_four_rows_visible_and_a_light_selection(
        window, qapp, monkeypatch, tmp_path, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFont
    from app.config.defaults import APP_FONT_FAMILY, CHOICE_SELECTED_COLOR, FONT_SIZE_BODY_PT
    from extraction.models import ColumnSpec
    from extraction.source_readers import read_sources
    from docx import Document

    original_font = qapp.font()
    try:
        qapp.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        window.resize(1280, 800)
        monkeypatch.setattr(window, "_start_extraction", lambda *args, **kwargs: None)
        panel = window._create_screen
        panel.set_route("pull")
        paths = (tmp_path / "one.docx", tmp_path / "two.docx")
        for path in paths:
            document = Document()
            document.add_paragraph("Synthetic text")
            document.save(path)
        panel.set_paths(paths)
        documents = read_sources(paths)
        panel.show_inspection(documents)
        panel.set_columns(tuple(ColumnSpec(str(i), f"Column {i}", "Synthetic field", "text")
                                for i in range(1, 5)))
        panel.set_busy(True, action="extract")
        panel.show_source_progress(documents[0].source_id, len(documents[0].units),
                                   sum(len(doc.units) for doc in documents))
        qapp.processEvents()
        table = panel._columns_table
        assert not table.isEnabled() and panel._file_progress_box.isVisible()
        if check == "height":
            assert window.size().width() == 1280 and window.size().height() == 800
            rows_height = sum(table.rowHeight(row) for row in range(4))
            assert table.viewport().height() >= rows_height
            assert table.minimumHeight() >= rows_height + table.horizontalHeader().height()
        else:
            selected = table.visualItemRect(table.item(0, 1))
            point = QPoint(selected.right() - 8, selected.center().y())
            pixel = table.viewport().grab().toImage().pixelColor(point)
            assert pixel.name().lower() == CHOICE_SELECTED_COLOR.lower()
    finally:
        qapp.setFont(original_font)
