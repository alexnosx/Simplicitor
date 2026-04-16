# simplicitor/app/widgets/edit_panel.py
import logging
import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY,
    BODY_TEXT_COLOR,
    BORDER_COLOR,
    BORDER_RADIUS_PX,
    DISABLED_COLOR,
    EDIT_PROMPT_PLACEHOLDERS,
    FONT_SIZE_BODY_PT,
    FONT_SIZE_HEADING_PT,
    HOVER_ACCENT_COLOR,
    BORDER_HOVER_COLOR,
    MAX_PROMPT_CHARS,
    PANEL_BG_COLOR,
    PRIMARY_ACCENT_COLOR,
    WHITE,
)
from app.config.settings import Settings
from app.widgets.drop_zone import DropZone
from app.widgets.file_list import FileList
from app.widgets.status_banner import StatusBanner

logger = logging.getLogger(__name__)


class EditPanel(QWidget):
    """Right panel: upload a file, describe changes, save the result (Phase 4).

    Emits ``save_requested(file_path, prompt)`` when Save is clicked.
    Save is enabled only when: Ollama connected, a file is selected, and
    the prompt is non-empty.
    """

    save_requested = Signal(str, str)  # file_path, prompt
    retry_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        """Initialise the EditPanel.

        Args:
            settings: Application settings (provides uploads_dir, backups_dir).
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._settings = settings
        self._ollama_connected: bool = False
        self._selected_file: str = ""
        self._last_saved_path: str = ""
        self._build_ui()
        self._apply_styles()
        self._connect_signals()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setObjectName("panelContainer")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)  # 16px panel + 8px inner padding
        layout.setSpacing(12)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        # Section heading
        heading = QLabel("Edit")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        # Drop zone
        self._drop_zone = DropZone()
        layout.addWidget(self._drop_zone)

        # Supported types hint
        types_label = QLabel("Supported: .docx  .xlsx  .pptx  .txt  .pdf")
        types_label.setFont(QFont(APP_FONT_FAMILY, 8))
        types_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(types_label)

        # File list
        file_list_label = QLabel("Uploaded files")
        file_list_label.setFont(body_font)
        self._file_list = FileList()
        self._file_list.setFont(body_font)
        self._file_list.setMinimumHeight(80)
        layout.addWidget(file_list_label)
        layout.addWidget(self._file_list)

        # Prompt area
        prompt_label = QLabel("Describe the change")
        prompt_label.setFont(body_font)
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(120)
        self._prompt_edit.setPlaceholderText(EDIT_PROMPT_PLACEHOLDERS["default"])
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
        layout.addSpacing(12)  # extra gap between counter and Save button

        # Save button — disabled until file selected + Ollama connected + prompt non-empty
        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("save_btn")
        self._save_btn.setFont(heading_font)
        self._save_btn.setFixedHeight(40)
        self._save_btn.setEnabled(False)
        layout.addWidget(self._save_btn)

        # Status banner (dismissible, hidden until needed)
        self._status_banner = StatusBanner()
        layout.addWidget(self._status_banner)

        # Open file button (shown after successful save)
        self._open_file_btn = QPushButton("Open file")
        self._open_file_btn.setObjectName("open_file_btn")
        self._open_file_btn.setFont(body_font)
        self._open_file_btn.setFixedHeight(32)
        self._open_file_btn.setVisible(False)
        layout.addWidget(self._open_file_btn)

        # Disconnected message
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
        self._retry_btn.setObjectName("retry_btn_edit")
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
            f"#panelContainer {{ background-color: {PANEL_BG_COLOR}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; }}"
            # Primary action button
            f"QPushButton#save_btn {{ background-color: {PRIMARY_ACCENT_COLOR}; color: white; "
            f"border: none; border-radius: {BORDER_RADIUS_PX}px; "
            f"padding: 10px 16px; font-size: 14px; font-weight: 600; }}"
            f"QPushButton#save_btn:hover {{ background-color: {HOVER_ACCENT_COLOR}; }}"
            f"QPushButton#save_btn:pressed {{ background-color: #1E40AF; }}"
            f"QPushButton#save_btn:disabled {{ background-color: {BORDER_COLOR}; "
            f"color: {DISABLED_COLOR}; }}"
            # Secondary button (Open file)
            f"QPushButton#open_file_btn {{ background-color: {WHITE}; "
            f"color: {BODY_TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 8px 14px; font-size: 13px; "
            f"font-weight: 500; }}"
            f"QPushButton#open_file_btn:hover {{ background-color: {PANEL_BG_COLOR}; "
            f"border-color: #9CA3AF; }}"
            f"QPushButton#open_file_btn:pressed {{ background-color: {BORDER_COLOR}; }}"
            f"QPushButton#open_file_btn:disabled {{ color: {DISABLED_COLOR}; "
            f"border-color: {BORDER_COLOR}; }}"
            # Retry button
            f"QPushButton#retry_btn_edit {{ background-color: {BORDER_COLOR}; "
            f"color: {BODY_TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; }}"
            f"QPushButton#retry_btn_edit:hover {{ background-color: {BORDER_HOVER_COLOR}; }}"
        )

    def _connect_signals(self) -> None:
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        self._file_list.file_selected.connect(self._on_file_selected)
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._retry_btn.clicked.connect(self.retry_requested)
        self._open_file_btn.clicked.connect(self._on_open_file)

    # ── Private handlers ──────────────────────────────────────────────────────

    def _on_file_dropped(self, file_path: str) -> None:
        """Copy the dropped/selected file to the uploads directory and add to list."""
        src = Path(file_path)
        uploads_dir = Path(self._settings.uploads_dir)
        try:
            uploads_dir.mkdir(parents=True, exist_ok=True)
            dest = uploads_dir / src.name
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            self._file_list.add_file(str(dest))
            self._selected_file = str(dest)
        except OSError as exc:
            logger.error("Could not copy file to uploads dir: %s", exc)
            self.show_status(f"Could not load file: {exc}", is_error=True)
            return
        self._update_save_btn_state()
        self._update_prompt_placeholder(src.suffix.lower())

    def _on_file_selected(self, file_path: str) -> None:
        self._selected_file = file_path
        self._update_save_btn_state()
        self._update_prompt_placeholder(Path(file_path).suffix.lower())

    def _on_prompt_changed(self) -> None:
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            cursor = self._prompt_edit.textCursor()
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            self._prompt_edit.setTextCursor(cursor)
        count = min(len(text), MAX_PROMPT_CHARS)
        self._char_counter.setText(f"{count} / {MAX_PROMPT_CHARS}")
        self._update_save_btn_state()

    def _on_save_clicked(self) -> None:
        if self._selected_file:
            self.save_requested.emit(
                self._selected_file,
                self._prompt_edit.toPlainText().strip(),
            )

    def _on_open_file(self) -> None:
        if self._last_saved_path:
            try:
                os.startfile(self._last_saved_path)
            except OSError as exc:
                logger.error("Could not open file %s: %s", self._last_saved_path, exc)

    def _update_save_btn_state(self) -> None:
        """Enable Save only when Ollama connected, file selected, and prompt non-empty."""
        prompt_filled = bool(self._prompt_edit.toPlainText().strip())
        self._save_btn.setEnabled(
            self._ollama_connected and bool(self._selected_file) and prompt_filled
        )

    def _update_prompt_placeholder(self, suffix: str) -> None:
        placeholder = EDIT_PROMPT_PLACEHOLDERS.get(suffix, EDIT_PROMPT_PLACEHOLDERS["default"])
        self._prompt_edit.setPlaceholderText(placeholder)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ollama_connected(self, connected: bool) -> None:
        """Show or hide the disconnected message and update Save button state.

        Args:
            connected: True when Ollama is reachable; False otherwise.
        """
        self._ollama_connected = connected
        self._update_save_btn_state()
        self._disconnected_widget.setVisible(not connected)

    def set_saving(self, in_progress: bool) -> None:
        """Disable/re-enable the Save button while the worker is running.

        Args:
            in_progress: True while saving; False when done.
        """
        if not in_progress:
            self._update_save_btn_state()
        else:
            self._save_btn.setEnabled(False)
            self._open_file_btn.setVisible(False)
        self._save_btn.setText("Saving\u2026" if in_progress else "Save")

    def show_status(
        self, message: str, is_error: bool = False, secondary: str = "", tooltip: str = ""
    ) -> None:
        """Show a status message below the Save button.

        Args:
            message: Short primary message text to display.
            is_error: True for red text (error), False for green (success).
            secondary: Optional secondary line (e.g. truncated file paths) in muted gray.
            tooltip: Full text shown on hover over the secondary line.
        """
        self._status_banner.show_message(message, is_error, secondary, tooltip)

    def clear_status(self) -> None:
        """Hide the status banner."""
        self._status_banner.hide_message()

    def clear_prompt(self) -> None:
        """Clear the prompt text area and reset the character counter."""
        self._prompt_edit.clear()
        self._char_counter.setText(f"0 / {MAX_PROMPT_CHARS}")

    def show_open_file_btn(self, path: str) -> None:
        """Show the Open File button for the given path.

        Args:
            path: Absolute path to the saved file.
        """
        self._last_saved_path = path
        self._open_file_btn.setVisible(True)
