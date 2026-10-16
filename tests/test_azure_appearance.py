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
