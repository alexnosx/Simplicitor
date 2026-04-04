# simplicitor/app/widgets/create_panel.py
import logging
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QPlainTextEdit, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    GENERATE_FILE_TYPES, PROMPT_PLACEHOLDERS, MAX_PROMPT_CHARS,
    PANEL_BG_COLOR, PRIMARY_ACCENT_COLOR, BORDER_COLOR, BODY_TEXT_COLOR,
    DISABLED_COLOR, WHITE, BORDER_RADIUS_PX,
    HOVER_ACCENT_COLOR, BORDER_HOVER_COLOR,
    SUCCESS_COLOR, ERROR_COLOR,
    PROMPT_COMPLEXITY_THRESHOLD_CHARS, STYLING_KEYWORDS,
)
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class CreatePanel(QWidget):
    """Left panel: generate a new Office document from a prompt.

    Emits generate_requested(file_type, save_path, prompt) when Generate
    is clicked. The button stays disabled until set_ollama_connected(True)
    is called AND the prompt is non-empty.
    """

    generate_requested = Signal(str, str, str)  # file_type, save_path, prompt
    retry_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._ollama_connected: bool = False
        self._model_is_small: bool = False
        self._last_generated_path: str = ""
        self._build_ui()
        self._apply_styles()
        self._connect_signals()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        # Section heading
        heading = QLabel("Create")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        # File type selector
        type_label = QLabel("File type")
        type_label.setFont(body_font)
        self._type_combo = QComboBox()
        self._type_combo.addItems(GENERATE_FILE_TYPES)
        self._type_combo.setFont(body_font)
        layout.addWidget(type_label)
        layout.addWidget(self._type_combo)

        # Save location
        save_label = QLabel("Save to")
        save_label.setFont(body_font)
        save_row = QHBoxLayout()
        self._save_path_edit = QLineEdit(self._settings.generated_dir)
        self._save_path_edit.setFont(body_font)
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setFont(body_font)
        self._browse_btn.setFixedHeight(30)
        save_row.addWidget(self._save_path_edit)
        save_row.addWidget(self._browse_btn)
        layout.addWidget(save_label)
        layout.addLayout(save_row)

        # Prompt area
        prompt_label = QLabel("Describe what you need")
        prompt_label.setFont(body_font)
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(120)
        self._prompt_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._update_placeholder()
        layout.addWidget(prompt_label)
        layout.addWidget(self._prompt_edit)

        # Character counter
        self._char_counter = QLabel(f"0 / {MAX_PROMPT_CHARS}")
        self._char_counter.setFont(QFont(APP_FONT_FAMILY, 8))
        self._char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._char_counter)

        # Complex prompt tip (shown when small model + complex prompt)
        self._tip_label = QLabel(
            "Tip: Your model works best with short, clear prompts. "
            "Consider simplifying your request for better results."
        )
        self._tip_label.setFont(body_font)
        self._tip_label.setWordWrap(True)
        self._tip_label.setVisible(False)
        layout.addWidget(self._tip_label)

        # Generate button — disabled until Ollama connects and prompt is non-empty
        self._generate_btn = QPushButton("Generate")
        self._generate_btn.setObjectName("generate_btn")
        self._generate_btn.setFont(heading_font)
        self._generate_btn.setFixedHeight(40)
        self._generate_btn.setEnabled(False)
        layout.addWidget(self._generate_btn)

        # Status label (hidden until needed)
        self._status_label = QLabel()
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # Open file button (shown after successful generation)
        self._open_file_btn = QPushButton("Open file")
        self._open_file_btn.setObjectName("open_file_btn")
        self._open_file_btn.setFont(body_font)
        self._open_file_btn.setFixedHeight(32)
        self._open_file_btn.setVisible(False)
        layout.addWidget(self._open_file_btn)

        # Disconnected message (shown when Ollama not available)
        self._disconnected_widget = QWidget()
        disconnected_layout = QVBoxLayout(self._disconnected_widget)
        disconnected_layout.setContentsMargins(0, 8, 0, 0)
        disconnected_layout.setSpacing(6)

        self._disconnected_label = QLabel(
            "Simplicitor cannot find your AI engine.\nPlease start Ollama and click Retry."
        )
        self._disconnected_label.setFont(body_font)
        self._disconnected_label.setWordWrap(True)
        self._disconnected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._retry_btn = QPushButton("Retry")
        self._retry_btn.setObjectName("retry_btn")
        self._retry_btn.setFont(body_font)
        self._retry_btn.setFixedHeight(32)
        self._retry_btn.setFixedWidth(80)

        retry_row = QHBoxLayout()
        retry_row.addStretch()
        retry_row.addWidget(self._retry_btn)
        retry_row.addStretch()

        self._ollama_link = QLabel('<a href="https://ollama.com">How to start Ollama</a>')
        self._ollama_link.setFont(body_font)
        self._ollama_link.setOpenExternalLinks(True)
        self._ollama_link.setAlignment(Qt.AlignmentFlag.AlignCenter)

        disconnected_layout.addWidget(self._disconnected_label)
        disconnected_layout.addLayout(retry_row)
        disconnected_layout.addWidget(self._ollama_link)

        layout.addWidget(self._disconnected_widget)
        self._disconnected_widget.setVisible(True)

        layout.addStretch()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"CreatePanel {{ background-color: {PANEL_BG_COLOR}; }}"
            f"QPlainTextEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 6px; color: {BODY_TEXT_COLOR}; }}"
            f"QLineEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 4px 8px; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton#generate_btn {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; "
            f"border-radius: {BORDER_RADIUS_PX}px; font-weight: 600; }}"
            f"QPushButton#generate_btn:disabled {{ background-color: {DISABLED_COLOR}; }}"
            f"QPushButton#generate_btn:hover:enabled {{ background-color: {HOVER_ACCENT_COLOR}; }}"
            f"QPushButton#retry_btn {{ background-color: {BORDER_COLOR}; color: {BODY_TEXT_COLOR}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; }}"
            f"QPushButton#retry_btn:hover {{ background-color: {BORDER_HOVER_COLOR}; }}"
            f"QPushButton#open_file_btn {{ background-color: {BORDER_COLOR}; color: {BODY_TEXT_COLOR}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; }}"
            f"QPushButton#open_file_btn:hover {{ background-color: {BORDER_HOVER_COLOR}; }}"
        )

    def _connect_signals(self) -> None:
        self._type_combo.currentTextChanged.connect(self._update_placeholder)
        self._browse_btn.clicked.connect(self._browse_save_dir)
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._generate_btn.clicked.connect(self._on_generate_clicked)
        self._retry_btn.clicked.connect(self.retry_requested)
        self._open_file_btn.clicked.connect(self._on_open_file)

    # ── Private handlers ──────────────────────────────────────────────────────

    def _update_placeholder(self) -> None:
        file_type = self._type_combo.currentText()
        placeholder = PROMPT_PLACEHOLDERS.get(file_type, "Describe what you need…")
        self._prompt_edit.setPlaceholderText(placeholder)

    def _browse_save_dir(self) -> None:
        current = self._save_path_edit.text() or self._settings.generated_dir
        chosen = QFileDialog.getExistingDirectory(self, "Select Save Location", current)
        if chosen:
            self._save_path_edit.setText(chosen)

    def _on_prompt_changed(self) -> None:
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            cursor = self._prompt_edit.textCursor()
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            self._prompt_edit.setTextCursor(cursor)
        count = min(len(text), MAX_PROMPT_CHARS)
        self._char_counter.setText(f"{count} / {MAX_PROMPT_CHARS}")
        self._update_generate_btn_state()
        self._update_tip_visibility()

    def _on_generate_clicked(self) -> None:
        self.generate_requested.emit(
            self._type_combo.currentText(),
            self._save_path_edit.text(),
            self._prompt_edit.toPlainText().strip(),
        )

    def _update_generate_btn_state(self) -> None:
        """Enable Generate only when Ollama connected AND prompt is non-empty."""
        prompt_filled = bool(self._prompt_edit.toPlainText().strip())
        self._generate_btn.setEnabled(self._ollama_connected and prompt_filled)

    def _update_tip_visibility(self) -> None:
        """Show inline tip if small model active AND prompt is long or contains styling keywords."""
        text = self._prompt_edit.toPlainText()
        is_complex = (
            len(text) > PROMPT_COMPLEXITY_THRESHOLD_CHARS
            or any(kw in text.lower() for kw in STYLING_KEYWORDS)
        )
        self._tip_label.setVisible(self._model_is_small and is_complex)

    def _on_open_file(self) -> None:
        """Open the last generated file using the OS default application."""
        if self._last_generated_path:
            try:
                os.startfile(self._last_generated_path)
            except OSError as exc:
                logger.error("Could not open file %s: %s", self._last_generated_path, exc)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ollama_connected(self, connected: bool) -> None:
        """Enable or disable Generate based on Ollama connectivity.

        Args:
            connected: True when Ollama is reachable; False otherwise.
        """
        self._ollama_connected = connected
        self._update_generate_btn_state()
        self._disconnected_widget.setVisible(not connected)

    def set_generating(self, in_progress: bool) -> None:
        """Show or hide generation progress state.

        Args:
            in_progress: True when generation is underway; False when idle.
        """
        if not in_progress:
            self._update_generate_btn_state()
        else:
            self._generate_btn.setEnabled(False)
            self._open_file_btn.setVisible(False)
        self._generate_btn.setText("Generating\u2026" if in_progress else "Generate")

    def show_status(self, message: str, is_error: bool = False) -> None:
        """Show a status message below the Generate button.

        Args:
            message: The message text to display.
            is_error: If True, display message in error color; otherwise success color.
        """
        color = ERROR_COLOR if is_error else SUCCESS_COLOR
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)
        self._status_label.setVisible(True)

    def clear_status(self) -> None:
        """Hide the status message."""
        self._status_label.setVisible(False)
        self._status_label.setText("")

    def set_model_small(self, is_small: bool) -> None:
        """Called by MainWindow when model param count changes.

        Args:
            is_small: True if current model is under SMALL_MODEL_PARAM_THRESHOLD.
        """
        self._model_is_small = is_small
        self._update_tip_visibility()

    def show_open_file_btn(self, path: str) -> None:
        """Show the Open File button pointing at the given path.

        Args:
            path: Absolute path to the generated file.
        """
        self._last_generated_path = path
        self._open_file_btn.setVisible(True)
