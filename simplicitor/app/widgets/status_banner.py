# simplicitor/app/widgets/status_banner.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY,
    BODY_TEXT_COLOR,
    ERROR_COLOR,
    FONT_SIZE_BODY_PT,
    SUCCESS_COLOR,
    WHITE,
)

_MUTED_TEXT_COLOR = "#6B7280"


class StatusBanner(QWidget):
    """Dismissible inline banner for success and error status messages.

    For success messages shows a two-line layout: a short human-readable
    primary phrase in green, and the file path(s) in muted gray below.
    For error messages shows a single line in red.

    Hidden by default. Call show_message() to display.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        self._strip = QFrame()
        self._strip.setFixedWidth(4)
        self._strip.setObjectName("status_strip")
        layout.addWidget(self._strip)

        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        # Vertical block: primary line + optional secondary line
        text_block = QWidget()
        text_layout = QVBoxLayout(text_block)
        text_layout.setContentsMargins(8, 4, 8, 4)
        text_layout.setSpacing(2)

        self._primary_label = QLabel()
        primary_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)
        primary_font.setWeight(QFont.Weight.DemiBold)
        self._primary_label.setFont(primary_font)
        self._primary_label.setWordWrap(True)
        self._primary_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        text_layout.addWidget(self._primary_label)

        self._secondary_label = QLabel()
        secondary_font = QFont(APP_FONT_FAMILY, 8)
        self._secondary_label.setFont(secondary_font)
        self._secondary_label.setWordWrap(True)
        self._secondary_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._secondary_label.setStyleSheet(f"color: {_MUTED_TEXT_COLOR};")
        self._secondary_label.setVisible(False)
        text_layout.addWidget(self._secondary_label)

        layout.addWidget(text_block, stretch=1)

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

    def show_message(
        self,
        message: str,
        is_error: bool = False,
        secondary: str = "",
        tooltip: str = "",
    ) -> None:
        """Display the banner with a message.

        Args:
            message: Primary text to show (short phrase).
            is_error: True for red (error), False for green (success).
            secondary: Optional secondary text (truncated paths etc.) shown below in muted gray.
                       For multiple paths, separate with newline.
            tooltip: Full-length text shown on hover over the secondary line.
                     Defaults to ``secondary`` if not supplied.
        """
        color = ERROR_COLOR if is_error else SUCCESS_COLOR
        self._strip.setStyleSheet(f"QFrame {{ background-color: {color}; }}")
        self._primary_label.setStyleSheet(f"color: {color};")
        self._primary_label.setText(message)

        if secondary and not is_error:
            self._secondary_label.setText(secondary)
            self._secondary_label.setToolTip(tooltip or secondary)
            self._secondary_label.setVisible(True)
        else:
            self._secondary_label.setVisible(False)

        self.show()

    def hide_message(self) -> None:
        """Hide the banner."""
        self.hide()

    def text(self) -> str:
        """Return the current banner primary message text."""
        return self._primary_label.text()
