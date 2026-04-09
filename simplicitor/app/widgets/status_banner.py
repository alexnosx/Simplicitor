# simplicitor/app/widgets/status_banner.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from app.config.defaults import (
    APP_FONT_FAMILY,
    BODY_TEXT_COLOR,
    ERROR_COLOR,
    FONT_SIZE_BODY_PT,
    SUCCESS_COLOR,
    WHITE,
)


class StatusBanner(QWidget):
    """Dismissible inline banner for success and error status messages.

    Shows a colored left strip + message text + dismiss (✕) button.
    Hidden by default. Call show_message() to display.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        self.setMaximumHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        self._strip = QFrame()
        self._strip.setFixedWidth(4)
        self._strip.setObjectName("status_strip")
        layout.addWidget(self._strip)

        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)
        self._text_label = QLabel()
        self._text_label.setFont(body_font)
        self._text_label.setContentsMargins(8, 4, 8, 4)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._text_label.setWordWrap(True)
        layout.addWidget(self._text_label, stretch=1)

        self._dismiss_btn = QPushButton("\u2715")
        self._dismiss_btn.setObjectName("status_dismiss_btn")
        self._dismiss_btn.setFont(body_font)
        self._dismiss_btn.setFixedSize(24, 24)
        self._dismiss_btn.clicked.connect(self.hide)
        layout.addWidget(self._dismiss_btn)

        self.setStyleSheet(
            f"StatusBanner {{ background-color: {WHITE}; }}"
            "QFrame#status_strip { border: none; }"
            f"QPushButton#status_dismiss_btn {{ border: none; background-color: transparent; "
            f"color: {BODY_TEXT_COLOR}; }}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def show_message(self, message: str, is_error: bool = False) -> None:
        """Display the banner with a message.

        Args:
            message: Text to show in the banner.
            is_error: True for red (error), False for green (success).
        """
        color = ERROR_COLOR if is_error else SUCCESS_COLOR
        self._strip.setStyleSheet(f"QFrame {{ background-color: {color}; }}")
        self._text_label.setText(message)
        self.show()

    def hide_message(self) -> None:
        """Hide the banner."""
        self.hide()

    def text(self) -> str:
        """Return the current banner message text."""
        return self._text_label.text()
