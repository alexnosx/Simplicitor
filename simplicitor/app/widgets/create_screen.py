"""One Create workspace for prompt generation and read-only source extraction."""
import logging
import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    BORDER_COLOR, GENERATE_FILE_TYPES, MAX_PROMPT_CHARS, PRIMARY_ACCENT_COLOR,
    PROMPT_COMPLEXITY_THRESHOLD_CHARS, PROMPT_PLACEHOLDERS, STYLING_KEYWORDS,
    EXTRACTION_SOURCE_FILTER, TEMPLATE_FILE_TYPE,
)
from app.config.settings import Settings
from app.widgets.plain_labels import describe_coverage
from app.widgets.status_banner import StatusBanner
from app.widgets.step_indicator import StepIndicator
from app.workers.extraction_worker import ExtractionSetup
from extraction.models import ExtractionProfile

logger = logging.getLogger(__name__)
EXCEL = "Excel (.xlsx)"
SOURCE_SUFFIXES = {".docx", ".pdf"}
SOURCES_NOTE = ("Files you add are turned into an Excel table. "
                "Reports from files come in a later version.")
ROUTE_PROMPT = ["Describe", "Save"]
ROUTE_SOURCES = ["Describe", "Choose columns", "Review and save"]


class CreateScreen(QWidget):
    """Emit frozen work requests and display results supplied by GUI-thread slots."""

    generate_requested = Signal(str, str, str)
    template_requested = Signal()
    file_type_changed = Signal(str)
    retry_requested = Signal()
    inspect_requested = Signal(object)
    propose_requested = Signal(object)
    extract_requested = Signal(object)
    cancel_requested = Signal()
    save_requested = Signal(object, bool)
    setup_changed = Signal()
    busy_changed = Signal(bool)

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._save_dir = settings.generated_dir
        self._paths: tuple[Path, ...] = ()
        self._documents: tuple = ()
        self._inspecting = self._confirmed = self._pending_confirm = self._loading = False
        self._busy = self._generating = self._connected = self._saving = False
        self._model = ""
        self._model_is_small = self._template_loaded = False
        self._candidate = None
        self._cells: dict = {}
        self._last_generated_path = ""
        self.setAcceptDrops(True)
        self.setStyleSheet(
            f"QFrame#documentCard {{ background: white; border: 1px solid {BORDER_COLOR}; "
            "border-radius: 4px; }"
            f"QPushButton[primary='true'] {{ background: {PRIMARY_ACCENT_COLOR}; color: white; "
            "border: none; border-radius: 4px; padding: 8px 14px; font-weight: 600; }"
            "QPushButton[primary='true']:disabled { background: #E5E7EB; color: #747B87; }"
            f"QPushButton[link='true'] {{ color: {PRIMARY_ACCENT_COLOR}; border: none; "
            "background: transparent; text-align: left; padding: 3px 0; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 20)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Create a new file")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        self._caption = QLabel("Describe what you need.")
        self._caption.setStyleSheet("color: #626B78;")
        heading.addWidget(title)
        heading.addWidget(self._caption)
        heading.addStretch()
        self._steps = StepIndicator()
        self._pages = QStackedWidget()
        self._describe_page = self._build_describe_page()
        self._saved_page = self._build_saved_page()
        self._pages.addWidget(self._describe_page)
        self._pages.addWidget(self._saved_page)
        self._status = StatusBanner()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self.cancel_requested)
        footer = QHBoxLayout()
        footer.addWidget(self._status, stretch=1)
        footer.addWidget(self._cancel_btn)
        layout.addLayout(heading)
        layout.addWidget(self._steps)
        layout.addWidget(self._pages, stretch=1)
        layout.addLayout(footer)
        self._prompt_edit.textChanged.connect(self._setup_edited)
        self._type_combo.currentTextChanged.connect(self._type_changed)
        self._prompt_edit.setPlaceholderText(PROMPT_PLACEHOLDERS[self.file_type()])
        self._refresh()

    @staticmethod
    def _card() -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("documentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        return card, layout

    def _build_describe_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)
        describe, column = self._card()
        column.addWidget(QLabel("What do you want to create?"))
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setMinimumHeight(116)
        self._prompt_edit.setMaximumHeight(180)
        column.addWidget(self._prompt_edit)
        fields = QHBoxLayout()
        types = QVBoxLayout()
        types.addWidget(QLabel("File type"))
        self._type_combo = QComboBox()
        for label in GENERATE_FILE_TYPES:
            self._type_combo.addItem(label.split(" (", 1)[0], label)
        types.addWidget(self._type_combo)
        self._template_btn = QPushButton("Use a template")
        self._template_btn.setProperty("link", True)
        self._template_btn.clicked.connect(self.template_requested)
        self._template_name = QLabel()
        self._template_name.setTextFormat(Qt.TextFormat.PlainText)
        types.addWidget(self._template_btn)
        types.addWidget(self._template_name)
        types.addStretch()
        self._save_folder = QWidget()
        save = QVBoxLayout(self._save_folder)
        save.setContentsMargins(0, 0, 0, 0)
        save.addWidget(QLabel("Save to"))
        self._folder_label = QLabel(self._save_dir)
        self._folder_label.setWordWrap(True)
        self._folder_label.setTextFormat(Qt.TextFormat.PlainText)
        self._change_folder_btn = QPushButton("Change")
        self._change_folder_btn.setProperty("link", True)
        self._change_folder_btn.clicked.connect(self._browse_save_dir)
        save.addWidget(self._folder_label)
        save.addWidget(self._change_folder_btn)
        save.addStretch()
        fields.addLayout(types, 1)
        fields.addWidget(self._save_folder, 1)
        column.addLayout(fields)
        self._tip_label = QLabel(
            "Tip: Your model works best with short, clear prompts. "
            "Consider simplifying your request for better results.")
        self._tip_label.setWordWrap(True)
        column.addWidget(self._tip_label)
        self._disconnected_label = QLabel(
            "Simplicitor cannot find your AI engine.\nPlease start Ollama and click Retry.")
        self._disconnected_label.setWordWrap(True)
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.clicked.connect(self.retry_requested)
        column.addWidget(self._disconnected_label)
        column.addWidget(self._retry_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._primary_btn = QPushButton("Create file")
        self._primary_btn.setProperty("primary", True)
        self._primary_btn.clicked.connect(self._primary_clicked)
        column.addWidget(self._primary_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        column.addStretch()
        source, sources = self._card()
        sources.addWidget(QLabel("Source files (optional)"))
        drop = QHBoxLayout()
        hint = QLabel("Drop Word files or PDFs with selectable text here, or")
        hint.setWordWrap(True)
        self._browse_btn = QPushButton("browse")
        self._browse_btn.setProperty("link", True)
        self._browse_btn.clicked.connect(self._add_sources)
        drop.addWidget(hint, 1)
        drop.addWidget(self._browse_btn)
        sources.addLayout(drop)
        self._source_list = QListWidget()
        self._source_list.setMaximumHeight(150)
        sources.addWidget(self._source_list)
        self._reading_label = QLabel("Reading your files...")
        self._read_again_btn = QPushButton("Read files again")
        self._read_again_btn.clicked.connect(self._read_again)
        sources.addWidget(self._reading_label)
        sources.addWidget(self._read_again_btn)
        self._sources_note = QLabel(SOURCES_NOTE)
        self._sources_note.setWordWrap(True)
        self._sources_note.setStyleSheet("background: #EFF6FF; padding: 10px;")
        sources.addWidget(self._sources_note)
        self._source_coverage = QPlainTextEdit()
        self._source_coverage.setReadOnly(True)
        self._source_coverage.setMaximumHeight(100)
        self._source_coverage.hide()
        self._coverage_view = self._source_coverage
        sources.addWidget(self._source_coverage)
        sources.addStretch()
        row.addWidget(describe, 65)
        row.addWidget(source, 35)
        return page

    def _build_saved_page(self) -> QWidget:
        page, layout = self._card()
        self._saved_label = QLabel()
        self._saved_label.setTextFormat(Qt.TextFormat.PlainText)
        self._saved_label.setWordWrap(True)
        self._saved_label.setStyleSheet("background: #F0F8F2; color: #237443; padding: 12px;")
        self._open_file_btn = QPushButton("Open file")
        self._open_file_btn.setProperty("primary", True)
        self._open_file_btn.clicked.connect(self._on_open_file)
        self._another_btn = QPushButton("Create another file")
        self._another_btn.clicked.connect(self._start_another)
        actions = QHBoxLayout()
        actions.addWidget(self._open_file_btn)
        actions.addWidget(self._another_btn)
        actions.addStretch()
        layout.addWidget(self._saved_label)
        layout.addLayout(actions)
        layout.addStretch()
        return page

    def _start_another(self) -> None:
        if self._busy:
            return
        self._loading = True
        self._prompt_edit.clear()
        self._loading = False
        self.set_template_loaded(False)
        if hasattr(self, "_columns_table"):
            self._columns_table.setRowCount(0)
            self._column_settings.clear()
        self.set_paths(())
        self.set_file_type(GENERATE_FILE_TYPES[0])
        self._last_generated_path = ""
        self._pages.setCurrentWidget(self._describe_page)
        self._steps.set_current(0)
        self._caption.setText("Describe what you need.")
        self.clear_status()
        self._refresh()

    def _add_sources(self) -> None:
        if self._busy:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Choose source documents", "", EXTRACTION_SOURCE_FILTER)
        if paths:
            self.set_paths(self._paths + tuple(Path(path) for path in paths))

    def _remove_index(self, index: int) -> None:
        if not self._busy:
            self.set_paths(tuple(path for i, path in enumerate(self._paths) if i != index))

    def _remove_sources(self) -> None:
        selected = {self._source_list.row(item) for item in self._source_list.selectedItems()}
        self.set_paths(tuple(path for i, path in enumerate(self._paths) if i not in selected))

    def set_paths(self, paths) -> None:
        """Keep attachments independently and request inspection after source changes."""
        if self._busy:
            return
        self._paths = tuple(Path(path) for path in paths if Path(path).suffix.lower() in SOURCE_SUFFIXES)
        self._source_list.clear()
        for index, path in enumerate(self._paths):
            item = QListWidgetItem(path.name)
            self._source_list.addItem(item)
            holder = QWidget()
            row = QHBoxLayout(holder)
            row.setContentsMargins(2, 2, 2, 2)
            label = QLabel(path.name)
            label.setTextFormat(Qt.TextFormat.PlainText)
            remove = QPushButton("Remove")
            remove.clicked.connect(lambda _checked=False, i=index: self._remove_index(i))
            row.addWidget(label, 1)
            row.addWidget(remove)
            item.setSizeHint(holder.sizeHint())
            self._source_list.setItemWidget(item, holder)
        self._documents = ()
        self._inspecting = bool(self._paths)
        self._force_excel_if_sources()
        self._setup_edited()
        if self._paths:
            self.inspect_requested.emit(self.snapshot(False))

    def _force_excel_if_sources(self) -> None:
        if self._paths and self.file_type() != EXCEL:
            self._type_combo.blockSignals(True)
            self.set_file_type(EXCEL)
            self._type_combo.blockSignals(False)
            self._prompt_edit.setPlaceholderText(PROMPT_PLACEHOLDERS[EXCEL])
            self.set_template_loaded(False)
            self.file_type_changed.emit(EXCEL)

    def _read_again(self) -> None:
        if self._paths and not self._busy:
            self._inspecting = True
            self._refresh()
            self.inspect_requested.emit(self.snapshot(False))

    def dragEnterEvent(self, event) -> None:
        """Accept supported local-file drops only while the setup is editable."""
        urls = event.mimeData().urls()
        if (not self._busy and urls and all(url.isLocalFile()
                and Path(url.toLocalFile()).suffix.lower() in SOURCE_SUFFIXES for url in urls)):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Append a supported drop without deduplicating attachment names."""
        urls = event.mimeData().urls()
        if (not self._busy and urls and all(url.isLocalFile()
                and Path(url.toLocalFile()).suffix.lower() in SOURCE_SUFFIXES for url in urls)):
            self.set_paths(self._paths + tuple(Path(url.toLocalFile()) for url in urls))
            event.acceptProposedAction()

    @Slot(object)
    def show_inspection(self, documents) -> None:
        """Store source metadata and show its reading problems without internal codes."""
        self._documents = tuple(documents)
        self._set_coverage("\n".join(describe_coverage(doc.label, issue.anchor, issue.code)
            for doc in self._documents for issue in doc.issues))
        self.inspection_finished()
        if hasattr(self, "_columns_table"):
            self._update_details()

    def inspection_finished(self) -> None:
        """End reading after success, failure or cancellation without clearing setup."""
        self._inspecting = False
        self._refresh()

    def resume_pending_confirmation(self) -> None:
        """Resume confirmation only after MainWindow releases the inspection thread."""
        if self._pending_confirm and self._documents:
            self._pending_confirm = False
            self._confirm_and_extract()

    def _setup_edited(self, *_args) -> None:
        if self._loading:
            return
        text = self._prompt_edit.toPlainText()
        if len(text) > MAX_PROMPT_CHARS:
            position = self._prompt_edit.textCursor().position()
            self._prompt_edit.blockSignals(True)
            self._prompt_edit.setPlainText(text[:MAX_PROMPT_CHARS])
            cursor = self._prompt_edit.textCursor()
            cursor.setPosition(min(position, MAX_PROMPT_CHARS))
            self._prompt_edit.setTextCursor(cursor)
            self._prompt_edit.blockSignals(False)
        self._confirmed = self._pending_confirm = False
        self.clear_review()
        self.setup_changed.emit()
        self._refresh()

    def _type_changed(self, _display_name: str) -> None:
        label = self.file_type()
        self._prompt_edit.setPlaceholderText(PROMPT_PLACEHOLDERS.get(label, ""))
        self.file_type_changed.emit(label)
        self._setup_edited()

    def file_type(self) -> str:
        """Return the existing backend type label, independently of display text."""
        return self._type_combo.currentData()

    def set_file_type(self, label: str) -> None:
        """Select a backend type while preserving the ordinary change signal."""
        self._type_combo.setCurrentIndex(self._type_combo.findData(label))

    def set_model(self, model: str) -> None:
        """Use the selected local model for subsequent frozen requests."""
        self._model = model
        self._refresh()

    def set_ollama_connected(self, connected: bool) -> None:
        """Gate model requests while retaining offline source setup and saved results."""
        self._connected = connected
        self._refresh()

    def set_busy(self, busy: bool, saving: bool = False) -> None:
        """Freeze setup individually while keeping cancellable work outside the pages."""
        self._busy, self._saving = busy, saving
        for control in self._setup_controls():
            control.setEnabled(not busy)
        self._cancel_btn.setEnabled(busy and not saving and not self._generating)
        self.busy_changed.emit(busy)
        self._refresh()

    def _setup_controls(self) -> tuple:
        return (self._prompt_edit, self._type_combo, self._source_list, self._browse_btn,
                self._change_folder_btn, self._template_btn, self._retry_btn, self._read_again_btn,
                self._primary_btn, self._open_file_btn, self._another_btn)

    def set_generating(self, in_progress: bool) -> None:
        """Display generation progress without allowing a duplicate request."""
        self._generating = in_progress
        self._cancel_btn.setEnabled(self._busy and not self._saving and not in_progress)
        self._refresh()

    @Slot(str)
    @Slot(str, bool)
    @Slot(str, bool, str, str)
    def show_status(self, message: str, is_error: bool = False,
                    secondary: str = "", tooltip: str = "") -> None:
        """Show sanitized status text and an optional user-visible output label."""
        self._status.show_message(message, is_error, secondary, tooltip)

    def clear_status(self) -> None:
        """Hide status from the preceding action."""
        self._status.hide_message()

    @Slot(str, object)
    def show_failure(self, message: str, issues: tuple) -> None:
        """Retain editable instructions and show plain source-reading problems."""
        self.show_status(message, True)
        if issues:
            labels = {doc.source_id: doc.label for doc in self._documents}
            self._set_coverage("\n".join(describe_coverage(
                labels.get(issue.source_id, "Source file"), issue.anchor, issue.code)
                for issue in issues))

    def _set_coverage(self, text: str) -> None:
        for view in {self._source_coverage, self._coverage_view}:
            view.setPlainText(text)
            view.setVisible(bool(text))

    def clear_prompt(self) -> None:
        """Clear instructions after successful generation."""
        self._prompt_edit.clear()

    def set_model_small(self, is_small: bool) -> None:
        """Keep the existing non-blocking short-prompt hint."""
        self._model_is_small = is_small
        self._refresh()

    def set_template_loaded(self, loaded: bool, name: str = "") -> None:
        """Reflect the selected PowerPoint template without changing its engine."""
        self._template_loaded = loaded
        self._template_name.setText("Template: " + (name or "selected") if loaded else "")
        self._refresh()

    def show_open_file_btn(self, path: str) -> None:
        """Show the saved-file page and retain its path for the explicit Open action."""
        self._last_generated_path = path
        self._saved_label.setText("Saved: " + Path(path).name)
        self._pages.setCurrentWidget(self._saved_page)
        self._steps.set_steps(ROUTE_SOURCES if self._paths else ROUTE_PROMPT)
        self._steps.set_current(2 if self._paths else 1)
        self._caption.setText("Your file is ready.")

    def _on_open_file(self) -> None:
        if self._last_generated_path:
            try:
                os.startfile(self._last_generated_path)
            except OSError as exc:
                logger.error("Could not open saved file (%s)", type(exc).__name__)
                self.show_status("Could not open the saved file. Open it from its folder.", True)

    def _browse_save_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Save to folder", self._save_dir)
        if chosen:
            self._save_dir = chosen
            self._folder_label.setText(chosen)

    def current_columns(self) -> tuple:
        """Return editor columns; the editor is added in C2.5."""
        return ()

    def snapshot(self, include_columns: bool = True) -> ExtractionSetup:
        """Freeze setup for the worker without sharing live widget state."""
        return ExtractionSetup(self._paths, self._prompt_edit.toPlainText().strip(),
            self.current_columns() if include_columns else (), ExtractionProfile(self._model))

    def candidate(self):
        """Return the current saved candidate, if any."""
        return self._candidate

    def columns_confirmed(self) -> bool:
        """Return whether the current columns passed confirmation."""
        return self._confirmed

    def disable_cancel(self) -> None:
        """Prevent another cancellation while an existing request settles."""
        self._cancel_btn.setEnabled(False)

    def clear_review(self) -> None:
        """Invalidate the preceding candidate when setup changes."""
        self._candidate, self._cells = None, {}
        self._set_coverage("")
        self._refresh()

    def _refresh(self) -> None:
        has_sources = bool(self._paths)
        for index in range(self._type_combo.count()):
            self._type_combo.model().item(index).setEnabled(
                not has_sources or self._type_combo.itemData(index) == EXCEL)
        self._sources_note.setVisible(has_sources)
        self._save_folder.setVisible(not has_sources)
        self._reading_label.setVisible(self._inspecting)
        self._read_again_btn.setVisible(has_sources and not self._documents and not self._inspecting)
        self._read_again_btn.setEnabled(not self._busy)
        self._steps.set_steps(ROUTE_SOURCES if has_sources else ROUTE_PROMPT)
        self._retry_btn.setVisible(not self._connected)
        self._disconnected_label.setVisible(not self._connected)
        ready = (not self._busy and not self._generating and self._connected and bool(self._model)
                 and bool(self._prompt_edit.toPlainText().strip()))
        self._primary_btn.setText("Next: choose columns" if has_sources
                                  else "Creating..." if self._generating else "Create file")
        self._primary_btn.setEnabled(ready and (not has_sources or not self._inspecting))
        is_ppt = self.file_type() == TEMPLATE_FILE_TYPE
        self._template_btn.setVisible(is_ppt)
        self._template_btn.setEnabled(is_ppt and not has_sources and ready)
        self._template_name.setVisible(is_ppt and self._template_loaded)
        text = self._prompt_edit.toPlainText()
        self._tip_label.setVisible(self._model_is_small and (
            len(text) > PROMPT_COMPLEXITY_THRESHOLD_CHARS
            or any(keyword in text.lower() for keyword in STYLING_KEYWORDS)))

    def _primary_clicked(self) -> None:
        if self._paths:
            self.propose_requested.emit(self.snapshot(False))
        else:
            self.generate_requested.emit(self.file_type(), self._save_dir,
                                         self._prompt_edit.toPlainText().strip())
