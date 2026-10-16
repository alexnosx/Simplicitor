"""Shared input styles for the application and its deterministic screen captures."""
from app.config.defaults import (
    APP_FONT_FAMILY, BODY_TEXT_COLOR, BORDER_COLOR, BORDER_RADIUS_PX,
    CHOICE_HOVER_COLOR, CHOICE_SELECTED_COLOR, DISABLED_COLOR, FONT_SIZE_BODY_PT,
    PRIMARY_ACCENT_COLOR, WHITE, AZURE_HEADER_BG_COLOR, BACKGROUND_COLOR,
    INFO_BANNER_BG_COLOR, SECONDARY_PRESSED_COLOR, MUTED_TEXT_COLOR,
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


def workspace_styles() -> str:
    """Shared flat cards and readable controls; backgrounds target containers only."""
    return input_styles() + (
        f"QWidget#createWorkspace, QWidget#editWorkspace {{ color: {BODY_TEXT_COLOR}; "
        f"font-family: '{APP_FONT_FAMILY}'; font-size: {FONT_SIZE_BODY_PT}pt; }}"
        f"QFrame#documentCard {{ background: {WHITE}; border: 1px solid {BORDER_COLOR}; "
        f"border-radius: {BORDER_RADIUS_PX}px; }}"
        "QLabel[cardTitle='true'] { font-size: 13pt; font-weight: 600; }"
        "QLabel[choiceTitle='true'] { font-weight: 600; }"
        f"QLabel[muted='true'] {{ color: {MUTED_TEXT_COLOR}; }}"
        f"QPushButton[choice='true']:checked {{ background: {CHOICE_SELECTED_COLOR}; "
        f"border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton {{ background: {WHITE}; color: {BODY_TEXT_COLOR}; "
        f"border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; "
        f"padding: 6px 12px; min-height: 22px; font-size: {FONT_SIZE_BODY_PT}pt; }}"
        f"QPushButton:hover {{ background: {CHOICE_HOVER_COLOR}; }}"
        f"QPushButton:focus {{ border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton:pressed {{ background: {SECONDARY_PRESSED_COLOR}; }}"
        f"QPushButton:disabled {{ background: {BACKGROUND_COLOR}; color: {MUTED_TEXT_COLOR}; }}"
        f"QPushButton[primary='true'] {{ background: {PRIMARY_ACCENT_COLOR}; color: {WHITE}; "
        "font-weight: 600; min-height: 26px; }"
        f"QPushButton[primary='true']:hover {{ background: {AZURE_HEADER_BG_COLOR}; }}"
        f"QPushButton[primary='true']:disabled {{ background: {BORDER_COLOR}; color: {MUTED_TEXT_COLOR}; }}"
        f"QPushButton[secondary='true'] {{ background: {INFO_BANNER_BG_COLOR}; "
        f"color: {PRIMARY_ACCENT_COLOR}; border: 1px solid {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton[secondary='true']:hover {{ background: {CHOICE_SELECTED_COLOR}; }}"
        f"QPushButton[secondary='true']:pressed {{ background: {SECONDARY_PRESSED_COLOR}; }}"
        f"QPushButton[secondary='true'][chosen='true'] {{ background: {CHOICE_SELECTED_COLOR}; "
        f"border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton[link='true'] {{ color: {PRIMARY_ACCENT_COLOR}; background: transparent; "
        "border: none; text-align: left; padding: 2px 0; }"
    )


def header_styles() -> str:
    """Style the brand and navigation separately without painting label strips."""
    return (
        f"QWidget#azureBrandRow {{ background: {AZURE_HEADER_BG_COLOR}; }}"
        f"QWidget#azureBrandRow QLabel {{ color: {WHITE}; background: transparent; }}"
        f"QWidget#azureNavigationRow {{ background: {WHITE}; "
        f"border-bottom: 1px solid {BORDER_COLOR}; }}"
        f"QWidget#azureNavigationRow QLabel {{ color: {BODY_TEXT_COLOR}; background: transparent; }}"
        f"QPushButton {{ background: transparent; color: {BODY_TEXT_COLOR}; border: none; "
        f"border-radius: {BORDER_RADIUS_PX}px; padding: 6px 14px; }}"
        f"QPushButton:hover {{ background: {CHOICE_HOVER_COLOR}; }}"
        f"QPushButton:checked {{ background: {CHOICE_SELECTED_COLOR}; color: {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton:focus {{ border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
        f"QPushButton:disabled {{ color: {MUTED_TEXT_COLOR}; }}"
    )
