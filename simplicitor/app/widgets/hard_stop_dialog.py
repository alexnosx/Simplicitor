# simplicitor/app/widgets/hard_stop_dialog.py
# Phase K: Two-choice modal shown when an uploaded deck cannot be templated.
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)

CHOICE_BUILTIN = "builtin"
CHOICE_CANCEL = "cancel"
_DIALOG_TITLE = "This deck can't be used as a template"


class HardStopDialog(QDialog):
    """Modal shown when import_template returns a hard stop.

    Offers exactly two actions when a built-in template is available: use a
    built-in, or cancel and rebuild. When no built-in is available (before
    Phase L) only the cancel/rebuild path is shown - no dead-end button. The
    built-in button appears automatically once the caller passes
    builtin_available=True (i.e. once built-ins ship).

    Purely presentational: the message is rendered verbatim (it is a
    template-structure diagnostic, not model output or user content).
    """

    def __init__(
        self, message: str, builtin_available: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._choice = CHOICE_CANCEL
        self._builtin_available = builtin_available
        self.setWindowTitle(_DIALOG_TITLE)
        self.setMinimumWidth(480)
        self._build_ui(message)
        self.setStyleSheet(f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}")

    def _build_ui(self, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        heading = QLabel(_DIALOG_TITLE)
        hf = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        hf.setWeight(QFont.Weight.DemiBold)
        heading.setFont(hf)
        layout.addWidget(heading)

        body = QLabel(message)
        body.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        body.setWordWrap(True)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self._cancel_btn = QPushButton("Cancel and rebuild with proper layouts")
        self._cancel_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        self._cancel_btn.clicked.connect(self._on_cancel)

        if self._builtin_available:
            self._builtin_btn = QPushButton("Use a built-in template")
            self._builtin_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
            self._builtin_btn.clicked.connect(self._on_builtin)
            buttons.addWidget(self._builtin_btn)

        buttons.addWidget(self._cancel_btn)
        layout.addLayout(buttons)

    def _on_builtin(self) -> None:
        self._choice = CHOICE_BUILTIN
        self.accept()

    def _on_cancel(self) -> None:
        self._choice = CHOICE_CANCEL
        self.reject()

    def choice(self) -> str:
        """Return the user's choice: CHOICE_BUILTIN or CHOICE_CANCEL."""
        return self._choice

    def has_builtin_button(self) -> bool:
        """True if the 'use a built-in' button was rendered."""
        return self._builtin_available
