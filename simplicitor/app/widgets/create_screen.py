"""One Create workspace for prompt generation and read-only source extraction."""
import logging
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QProgressBar, QPushButton, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from PySide6.QtGui import QColor

from app.config.defaults import (
    BORDER_COLOR, EXTRACTION_PROMPT_PLACEHOLDER, GENERATE_FILE_TYPES, MAX_PROMPT_CHARS,
    PRIMARY_ACCENT_COLOR, FONT_SIZE_BODY_PT, CHOICE_SELECTED_COLOR,
    SECONDARY_PRESSED_COLOR, INFO_BANNER_BG_COLOR, BODY_TEXT_COLOR,
    PROMPT_COMPLEXITY_THRESHOLD_CHARS, PROMPT_PLACEHOLDERS, STYLING_KEYWORDS,
    EXTRACTION_SOURCE_FILTER, TEMPLATE_FILE_TYPE, EXTRACTION_FLAG_COLOR,
)
from app.config.settings import Settings
from app.config.styles import input_styles
from app.widgets.plain_labels import describe_anchor, describe_coverage, describe_issues
from app.widgets.status_banner import StatusBanner
from app.widgets.step_indicator import StepIndicator
from app.workers.extraction_worker import ExtractionSetup
from extraction.models import Candidate, ColumnSpec, ExtractionProfile, ReviewCell
from extraction.pipeline import ambiguous_date_columns

logger = logging.getLogger(__name__)
EXCEL = "Excel (.xlsx)"
SOURCE_SUFFIXES = {".docx", ".pdf"}
COVERAGE_HEADER = ("Some information may be missing from the table. "
                   "Check these problems before you use it:")
ROUTE_PROMPT = ["Describe", "Save"]
ROUTE_SOURCES = ["Describe", "Choose columns", "Review and save"]
TYPE_NAMES = {"text": "Text", "integer": "Whole number", "decimal": "Decimal number",
              "date": "Date"}


