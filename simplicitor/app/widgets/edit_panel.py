# simplicitor/app/widgets/edit_panel.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QPlainTextEdit, QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    MAX_PROMPT_CHARS, PANEL_BG_COLOR, PRIMARY_ACCENT_COLOR, BORDER_COLOR,
    BODY_TEXT_COLOR, DISABLED_COLOR, WHITE, BORDER_RADIUS_PX,
)
from app.config.settings import Settings


class EditPanel(QWidget):
    """Right panel: upload a file, describe changes, save the result.

    Phase 1: drop zone is a styled placeholder label; file list is an
    empty QListWidget. Phase 4 adds full drag-and-drop and FileList logic.

    Emits save_requested(file_path, prompt) when Save is clicked.
    Save stays disabled until Phase 4 wires up file selection.
    """

    save_requested = Signal(str, str)  # file_path, prompt

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
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
        heading = QLabel("Edit")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        # Drop zone placeholder (Phase 4 replaces with real DropZone widget)
        self._drop_zone_label = QLabel("Drop files here or click to browse")
        self._drop_zone_label.setObjectName("drop_zone_label")
        self._drop_zone_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_zone_label.setFont(body_font)
        self._drop_zone_label.setFixedHeight(80)
        layout.addWidget(self._drop_zone_label)

        # Supported file types hint
        types_label = QLabel("Supported: .docx, .xlsx, .pptx, .txt, .pdf")
        types_label.setFont(QFont(APP_FONT_FAMILY, 8))
        types_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(types_label)

        # File list (empty in Phase 1; Phase 4 populates it)
        file_list_label = QLabel("Uploaded files")
        file_list_label.setFont(body_font)
        self._file_list = QListWidget()
        self._file_list.setFont(body_font)
        self._file_list.setMinimumHeight(80)
        layout.addWidget(file_list_label)
        layout.addWidget(self._file_list)

        # Prompt area
        prompt_label = QLabel("Describe the change")
        prompt_label.setFont(body_font)
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(100)
        self._prompt_edit.setPlaceholderText(
            "Select a file above, then describe what you want to change"
        )
        self._prompt_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(prompt_label)
        layout.addWidget(self._prompt_edit)

        # Character counter
        self._char_counter = QLabel(f"0 / {MAX_PROMPT_CHARS}")
        self._char_counter.setFont(QFont(APP_FONT_FAMILY, 8))
        self._char_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._char_counter)

        # Save button — disabled until file selected + Ollama connected (Phase 4)
        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("save_btn")
        self._save_btn.setFont(heading_font)
        self._save_btn.setFixedHeight(40)
        self._save_btn.setEnabled(False)
        layout.addWidget(self._save_btn)

        # Status label (hidden until needed)
        self._status_label = QLabel()
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        layout.addStretch()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"EditPanel {{ background-color: {PANEL_BG_COLOR}; }}"
            f"QLabel#drop_zone_label {{ border: 2px dashed {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; color: {BODY_TEXT_COLOR}; }}"
            f"QListWidget {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; color: {BODY_TEXT_COLOR}; }}"
            f"QListWidget::item:selected {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; }}"
            f"QPlainTextEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 6px; color: {BODY_TEXT_COLOR}; }}"
            f"QPushButton#save_btn {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; "
            f"border-radius: {BORDER_RADIUS_PX}px; font-weight: 600; }}"
            f"QPushButton#save_btn:disabled {{ background-color: {DISABLED_COLOR}; }}"
            f"QPushButton#save_btn:hover:enabled {{ background-color: #1D4ED8; }}"
        )

    def _connect_signals(self) -> None:
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._save_btn.clicked.connect(self._on_save_clicked)

    # ── Private handlers ──────────────────────────────────────────────────────

    def _on_prompt_changed(self) -> None:
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            cursor = self._prompt_edit.textCursor()
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            self._prompt_edit.setTextCursor(cursor)
        count = min(len(text), MAX_PROMPT_CHARS)
        self._char_counter.setText(f"{count} / {MAX_PROMPT_CHARS}")

    def _on_save_clicked(self) -> None:
        self.save_requested.emit("", self._prompt_edit.toPlainText().strip())

    # ── Public API ────────────────────────────────────────────────────────────

    def show_status(self, message: str, is_error: bool = False) -> None:
        """Show a status message below the Save button."""
        color = "#DC2626" if is_error else "#16A34A"
        self._status_label.setStyleSheet(f"color: {color};")
        self._status_label.setText(message)
        self._status_label.setVisible(True)

    def clear_status(self) -> None:
        """Hide the status message."""
        self._status_label.setVisible(False)
        self._status_label.setText("")
