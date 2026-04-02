# simplicitor/app/widgets/status_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_HEADING_PT, FONT_SIZE_BODY_PT,
    BORDER_COLOR, BODY_TEXT_COLOR, WHITE,
)


class TopBar(QWidget):
    """Top navigation bar for Phase 1.

    Shows the app title and a settings gear button.
    Phase 2 adds: connection indicator, model name label, model dropdown.

    Signals:
        settings_requested: emitted when the gear button is clicked.
    """

    settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._apply_styles()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)

        self._title_label = QLabel(APP_NAME)
        self._title_label.setFont(heading_font)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT))
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_requested)

        layout.addWidget(self._title_label)
        layout.addStretch()
        layout.addWidget(self._settings_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"TopBar {{ background-color: {WHITE}; border-bottom: 1px solid {BORDER_COLOR}; }}"
            f"QPushButton {{ border: none; background: transparent; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton:hover {{ background-color: {BORDER_COLOR}; border-radius: 4px; }}"
        )