class CreateScreen(QWidget):
    """Emit frozen work requests and display results supplied by GUI-thread slots."""

    generate_requested = Signal(str, str, str)
    template_requested = Signal()
    template_cleared = Signal()
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
        self._route = "write"
        self._requests = {"write": "", "pull": ""}
        self._paths: tuple[Path, ...] = ()
        self._documents: tuple = ()
        self._inspecting = self._confirmed = self._pending_confirm = self._loading = False
        self._busy = self._generating = self._connected = self._saving = False
        self._model = ""
        self._model_is_small = self._template_loaded = False
        self._candidate = None
        self._cells: dict = {}
        self._last_generated_path = ""
        self._column_settings: dict[str, ColumnSpec] = {}
        self._next_column = 0
        self._work_action = self._progress_message = ""
        self._progress_counts: tuple[int, int] | None = None
        self._source_counts: dict[str, int] = {}
        self._reading_problems: set[str] = set()
        self._file_scroll_timer = QTimer(self)
        self._file_scroll_timer.setSingleShot(True)
        self._file_scroll_timer.timeout.connect(self._scroll_to_active_file)
        self.setAcceptDrops(True)
        self.setObjectName("createWorkspace")
        self.setStyleSheet(
            input_styles()
            + f"QWidget#createWorkspace {{ font-size: {FONT_SIZE_BODY_PT}pt; "
            f"color: {BODY_TEXT_COLOR}; }}"
            f"QFrame#documentCard {{ background: white; border: 1px solid {BORDER_COLOR}; "
            "border-radius: 4px; }"
            f"QPushButton {{ background: white; color: {BODY_TEXT_COLOR}; "
            f"border: 1px solid {BORDER_COLOR}; border-radius: 4px; padding: 8px 12px; }}"
            "QPushButton:disabled { background: #F9FAFB; color: #9CA3AF; }"
            f"QPushButton[primary='true'] {{ background: {PRIMARY_ACCENT_COLOR}; color: white; "
            "border: none; border-radius: 4px; padding: 8px 14px; font-weight: 600; }"
            "QPushButton[primary='true']:disabled { background: #E5E7EB; color: #747B87; }"
            f"QPushButton[link='true'] {{ color: {PRIMARY_ACCENT_COLOR}; border: none; "
            "background: transparent; text-align: left; padding: 3px 0; }"
            f"QPushButton[secondary='true'] {{ background: {INFO_BANNER_BG_COLOR}; "
            f"color: {PRIMARY_ACCENT_COLOR}; border: 1px solid {PRIMARY_ACCENT_COLOR}; "
            "border-radius: 4px; padding: 8px 14px; font-weight: 600; }"
            f"QPushButton[secondary='true']:hover {{ background: {CHOICE_SELECTED_COLOR}; }}"
            f"QPushButton[secondary='true']:pressed {{ background: {SECONDARY_PRESSED_COLOR}; }}"
            f"QPushButton[secondary='true'][chosen='true'] {{ "
            f"background: {CHOICE_SELECTED_COLOR}; border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
            "QPushButton[secondary='true']:disabled { color: #747B87; }"
            f"QPushButton[route='true'] {{ background: white; border: 1px solid {BORDER_COLOR}; "
            "border-radius: 4px; padding: 12px 16px; text-align: left; }"
            f"QPushButton[route='true']:hover {{ background: {INFO_BANNER_BG_COLOR}; }}"
            f"QPushButton[route='true']:checked {{ background: {INFO_BANNER_BG_COLOR}; "
            f"border: 2px solid {PRIMARY_ACCENT_COLOR}; }}"
            f"QProgressBar {{ border: none; background: #E2E7EE; }}"
            f"QProgressBar::chunk {{ background: {PRIMARY_ACCENT_COLOR}; }}"
            "QLabel[cardTitle='true'] { font-weight: 600; }"
            "QPlainTextEdit#readingProblems { background: #FFF8E9; border: 1px solid #B88B40; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 20)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("Create new")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        self._caption = QLabel("Describe what you need.")
        self._caption.setStyleSheet("color: #626B78;")
        heading.addWidget(title)
        heading.addWidget(self._caption)
        heading.addStretch()
        options = QHBoxLayout()
        self._write_option = QPushButton("Write a new document\n"
                                        "Word, PDF, PowerPoint or Excel, from a description.")
        self._pull_option = QPushButton("Pull information from documents into Excel\n"
                                       "Read your Word files or PDFs and make an Excel table.")
        self._route_buttons = QButtonGroup(self)
        for route, button in (("write", self._write_option), ("pull", self._pull_option)):
            button.setProperty("route", True)
            button.setCheckable(True)
            self._route_buttons.addButton(button)
            button.clicked.connect(lambda _checked=False, value=route: self.set_route(value))
            options.addWidget(button, 1)
        self._steps = StepIndicator()
        self._pages = QStackedWidget()
        self._describe_page = self._build_describe_page()
        self._saved_page = self._build_saved_page()
        self._pages.addWidget(self._describe_page)
        self._pages.addWidget(self._saved_page)
        self._columns_page = self._build_columns_page()
        self._review_page = self._build_review_page()
        self._pages.addWidget(self._columns_page)
        self._pages.addWidget(self._review_page)
        self._status = StatusBanner()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self.cancel_requested)
        footer = QHBoxLayout()
        footer.addWidget(self._status, stretch=1)
        footer.addStretch()
        footer.addWidget(self._cancel_btn)
        layout.addLayout(heading)
        layout.addLayout(options)
        layout.addWidget(self._steps)
        layout.addWidget(self._pages, stretch=1)
        layout.addLayout(footer)
        self._prompt_edit.textChanged.connect(self._setup_edited)
        self._type_combo.currentTextChanged.connect(self._type_changed)
        self._update_placeholder()
        self._refresh()
        self._update_details()

    def route(self) -> str:
        """Return the chosen operation independently of attached source files."""
        return self._route

    def set_route(self, route: str) -> None:
        """Keep each option's inputs; invalidate derived Pull results through setup_changed."""
        if route not in self._requests or route == self._route:
            return
        if self._busy or self._generating or self._inspecting:
            return
        self._requests[self._route] = self._prompt_edit.toPlainText()
        self._loading = True
        if self._route == "pull":
            self._columns_table.setRowCount(0)
            self._column_settings.clear()
        self._route = route
        self._prompt_edit.setPlainText(self._requests[route])
        self._loading = False
        self._pages.setCurrentWidget(self._describe_page)
        self._setup_edited()
        self._steps.set_current(0)
        self._caption.setText("Describe what you need.")
        self._update_placeholder()
        if route == "pull":
            if self._documents:
                self.show_inspection(self._documents)
            elif self._paths:
                self._read_again()

    @staticmethod
    def _card() -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("documentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        return card, layout

    @staticmethod
    def _card_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("cardTitle", True)
        return label

    def _build_describe_page(self) -> QWidget:
        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)
        self._description_card, column = self._card()
        self._describe_title = self._card_title("1. Describe the document you need")
        column.addWidget(self._describe_title)
        self._prompt_label = QLabel("Description")
        column.addWidget(self._prompt_label)
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setMinimumHeight(116)
        self._prompt_edit.setMaximumHeight(180)
        column.addWidget(self._prompt_edit)
        self._writing_help = QLabel("Be specific about the content, sections and length.")
        column.addWidget(self._writing_help)
        self._tip_label = QLabel(
            "Tip: Your model works best with short, clear prompts. "
            "Consider simplifying your request for better results.")
        self._tip_label.setWordWrap(True)
        column.addWidget(self._tip_label)
        self._sources_note = QLabel("One row per file. You will confirm the columns, then review "
                                   "the table and its source text before saving.")
        self._sources_note.setWordWrap(True)
        self._sources_note.setStyleSheet("background: #EFF6FF; padding: 10px;")
        column.addWidget(self._sources_note)
        self._disconnected_label = QLabel(
            "Simplicitor cannot find your AI engine.\nPlease start Ollama and click Retry.")
        self._disconnected_label.setWordWrap(True)
        self._retry_btn = QPushButton("Retry")
        self._retry_btn.clicked.connect(self.retry_requested)
        column.addWidget(self._disconnected_label)
        column.addWidget(self._retry_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._pull_actions = QHBoxLayout()
        column.addLayout(self._pull_actions)
        column.addStretch()

        self._output_card, output = self._card()
        output.addWidget(self._card_title("2. Choose the output"))
        output.addWidget(QLabel("File type"))
        self._type_combo = QComboBox()
        for label in GENERATE_FILE_TYPES:
            self._type_combo.addItem(label.split(" (", 1)[0], label)
        output.addWidget(self._type_combo)
        self._template_btn = QPushButton("Use a template")
        self._template_btn.setProperty("secondary", True)
        self._template_btn.setProperty("chosen", False)
        self._template_btn.clicked.connect(self.template_requested)
        output.addWidget(self._template_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._template_name = QLabel()
        self._template_name.setWordWrap(True)
        self._template_name.setTextFormat(Qt.TextFormat.PlainText)
        self._clear_template_btn = QPushButton("Clear")
        self._clear_template_btn.setProperty("link", True)
        self._clear_template_btn.clicked.connect(self._clear_template)
        selected = QHBoxLayout()
        selected.addWidget(self._template_name, 1)
        selected.addWidget(self._clear_template_btn)
        output.addLayout(selected)
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
        save.addWidget(self._change_folder_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        output.addWidget(self._save_folder)
        self._write_actions = QHBoxLayout()
        output.addLayout(self._write_actions)
        output.addStretch()
        self._primary_btn = QPushButton("Create file")
        self._primary_btn.setProperty("primary", True)
        self._primary_btn.clicked.connect(self._primary_clicked)
        self._write_actions.addWidget(self._primary_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._write_actions.addStretch()

        self._source_card, sources = self._card()
        sources.addWidget(self._card_title("2. Add your source files"))
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
        # Row widgets own their spacing; the entry-point item padding would clip them.
        self._source_list.setStyleSheet("QListWidget::item { padding: 0; }")
        self._source_list.setMaximumHeight(180)
        sources.addWidget(self._source_list)
        source_hint = QLabel("DOCX and PDFs with selectable text. Scanned PDFs are not supported.")
        source_hint.setWordWrap(True)
        sources.addWidget(source_hint)
        self._reading_label = QLabel("Reading your files...")
        self._read_again_btn = QPushButton("Read files again")
        self._read_again_btn.clicked.connect(self._read_again)
        sources.addWidget(self._reading_label)
        sources.addWidget(self._read_again_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._source_coverage = QPlainTextEdit()
        self._source_coverage.setObjectName("readingProblems")
        self._source_coverage.setReadOnly(True)
        self._source_coverage.setMaximumHeight(160)
        self._source_coverage.hide()
        self._coverage_view = self._source_coverage
        sources.addWidget(self._source_coverage)
        sources.addStretch()
        row.addWidget(self._description_card, 65)
        row.addWidget(self._output_card, 35)
        row.addWidget(self._source_card, 35)
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
        self._requests = {"write": "", "pull": ""}
        self._loading = False
        self.set_template_loaded(False)
        if hasattr(self, "_columns_table"):
            self._columns_table.setRowCount(0)
            self._column_settings.clear()
        self.set_paths(())
        self.set_route("write")
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
        self._documents = ()
        self._reading_problems.clear()
        self._source_counts.clear()
        self._render_source_rows()
        self._inspecting = self._route == "pull" and bool(self._paths)
        self._update_placeholder()
        self._setup_edited()
        if self._inspecting:
            self.inspect_requested.emit(self.snapshot(False))

    def _read_again(self) -> None:
        if self._route == "pull" and self._paths and not self._busy:
            self._inspecting = True
            self._refresh()
            self.inspect_requested.emit(self.snapshot(False))

    def dragEnterEvent(self, event) -> None:
        """Accept supported local-file drops only while the setup is editable."""
        urls = event.mimeData().urls()
        if (self._route == "pull" and self._pages.currentWidget() is self._describe_page
                and not self._busy and urls and all(url.isLocalFile()
                and Path(url.toLocalFile()).suffix.lower() in SOURCE_SUFFIXES for url in urls)):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Append a supported drop without deduplicating attachment names."""
        urls = event.mimeData().urls()
        if (self._route == "pull" and self._pages.currentWidget() is self._describe_page
                and not self._busy and urls and all(url.isLocalFile()
                and Path(url.toLocalFile()).suffix.lower() in SOURCE_SUFFIXES for url in urls)):
            self.set_paths(self._paths + tuple(Path(url.toLocalFile()) for url in urls))
            event.acceptProposedAction()

    @Slot(object)
    def show_inspection(self, documents) -> None:
        """Store source metadata and show its reading problems without internal codes."""
        if self._route != "pull":
            return
        self._documents = tuple(documents)
        self._reading_problems = {doc.source_id for doc in self._documents if doc.issues}
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
        self._requests[self._route] = self._prompt_edit.toPlainText()
        self.clear_review()
        self.setup_changed.emit()
        self._refresh()

    def _type_changed(self, _display_name: str) -> None:
        label = self._type_combo.currentData()
        self._update_placeholder()
        self.file_type_changed.emit(label)
        self._setup_edited()

    def _update_placeholder(self) -> None:
        """Hint at extraction while sources are attached, else at the chosen file type."""
        self._prompt_edit.setPlaceholderText(
            EXTRACTION_PROMPT_PLACEHOLDER if self._route == "pull"
            else PROMPT_PLACEHOLDERS.get(self.file_type(), ""))

    def file_type(self) -> str:
        """Return the existing backend type label, independently of display text."""
        return EXCEL if self._route == "pull" else self._type_combo.currentData()

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

    def set_busy(self, busy: bool, saving: bool = False, action: str = "") -> None:
        """Freeze setup individually while keeping cancellable work outside the pages."""
        self._busy, self._saving = busy, saving
        self._work_action = action if busy else ""
        self._progress_message = ""
        self._progress_counts = None
        self._source_counts.clear()
        if not busy:
            self._inspecting = False
        for control in self._setup_controls():
            control.setEnabled(not busy)
        self._cancel_btn.setEnabled(busy and not saving and not self._generating)
        self.busy_changed.emit(busy)
        self._refresh()

    def show_progress(self, message: str) -> None:
        """Put existing worker progress on the action as well as the status line."""
        if self._route != "pull":
            return
        self._progress_message = message
        if message.startswith("Reading sources"):
            self._inspecting = True
        elif message.startswith("Suggesting columns"):
            self._work_action = "propose"
        self.show_status(message)
        self._refresh()

    @Slot(str, int, int)
    def show_source_progress(self, source_id: str, done: int, total: int) -> None:
        """Display the pipeline's completed units against their attachment identity."""
        if self._route != "pull" or not any(doc.source_id == source_id for doc in self._documents):
            return
        self._progress_counts = (done, total)
        offset = 0
        for doc in self._documents:
            if doc.source_id == source_id:
                self._source_counts[source_id] = min(len(doc.units), max(0, done - offset))
                break
            offset += len(doc.units)
        self._refresh()

    def _render_source_rows(self) -> None:
        for view in (self._source_list, self._working_files):
            view.clear()
            for index, path in enumerate(self._paths):
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.AccessibleTextRole, path.name)
                item.setToolTip(str(path))
                view.addItem(item)
                holder = QWidget()
                layout = QVBoxLayout(holder)
                layout.setContentsMargins(2, 2, 2, 2)
                layout.setSpacing(4)
                top = QHBoxLayout()
                label = QLabel(path.name)
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setStyleSheet(f"color: {BODY_TEXT_COLOR};")
                label.setWordWrap(True)
                label.setMinimumWidth(0)
                top.addWidget(label, 1)
                if view is self._source_list:
                    remove = QPushButton("Remove")
                    remove.setMinimumHeight(28)
                    remove.clicked.connect(lambda _checked=False, i=index: self._remove_index(i))
                    top.addWidget(remove)
                layout.addLayout(top)
                status = QLabel()
                status.setObjectName("fileState")
                layout.addWidget(status, alignment=Qt.AlignmentFlag.AlignLeft)
                detail = QLabel()
                detail.setObjectName("fileProgress")
                layout.addWidget(detail)
                bar = QProgressBar()
                bar.setObjectName("fileProgressBar")
                bar.setRange(0, 0)
                bar.setTextVisible(False)
                bar.setFixedHeight(4)
                layout.addWidget(bar)
                view.setItemWidget(item, holder)
                item.setSizeHint(holder.sizeHint())

    def _update_source_rows(self) -> None:
        extracting = self._busy and self._work_action == "extract"
        active = next((doc.source_id for doc in self._documents
                       if self._source_counts.get(doc.source_id, 0) < len(doc.units)), None)
        self._file_progress_box.setVisible(extracting)
        for view in (self._source_list, self._working_files):
            active_item = None
            for index in range(view.count()):
                item = view.item(index)
                holder = view.itemWidget(item)
                doc = self._documents[index] if index < len(self._documents) else None
                state = ("Reading" if self._inspecting else
                         "Partly read" if doc and doc.source_id in self._reading_problems else
                         "Ready" if doc else "")
                status = holder.findChild(QLabel, "fileState")
                status.setText(state)
                status.setVisible(bool(state))
                background, ink = (("#E8F0FF", "#1D4ED8") if state == "Reading" else
                                   ("#FFF1D6", "#80530A") if state == "Partly read" else
                                   ("#EAF6EF", "#21633C"))
                status.setStyleSheet(f"background: {background}; color: {ink}; padding: 1px 7px;")
                detail = holder.findChild(QLabel, "fileProgress")
                working = extracting and doc is not None and doc.source_id == active
                done = self._source_counts.get(doc.source_id, 0) if doc else 0
                detail.setText(f"Extracting... {done} / {len(doc.units)} source units" if working
                               else f"Processed {done} source units" if done else "")
                detail.setVisible(extracting and bool(detail.text()))
                holder.findChild(QProgressBar, "fileProgressBar").setVisible(
                    self._inspecting or working)
                item.setSizeHint(holder.sizeHint())
                if working:
                    active_item = item
            if view is self._working_files and active_item is not None:
                view.scrollToItem(active_item, QAbstractItemView.ScrollHint.PositionAtBottom)
                # Row heights and scroll ranges also settle on the next layout turn.
                self._file_scroll_timer.start(0)

    def _scroll_to_active_file(self) -> None:
        if not self._busy or self._work_action != "extract":
            return
        for index, doc in enumerate(self._documents):
            if self._source_counts.get(doc.source_id, 0) < len(doc.units):
                self._working_files.scrollToItem(self._working_files.item(index),
                                                QAbstractItemView.ScrollHint.PositionAtBottom)
                break

    def eventFilter(self, watched, event) -> bool:
        """Keep the active progress row visible after a viewport resize."""
        if event.type() == QEvent.Type.Resize:
            self._file_scroll_timer.start(0)
        return super().eventFilter(watched, event)

    def _setup_controls(self) -> tuple:
        return (self._write_option, self._pull_option,
                self._prompt_edit, self._type_combo, self._source_list, self._browse_btn,
                self._change_folder_btn, self._template_btn, self._clear_template_btn,
                self._retry_btn, self._read_again_btn,
                self._primary_btn, self._open_file_btn, self._another_btn,
                self._columns_table, self._add_column_btn, self._remove_column_btn,
                self._thousands_edit, self._decimal_edit, self._date_order_combo,
                self._back_btn, self._extract_btn, self._ack_checkbox, self._save_btn,
                self._back_columns_btn)

    def set_generating(self, in_progress: bool) -> None:
        """Display generation progress without allowing a duplicate request."""
        self._generating = in_progress
        if in_progress and self._pages.currentWidget() is self._saved_page:
            self._pages.setCurrentWidget(self._describe_page)
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
        if (self._route == "pull" and self._paths and self._documents and not self._inspecting
                and self._pages.currentWidget() is self._describe_page):
            self.set_columns(())  # A failed proposal still permits manual column entry.
        self.show_status(message, True)
        if issues:
            self._reading_problems.update(issue.source_id for issue in issues)
            labels = {doc.source_id: doc.label for doc in self._documents}
            self._set_coverage("\n".join(describe_coverage(
                labels.get(issue.source_id, "Source file"), issue.anchor, issue.code)
                for issue in issues))
            self._update_source_rows()

    def _set_coverage(self, text: str) -> None:
        if text:
            text = f"{COVERAGE_HEADER}\n{text}"
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
        self._template_name.setText((name or "selected") if loaded else "")
        self._template_btn.setProperty("chosen", loaded)
        self._template_btn.style().unpolish(self._template_btn)
        self._template_btn.style().polish(self._template_btn)
        self._refresh()

    def _clear_template(self) -> None:
        if not self._busy and not self._generating:
            self.set_template_loaded(False)
            self.template_cleared.emit()

    def show_open_file_btn(self, path: str) -> None:
        """Show the saved-file page and retain its path for the explicit Open action."""
        self._last_generated_path = path
        self._saved_label.setText("Saved: " + Path(path).name)
        self._pages.setCurrentWidget(self._saved_page)
        self._steps.set_steps(ROUTE_SOURCES if self._route == "pull" else ROUTE_PROMPT)
        self._steps.set_current(2 if self._route == "pull" else 1)
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

    def snapshot(self, include_columns: bool = True) -> ExtractionSetup:
        """Freeze setup for the worker without sharing live widget state."""
        return ExtractionSetup(self._paths if self._route == "pull" else (),
            self._prompt_edit.toPlainText().strip(),
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
        self._grid.clear()
        self._grid.setRowCount(0)
        self._grid.setColumnCount(0)
        self._evidence.clear()
        self._ack_checkbox.setChecked(False)
        self._ack_checkbox.hide()
        self._review_note.hide()
        self._set_coverage("")
        self._refresh()

    def _refresh(self) -> None:
        pulling = self._route == "pull"
        has_sources = pulling and bool(self._paths)
        for route, button in (("write", self._write_option), ("pull", self._pull_option)):
            button.setChecked(route == self._route)
            button.setEnabled(not (self._busy or self._generating or self._inspecting))
        self._source_card.setVisible(pulling)
        self._output_card.setVisible(not pulling)
        self._describe_title.setText("1. Describe the information you need" if pulling
                                     else "1. Describe the document you need")
        self._prompt_label.setText("What should go in Excel?" if pulling else "Description")
        self._writing_help.setVisible(not pulling)
        host = self._description_card if pulling else self._output_card
        if self._primary_btn.parentWidget() is not host:
            (self._pull_actions if pulling else self._write_actions).insertWidget(
                0, self._primary_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._sources_note.setVisible(pulling)
        self._save_folder.setVisible(not pulling)
        self._reading_label.setVisible(self._inspecting)
        self._read_again_btn.setVisible(has_sources and not self._documents and not self._inspecting)
        self._read_again_btn.setEnabled(not self._busy)
        self._steps.set_steps(ROUTE_SOURCES if pulling else ROUTE_PROMPT)
        self._retry_btn.setVisible(not self._connected)
        self._disconnected_label.setVisible(not self._connected)
        ready = (not self._busy and not self._generating and self._connected and bool(self._model)
                 and bool(self._prompt_edit.toPlainText().strip()))
        self._primary_btn.setText("Reading files..." if pulling and self._inspecting else
                                  "Suggesting columns..." if pulling and self._busy
                                  and self._work_action == "propose" else
                                  "Next: choose columns" if pulling
                                  else "Creating..." if self._generating else "Create file")
        self._primary_btn.setEnabled(ready and (not pulling or (has_sources and not self._inspecting)))
        is_ppt = not pulling and self.file_type() == TEMPLATE_FILE_TYPE
        self._template_btn.setVisible(is_ppt)
        self._template_btn.setEnabled(is_ppt and not has_sources and not self._busy
                                      and not self._generating and self._connected
                                      and bool(self._model))
        self._template_name.setVisible(is_ppt and self._template_loaded)
        self._clear_template_btn.setVisible(is_ppt and self._template_loaded)
        text = self._prompt_edit.toPlainText()
        self._tip_label.setVisible(self._model_is_small and (
            len(text) > PROMPT_COMPLEXITY_THRESHOLD_CHARS
            or any(keyword in text.lower() for keyword in STYLING_KEYWORDS)))
        self._refresh_actions()
        self._update_source_rows()

    def _build_columns_page(self) -> QWidget:
        page, layout = self._card()
        layout.addWidget(self._card_title("3. Choose columns"))
        self._columns_table = QTableWidget(0, 3)
        self._columns_table.setHorizontalHeaderLabels(["Name", "Description", "Type"])
        self._columns_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._columns_table.verticalHeader().hide()
        self._columns_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._columns_table.itemChanged.connect(self._setup_edited)
        self._columns_table.currentCellChanged.connect(self._update_details)
        layout.addWidget(self._columns_table, 1)
        actions = QHBoxLayout()
        self._add_column_btn = QPushButton("Add column")
        self._remove_column_btn = QPushButton("Remove")
        self._add_column_btn.clicked.connect(self._add_column)
        self._remove_column_btn.clicked.connect(self._remove_column)
        actions.addWidget(self._add_column_btn)
        actions.addWidget(self._remove_column_btn)
        actions.addStretch()
        layout.addLayout(actions)
        details = QGroupBox("Selected column details")
        detail_layout = QVBoxLayout(details)
        self._numeric_details = QWidget()
        numeric = QFormLayout(self._numeric_details)
        numeric.setContentsMargins(0, 0, 0, 0)
        self._thousands_edit, self._decimal_edit = QLineEdit(","), QLineEdit(".")
        for edit in (self._thousands_edit, self._decimal_edit):
            edit.setMaxLength(1)
            edit.textChanged.connect(self._details_edited)
        numeric.addRow("Thousands separator", self._thousands_edit)
        numeric.addRow("Decimal separator", self._decimal_edit)
        self._date_details = QWidget()
        dates = QHBoxLayout(self._date_details)
        dates.setContentsMargins(0, 0, 0, 0)
        question = QLabel("Dates in your files are written like 03/04/2026. "
                          "Is that day/month or month/day?")
        question.setWordWrap(True)
        self._date_order_combo = QComboBox()
        self._date_order_combo.addItem("Choose...", None)
        self._date_order_combo.addItem("Day/month", "DMY")
        self._date_order_combo.addItem("Month/day", "MDY")
        self._date_order_combo.currentIndexChanged.connect(self._details_edited)
        dates.addWidget(question, 1)
        dates.addWidget(self._date_order_combo)
        self._details_hint = QLabel()
        detail_layout.addWidget(self._numeric_details)
        detail_layout.addWidget(self._date_details)
        detail_layout.addWidget(self._details_hint)
        layout.addWidget(details)
        self._file_progress_box = QGroupBox("File progress")
        progress = QVBoxLayout(self._file_progress_box)
        self._working_files = QListWidget()
        self._working_files.viewport().installEventFilter(self)
        self._working_files.setStyleSheet("QListWidget::item { padding: 0; }")
        self._working_files.setMaximumHeight(150)
        progress.addWidget(self._working_files)
        self._file_progress_box.hide()
        layout.addWidget(self._file_progress_box)
        bottom = QHBoxLayout()
        self._extract_btn = QPushButton("Extract to Excel")
        self._extract_btn.setProperty("primary", True)
        self._extract_btn.clicked.connect(self._confirm_and_extract)
        self._back_btn = QPushButton("Back")
        self._back_btn.clicked.connect(self._back_to_describe)
        bottom.addWidget(self._extract_btn)
        bottom.addWidget(self._back_btn)
        bottom.addStretch()
        layout.addLayout(bottom)
        return page

    def _build_review_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        review, left = self._card()
        left.addWidget(self._card_title("4. Review your table"))
        self._review_note = QLabel("Highlighted values need a check before you save.")
        self._review_note.setWordWrap(True)
        self._review_note.setStyleSheet("background: #FFF8E9; padding: 10px;")
        left.addWidget(self._review_note)
        self._grid = QTableWidget()
        self._grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._grid.currentCellChanged.connect(self._show_evidence)
        left.addWidget(self._grid, 1)
        self._coverage_view = QPlainTextEdit()
        self._coverage_view.setObjectName("readingProblems")
        self._coverage_view.setReadOnly(True)
        self._coverage_view.setMaximumHeight(100)
        self._coverage_view.hide()
        left.addWidget(self._coverage_view)
        self._ack_checkbox = QCheckBox()
        self._ack_checkbox.toggled.connect(self._refresh_actions)
        self._ack_checkbox.hide()
        left.addWidget(self._ack_checkbox)
        bottom = QHBoxLayout()
        self._save_btn = QPushButton("Save to Excel")
        self._save_btn.setProperty("primary", True)
        self._save_btn.clicked.connect(self._save_review)
        self._back_columns_btn = QPushButton("Back to columns")
        self._back_columns_btn.clicked.connect(self._back_to_columns)
        bottom.addWidget(self._save_btn)
        bottom.addWidget(self._back_columns_btn)
        bottom.addStretch()
        left.addLayout(bottom)
        evidence, right = self._card()
        right.addWidget(self._card_title("5. Where this value came from"))
        self._evidence = QPlainTextEdit()
        self._evidence.setReadOnly(True)
        right.addWidget(self._evidence, 1)
        splitter.addWidget(review)
        splitter.addWidget(evidence)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)
        splitter.setSizes([650, 350])
        layout.addWidget(splitter)
        return page

    def _back_to_describe(self) -> None:
        self._pages.setCurrentWidget(self._describe_page)
        self._steps.set_current(0)
        self._caption.setText("Describe what you need.")

    def _back_to_columns(self) -> None:
        self._ack_checkbox.setChecked(False)
        self._pages.setCurrentWidget(self._columns_page)
        self._steps.set_current(1)
        self._caption.setText("Choose the information you want in Excel.")

    @Slot(object)
    def set_columns(self, columns: tuple[ColumnSpec, ...]) -> None:
        """Install editable proposals and open the column-confirmation step."""
        if self._route != "pull":
            return
        self._loading = True
        self._columns_table.setRowCount(0)
        self._column_settings.clear()
        for column in columns:
            self._append_column(column)
        self._loading = False
        self._setup_edited()
        if columns:
            self._columns_table.selectRow(0)
        self._update_details()
        self._pages.setCurrentWidget(self._columns_page)
        self._steps.set_current(1)
        self._caption.setText("Choose the information you want in Excel.")

    def _confirm_and_extract(self) -> None:
        if self._route != "pull":
            return
        try:
            columns = self.current_columns()
            if not columns:
                raise ValueError("Add at least one column.")
            if any(not column.description.strip() for column in columns):
                raise ValueError("Give every column a description.")
            if not self._documents:
                self._pending_confirm = True
                if not self._inspecting:
                    self._inspecting = True
                    self.inspect_requested.emit(self.snapshot(False))
                return
            if self._busy:
                return
            if ambiguous_date_columns(self._documents, columns):
                raise ValueError("Choose day/month or month/day for the date columns.")
        except ValueError as exc:
            self.show_status(str(exc), True)
            return
        self._confirmed = True
        self.extract_requested.emit(self.snapshot())

    def _refresh_actions(self, *_args) -> None:
        if not hasattr(self, "_extract_btn") or not hasattr(self, "_save_btn"):
            return
        try:
            columns = self.current_columns()
            valid = (bool(columns) and all(column.description.strip() for column in columns)
                     and not ambiguous_date_columns(self._documents, columns))
        except ValueError:
            valid = False
        ready = (not self._busy and not self._generating and self._connected and bool(self._model)
                 and self._route == "pull" and bool(self._paths)
                 and bool(self._prompt_edit.toPlainText().strip()))
        self._extract_btn.setEnabled(ready and valid)
        self._extract_btn.setText(
            "Checking workbook..." if self._busy and self._work_action == "extract"
            and self._progress_message.startswith("Writing and checking") else
            "Extracting..." + (f" {self._progress_counts[0]} / {self._progress_counts[1]}"
                              if self._progress_counts else "")
            if self._busy and self._work_action == "extract" else "Extract to Excel")
        self._save_btn.setText("Saving..." if self._busy and self._saving else "Save to Excel")
        self._save_btn.setEnabled(bool(self._candidate) and not self._busy
            and (not self._candidate.issues or self._ack_checkbox.isChecked()))

    def _save_review(self) -> None:
        if self._save_btn.isEnabled() and self._candidate is not None:
            self.save_requested.emit(self._candidate, self._ack_checkbox.isChecked())

    @Slot(object, object)
    def show_candidate(self, candidate: Candidate, cells: tuple[ReviewCell, ...]) -> None:
        """Review saved cells and evidence, preserving typed values and formats."""
        if self._route != "pull":
            return
        self._candidate = candidate
        self._cells = {(cell.row - 2, cell.column - 2): cell for cell in cells}
        rows = max((cell.row - 1 for cell in cells), default=0)
        cols = max((cell.column - 1 for cell in cells), default=1)
        self._grid.setRowCount(rows)
        self._grid.setColumnCount(cols)
        labels = ["File"] + [""] * (cols - 1)
        highlighted = False
        coverage = set()
        for (row, col), cell in self._cells.items():
            entry = cell.evidence[0]
            labels[col] = entry["Field"]
            self._grid.setItem(row, 0, QTableWidgetItem(entry["File"]))
            text = cell.value.isoformat()[:10] if isinstance(cell.value, date) else str(cell.value)
            if cell.data_type == "n" and isinstance(cell.value, (int, float)):
                number = Decimal(str(cell.value))
                if cell.number_format == "0":
                    text = format(number, ".0f")
                elif cell.number_format.startswith("0."):
                    places = cell.number_format[2:]
                    if places and set(places) == {"0"}:
                        text = format(number, f".{len(places)}f")
                    elif cell.number_format == "0.##############E+00":
                        mantissa, exponent = format(number, ".14E").split("E")
                        text = mantissa.rstrip("0").rstrip(".") + f"E{int(exponent):+03d}"
            item = QTableWidgetItem("" if cell.value is None else text)
            flagged = any(entry["Status"] == "flagged" for entry in cell.evidence)
            if flagged:
                highlighted = True
                item.setBackground(QColor(EXTRACTION_FLAG_COLOR))
            self._grid.setItem(row, col, item)
            for entry in cell.evidence:
                if entry["Status"] == "coverage":
                    coverage.add(describe_coverage(entry["File"], entry["Anchor"], entry["Issue"]))
        self._grid.setHorizontalHeaderLabels(labels)
        self._grid.resizeColumnsToContents()
        field_codes = {"flagged_field", "excel_precision", "sectioned_source"}
        reading = bool(coverage) or any(issue.code not in field_codes for issue in candidate.issues)
        labels_by_source = {doc.source_id: doc.label for doc in self._documents}
        for issue in candidate.issues:
            if issue.code not in field_codes:
                self._reading_problems.add(issue.source_id)
                coverage.add(describe_coverage(labels_by_source.get(issue.source_id, "Source file"),
                                              issue.anchor, issue.code))
        self._set_coverage("\n".join(sorted(coverage)))
        self._review_note.setVisible(highlighted)
        self._ack_checkbox.setText(
            "I have checked the highlighted values and reading problems" if highlighted and reading
            else "I have checked the highlighted values" if highlighted
            else "I have checked the reading problems")
        self._ack_checkbox.setChecked(False)
        self._ack_checkbox.setVisible(bool(candidate.issues))
        self._pages.setCurrentWidget(self._review_page)
        self._steps.set_current(2)
        self._caption.setText("Check the values and their source text.")
        if cells:
            self._grid.setCurrentCell(0, 1)
            self._show_evidence(0, 1)
        self._refresh_actions()

    def _show_evidence(self, row: int, col: int, *_args) -> None:
        cell = self._cells.get((row, col))
        if not cell:
            self._evidence.clear()
            return
        blocks = []
        for entry in cell.evidence:
            where = describe_anchor(entry.get("Anchor") or "")
            value = entry.get("Value")
            lines = [f"Value: {value if value is not None and value != '' else 'Not found'}",
                     f"Source text: {entry.get('Quote') or ''}",
                     f"Found in: {entry.get('File') or ''}" + (f", {where}" if where else "")]
            check = describe_issues(entry.get("Issue") or "")
            if not check:
                check = ("The source text did not contain a value for this column."
                         if value is None or value == "" else
                         "The value was found in the source text."
                         if entry.get("Status") == "verified" else "Check this value.")
            lines.append(f"Check: {check}")
            blocks.append("\n".join(lines))
        self._evidence.setPlainText("\n\n".join(blocks))

    def _primary_clicked(self) -> None:
        if not self._primary_btn.isEnabled():
            return
        if self._route == "pull":
            self.propose_requested.emit(self.snapshot(False))
        else:
            self.generate_requested.emit(self.file_type(), self._save_dir,
                                         self._prompt_edit.toPlainText().strip())

    def _append_column(self, spec: ColumnSpec) -> None:
            self._next_column += 1
            spec = ColumnSpec(f"column_{self._next_column}", spec.label, spec.description,
                              spec.kind if spec.kind in ("text", "integer", "decimal", "date") else "text",
                              spec.thousands_separator, spec.decimal_separator, spec.date_order)
            self._column_settings[spec.id] = spec
            row = self._columns_table.rowCount()
            self._columns_table.insertRow(row)
            label = QTableWidgetItem(spec.label)
            label.setData(Qt.ItemDataRole.UserRole, spec.id)
            self._columns_table.setItem(row, 0, label)
            self._columns_table.setItem(row, 1, QTableWidgetItem(spec.description))
            kinds = QComboBox()
            for kind, label in TYPE_NAMES.items():
                kinds.addItem(label, kind)
            kinds.setCurrentIndex(kinds.findData(spec.kind))
            kinds.currentTextChanged.connect(self._setup_edited)
            kinds.currentTextChanged.connect(self._update_details)
            self._columns_table.setCellWidget(row, 2, kinds)

    def _add_column(self) -> None:
            self._loading = True
            self._append_column(ColumnSpec("", f"Column {self._next_column + 1}", ""))
            self._loading = False
            self._columns_table.selectRow(self._columns_table.rowCount() - 1)
            self._setup_edited()

    def _remove_column(self) -> None:
            row = self._columns_table.currentRow()
            if row >= 0:
                self._columns_table.removeRow(row)
                self._setup_edited()
                self._update_details()

    def current_columns(self) -> tuple[ColumnSpec, ...]:
            """Return validated editor values with confirmed English conversion settings."""
            columns = []
            for row in range(self._columns_table.rowCount()):
                item = self._columns_table.item(row, 0)
                saved = self._column_settings[item.data(Qt.ItemDataRole.UserRole)]
                kind = self._columns_table.cellWidget(row, 2).currentData()
                column = ColumnSpec(saved.id, item.text().strip(),
                                    self._columns_table.item(row, 1).text(), kind,
                                    saved.thousands_separator, saved.decimal_separator, saved.date_order)
                if not column.label:
                    raise ValueError("Give every column a name.")
                if kind in ("integer", "decimal"):
                    if column.thousands_separator not in ("", ",", ".", " ", "'"):
                        raise ValueError("Thousands separator must be comma, full stop, space, "
                                         "apostrophe or empty.")
                    if column.decimal_separator not in (".", ","):
                        raise ValueError("Decimal separator must be a full stop or comma.")
                if kind in ("integer", "decimal") and (not column.decimal_separator
                        or column.decimal_separator == column.thousands_separator):
                    raise ValueError("Use different thousands and decimal separators.")
                columns.append(column)
            if len({c.label.casefold() for c in columns}) != len(columns):
                raise ValueError("Give each column a distinct name.")
            return tuple(columns)

    def _selected_spec(self) -> ColumnSpec | None:
            row = self._columns_table.currentRow()
            if row < 0 or self._columns_table.item(row, 0) is None:
                return None
            return self._column_settings.get(self._columns_table.item(row, 0).data(Qt.ItemDataRole.UserRole))

    def _update_details(self, *_args) -> None:
            if self._loading:
                return
            spec = self._selected_spec()
            row = self._columns_table.currentRow()
            kind = self._columns_table.cellWidget(row, 2).currentData() if spec else "text"
            self._loading = True
            self._thousands_edit.setText(spec.thousands_separator if spec else ",")
            self._decimal_edit.setText(spec.decimal_separator if spec else ".")
            self._date_order_combo.setCurrentIndex(
                self._date_order_combo.findData(spec.date_order if spec else None))
            self._loading = False
            self._numeric_details.setVisible(kind in ("integer", "decimal"))
            ambiguous = bool(self._documents and ambiguous_date_columns(
                self._documents, (ColumnSpec("date", "Date", "", "date"),)))
            self._date_details.setVisible(kind == "date" and ambiguous)
            self._details_hint.setVisible(kind == "text" or (kind == "date" and not ambiguous))
            self._details_hint.setText("English month-name dates need no order setting."
                                       if kind == "date" else "Text identifiers preserve their leading zeros.")

    def _details_edited(self, *_args) -> None:
            if self._loading:
                return
            spec = self._selected_spec()
            if spec:
                self._column_settings[spec.id] = ColumnSpec(
                    spec.id, spec.label, spec.description, spec.kind,
                    self._thousands_edit.text(), self._decimal_edit.text(),
                    self._date_order_combo.currentData())
                self._setup_edited()
