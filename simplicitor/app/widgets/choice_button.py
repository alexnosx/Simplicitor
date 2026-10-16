"""An accessible push button with a wrapped caption and one click target."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from app.config.defaults import (
    BODY_TEXT_COLOR, BORDER_COLOR, BORDER_RADIUS_PX, CHOICE_HOVER_COLOR,
    CHOICE_SELECTED_COLOR, FONT_SIZE_BODY_PT, MUTED_TEXT_COLOR, PRIMARY_ACCENT_COLOR,
    SECONDARY_PRESSED_COLOR, WHITE,
)


class ChoiceButton(QPushButton):
    """Present one checkable choice; decorative children never intercept input."""

    def __init__(self, title: str, caption: str = "", icon: QIcon | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setProperty("choice", True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(62)
        self.setStyleSheet(
            f"ChoiceButton {{ background: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 0; }}"
            f"ChoiceButton:hover {{ background: {CHOICE_HOVER_COLOR}; }}"
            f"ChoiceButton:checked {{ background: {CHOICE_SELECTED_COLOR}; "
            f"border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
            f"ChoiceButton:focus {{ border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
            f"ChoiceButton:pressed {{ background: {SECONDARY_PRESSED_COLOR}; }}"
            f"ChoiceButton QLabel {{ background: transparent; color: {BODY_TEXT_COLOR}; "
            f"font-size: {FONT_SIZE_BODY_PT}pt; }}"
            "ChoiceButton QLabel[choiceTitle='true'] { font-weight: 600; }"
            f"ChoiceButton QLabel[muted='true'] {{ color: {MUTED_TEXT_COLOR}; }}")
        self.setAccessibleName(title + (". " + caption if caption else ""))
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(30, 30)
        if icon is not None:
            self._icon_label.setPixmap(icon.pixmap(30, 30))
        else:
            self._icon_label.hide()
        row.addWidget(self._icon_label)
        text = QVBoxLayout()
        text.setSpacing(3)
        self._title_label = QLabel(title)
        self._title_label.setWordWrap(True)
        self._title_label.setProperty("choiceTitle", True)
        self._caption_label = QLabel(caption)
        self._caption_label.setWordWrap(True)
        self._caption_label.setProperty("muted", True)
        self._caption_label.setVisible(bool(caption))
        for label in (self._title_label, self._caption_label):
            label.setTextFormat(Qt.TextFormat.PlainText)
            text.addWidget(label)
        row.addLayout(text, 1)
        self._check_label = QLabel("")
        self._check_label.setFixedWidth(18)
        row.addWidget(self._check_label)
        for label in (self._icon_label, self._title_label, self._caption_label, self._check_label):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.toggled.connect(self._show_checked)

    def _show_checked(self, checked: bool) -> None:
        self._check_label.setText("\u2713" if checked else "")

    def sizeHint(self) -> QSize:
        return self.layout().sizeHint().expandedTo(QSize(0, 62))

    def minimumSizeHint(self) -> QSize:
        return self.layout().minimumSize()
