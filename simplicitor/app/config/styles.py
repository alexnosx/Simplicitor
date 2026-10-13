"""Shared input styles for the application and its deterministic screen captures."""
from app.config.defaults import (
    APP_FONT_FAMILY, BODY_TEXT_COLOR, BORDER_COLOR, BORDER_RADIUS_PX,
    CHOICE_HOVER_COLOR, CHOICE_SELECTED_COLOR, DISABLED_COLOR, FONT_SIZE_BODY_PT,
    PRIMARY_ACCENT_COLOR, WHITE,
)


def input_styles() -> str:
    """Keep editable text readable and show blue focus, hover and selection states."""
    return (
        f"QLineEdit, QPlainTextEdit, QListWidget, QComboBox {{ background: {WHITE}; "
        f"border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; "
        f"padding: 6px 8px; font-family: '{APP_FONT_FAMILY}'; "
        f"font-size: {FONT_SIZE_BODY_PT}pt; color: {BODY_TEXT_COLOR}; }}"
        f"QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ "
        f"border: 1px solid {PRIMARY_ACCENT_COLOR}; outline: none; }}"
        f"QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{ "
        f"background: #F9FAFB; color: {DISABLED_COLOR}; }}"
        "QListWidget::item { padding: 6px 8px; border-radius: 2px; }"
        f"QListWidget::item:selected {{ background: {PRIMARY_ACCENT_COLOR}; color: {WHITE}; }}"
        f"QListWidget::item:hover:!selected {{ background: {CHOICE_HOVER_COLOR}; }}"
        f"QComboBox QAbstractItemView {{ background: {WHITE}; color: {BODY_TEXT_COLOR}; "
        f"border: 1px solid {BORDER_COLOR}; selection-background-color: {CHOICE_SELECTED_COLOR}; "
        f"selection-color: {BODY_TEXT_COLOR}; outline: none; }}"
        "QComboBox QAbstractItemView::item { padding: 6px 8px; }"
        f"QComboBox QAbstractItemView::item:hover {{ background: {CHOICE_HOVER_COLOR}; }}"
        f"QComboBox QAbstractItemView::item:selected {{ background: {CHOICE_SELECTED_COLOR}; }}"
    )
