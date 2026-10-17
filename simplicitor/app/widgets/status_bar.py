# simplicitor/app/widgets/status_bar.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QPushButton, QButtonGroup
from PySide6.QtCore import QPointF, QSize, Signal, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_HEADING_PT, FONT_SIZE_BODY_PT,
    BORDER_COLOR, BODY_TEXT_COLOR, WHITE, SUCCESS_COLOR, ERROR_COLOR, PRIMARY_ACCENT_COLOR,
    MUTED_TEXT_COLOR,
)
from app.config.styles import header_styles
from app.utils.file_utils import resource_path
from app.version import __version__


def _mode_icon(edit: bool) -> QIcon:
    """Draw the mockup's document-plus/document-pencil marks with Qt only."""
    page = QPainterPath(QPointF(12, 22))
    page.lineTo(6, 22)
    page.quadTo(4, 22, 4, 20)
    page.lineTo(4, 4)
    page.quadTo(4, 2, 6, 2)
    page.lineTo(14, 2)
    page.lineTo(20, 8)
    page.lineTo(20, 11)
    page.moveTo(14, 2)
    page.lineTo(14, 8)
    page.lineTo(20, 8)
    pencil = QPainterPath(QPointF(13, 20))
    for x, y in ((14, 16), (19, 11), (22, 14), (17, 19), (13, 20)):
        pencil.lineTo(x, y)
    pencil.moveTo(17, 13)
    pencil.lineTo(20, 16)
    icon = QIcon()
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Disabled):
        for state in (QIcon.State.Off, QIcon.State.On):
            colour = PRIMARY_ACCENT_COLOR if (
                mode != QIcon.Mode.Disabled and
                (state == QIcon.State.On or mode == QIcon.Mode.Active)
            ) else MUTED_TEXT_COLOR
            pixmap = QPixmap(72, 72)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(3, 3)
            painter.setPen(QPen(QColor(colour), 1.6, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(page)
            if edit:
                painter.drawPath(pencil)
            else:
                painter.drawLine(QPointF(17, 14), QPointF(17, 22))
                painter.drawLine(QPointF(13, 18), QPointF(21, 18))
            painter.end()
            pixmap.setDevicePixelRatio(3)
            icon.addPixmap(pixmap, mode, state)
    return icon


class TopBar(QWidget):
    """Two-row brand/navigation header; local model selection lives in Settings.

    The hidden combo retains discovery and model-change ownership. Navigation
    emits the existing mode/settings signals and starts disconnected.
    """

    settings_requested = Signal()
    model_changed = Signal(str)
    mode_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._apply_styles()
        self.set_disconnected()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)
        self._brand_row = QWidget()
        self._brand_row.setObjectName("azureBrandRow")
        brand = QHBoxLayout(self._brand_row)
        brand.setContentsMargins(24, 14, 24, 14)
        brand.setSpacing(12)
        self._brand_icon = QLabel()
        self._brand_icon.setPixmap(QIcon(str(resource_path(
            "assets/icons/simplicitor.ico"))).pixmap(40, 40))
        self._brand_icon.setFixedSize(40, 40)
        brand.addWidget(self._brand_icon)
        self._branding = QWidget()
        branding = QVBoxLayout(self._branding)
        branding.setContentsMargins(0, 0, 0, 0)
        branding.setSpacing(2)
        name = QHBoxLayout()
        name.setSpacing(10)
        title_font = QFont(APP_FONT_FAMILY, 17)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title_label = QLabel(APP_NAME)
        self._title_label.setFont(title_font)
        self._version_label = QLabel(__version__)
        self._version_label.setFont(body_font)
        name.addWidget(self._title_label)
        name.addWidget(self._version_label)
        name.addStretch()
        branding.addLayout(name)
        self._powered_label = QLabel("Powered by your local LLM")
        powered_font = QFont(body_font)
        powered_font.setItalic(True)
        self._powered_label.setFont(powered_font)
        branding.addWidget(self._powered_label)
        brand.addWidget(self._branding)
        brand.addStretch()
        self._tagline_label = QLabel("Your documents. Your computer. Your control.")
        self._tagline_label.setFont(body_font)
        brand.addWidget(self._tagline_label)
        layout.addWidget(self._brand_row)
        self._navigation_row = QWidget()
        self._navigation_row.setObjectName("azureNavigationRow")
        navigation = QHBoxLayout(self._navigation_row)
        navigation.setContentsMargins(24, 6, 24, 6)
        navigation.setSpacing(8)
        layout.addWidget(self._navigation_row)

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
        self._model_combo.hide()  # Selection is presented in Settings.

        # Settings owns the visible model selector
        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setMinimumSize(82, 36)
        self._settings_btn.setFont(body_font)
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settings_requested)

        self._create_mode_btn = QPushButton("Create new")
        self._edit_mode_btn = QPushButton("Edit document")
        self._create_mode_btn.setIcon(_mode_icon(edit=False))
        self._edit_mode_btn.setIcon(_mode_icon(edit=True))
        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        for button in (self._create_mode_btn, self._edit_mode_btn):
            button.setCheckable(True)
            button.setFont(body_font)
            button.setIconSize(QSize(20, 20))
            button.setMinimumHeight(36)
            self._mode_group.addButton(button)
        self._create_mode_btn.setChecked(True)
        self._create_mode_btn.clicked.connect(lambda: self.mode_changed.emit("create"))
        self._edit_mode_btn.clicked.connect(lambda: self.mode_changed.emit("edit"))
        navigation.addWidget(self._create_mode_btn)
        navigation.addWidget(self._edit_mode_btn)
        navigation.addStretch()
        navigation.addWidget(self._status_dot)
        navigation.addWidget(self._status_text)
        navigation.addWidget(self._settings_btn)

    def _apply_styles(self) -> None:
        self.setStyleSheet(header_styles())

    # ── Public API ────────────────────────────────────────────────────────────

    def set_connected(self, models: list[str], current_model: str = "") -> None:
        """Switch to connected state.

        Keep an existing selection when installed. Otherwise choose the loaded
        model or the first installed model. Discovery never replaces a deliberate
        selection with a different loaded model.

        Args:
            models: Full list of installed model names from /api/tags.
            current_model: The model currently loaded in Ollama, or "" if none.
        """
        self._status_dot.setStyleSheet(f"color: {SUCCESS_COLOR};")
        self._status_text.setText("Local AI ready")
        # Capture what was selected before rebuilding so we can detect a real change.
        previous_selection = self._model_combo.currentText()
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        choices = list(dict.fromkeys(models + ([current_model] if current_model else [])))
        if choices:
            self._model_combo.addItems(choices)
            selected = previous_selection if previous_selection in choices else current_model or choices[0]
            self._model_combo.setCurrentText(selected)
            self._model_combo.setEnabled(True)
        else:
            self._model_combo.setPlaceholderText("No model selected")
            self._model_combo.setEnabled(False)
        self._model_combo.blockSignals(False)
        # Only notify subscribers when the selection actually changed (not on every poll).
        selected = self._model_combo.currentText()
        if selected != previous_selection:
            self.model_changed.emit(selected)

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

    def mode(self) -> str:
        """Return the selected workspace mode."""
        return "edit" if self._edit_mode_btn.isChecked() else "create"

    def set_mode(self, mode: str) -> None:
        """Select a mode without emitting a user-switch signal."""
        (self._edit_mode_btn if mode == "edit" else self._create_mode_btn).setChecked(True)
