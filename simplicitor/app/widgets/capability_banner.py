# simplicitor/app/widgets/capability_banner.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT,
    PRIMARY_ACCENT_COLOR, INFO_BANNER_BG_COLOR, BODY_TEXT_COLOR,
)

_BANNER_TEXT = (
    "You are running a lightweight model. Simple tasks will work well. "
    "For best results with complex documents, try a model with 7B+ parameters."
)


class CapabilityBanner(QWidget):
    """Dismissible banner shown when the active model has < 7B parameters.

    Signals:
        dismissed: emitted when the user clicks the X button.
    """

    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._user_dismissed: bool = False
        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self.hide()  # banner starts hidden; call show_banner() to display it

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setMaximumHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        # Colored left strip
        self._left_strip = QFrame()
        self._left_strip.setFixedWidth(4)
        self._left_strip.setObjectName("banner_strip")
        layout.addWidget(self._left_strip)

        # Info text
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)
        self._info_label = QLabel(_BANNER_TEXT)
        self._info_label.setFont(body_font)
        self._info_label.setObjectName("banner_label")
        self._info_label.setContentsMargins(8, 0, 8, 0)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._info_label, stretch=1)

        # Dismiss button
        self._dismiss_btn = QPushButton("✕")
        self._dismiss_btn.setObjectName("banner_dismiss_btn")
        self._dismiss_btn.setFont(body_font)
        self._dismiss_btn.setFixedSize(24, 24)
        layout.addWidget(self._dismiss_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"CapabilityBanner {{ background-color: {INFO_BANNER_BG_COLOR}; }}"
            f"QFrame#banner_strip {{ background-color: {PRIMARY_ACCENT_COLOR}; border: none; }}"
            f"QLabel#banner_label {{ color: {BODY_TEXT_COLOR}; background-color: transparent; }}"
            f"QPushButton#banner_dismiss_btn {{ border: none; background-color: transparent; "
            f"color: {BODY_TEXT_COLOR}; }}"
        )

    def _connect_signals(self) -> None:
        self._dismiss_btn.clicked.connect(self._on_dismiss_clicked)

    # ── Private handlers ──────────────────────────────────────────────────────

    def _on_dismiss_clicked(self) -> None:
        self._user_dismissed = True
        self.dismissed.emit()
        self.hide()

    # ── Public API ────────────────────────────────────────────────────────────

    def show_banner(self) -> None:
        """Make the banner visible and reset the dismissed state."""
        self._user_dismissed = False
        self.show()

    def hide_banner(self) -> None:
        """Hide the banner (does not mark as user-dismissed)."""
        self.hide()

    def is_dismissed(self) -> bool:
        """Return whether the user has actively dismissed the banner.

        Returns:
            True if the user clicked the dismiss button; False otherwise.
        """
        return self._user_dismissed
