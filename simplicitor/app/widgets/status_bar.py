# simplicitor/app/widgets/status_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_HEADING_PT, FONT_SIZE_BODY_PT,
    BORDER_COLOR, BODY_TEXT_COLOR, WHITE, SUCCESS_COLOR, ERROR_COLOR,
)


class TopBar(QWidget):
    """Top navigation bar.

    Shows app title, Ollama connectivity indicator, model selector dropdown,
    and settings gear button. Starts in disconnected state (red dot, no models).
    Phase 2 wires in OllamaWorker to call set_connected / set_disconnected.

    Signals:
        settings_requested: emitted when the gear button is clicked.
        model_changed: emitted with the newly selected model name.
    """

    settings_requested = Signal()
    model_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._apply_styles()
        self.set_disconnected()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(8)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        self._title_label = QLabel(APP_NAME)
        self._title_label.setFont(heading_font)

        # Connection indicator dot
        self._status_dot = QLabel("●")
        self._status_dot.setFont(body_font)
        self._status_dot.setFixedWidth(16)

        # Connection status text
        self._status_text = QLabel()
        self._status_text.setFont(body_font)

        # Model selector — disabled until Ollama connects (Phase 2)
        self._model_combo = QComboBox()
        self._model_combo.setMinimumWidth(200)
        self._model_combo.setFont(body_font)
        self._model_combo.setEnabled(False)
        self._model_combo.currentTextChanged.connect(self.model_changed)

        # Settings gear
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT))
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_requested)

        layout.addWidget(self._title_label)
        layout.addSpacing(8)
        layout.addWidget(self._status_dot)
        layout.addWidget(self._status_text)
        layout.addStretch()
        layout.addWidget(self._model_combo)
        layout.addSpacing(4)
        layout.addWidget(self._settings_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"TopBar {{ background-color: {WHITE}; border-bottom: 1px solid {BORDER_COLOR}; }}"
            f"QComboBox {{ color: {BODY_TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: 4px; padding: 2px 8px; background: {WHITE}; }}"
            f"QComboBox:disabled {{ color: #9CA3AF; }}"
            f"QPushButton {{ border: none; background: transparent; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton:hover {{ background-color: {BORDER_COLOR}; border-radius: 4px; }}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def set_connected(self, models: list[str], current_model: str = "") -> None:
        """Switch to connected state and populate the model dropdown."""
        self._status_dot.setStyleSheet(f"color: {SUCCESS_COLOR};")
        self._status_text.setText("Connected")
        self._model_combo.setEnabled(True)
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItems(models)
        if current_model and current_model in models:
            self._model_combo.setCurrentText(current_model)
        self._model_combo.blockSignals(False)

    def set_disconnected(self) -> None:
        """Switch to disconnected state and clear the model dropdown."""
        self._status_dot.setStyleSheet(f"color: {ERROR_COLOR};")
        self._status_text.setText("AI engine not connected")
        self._model_combo.setEnabled(False)
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.setPlaceholderText("No model selected")
        self._model_combo.blockSignals(False)

    def current_model(self) -> str:
        """Return the currently selected model name, or empty string."""
        return self._model_combo.currentText()
