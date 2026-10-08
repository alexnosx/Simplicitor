"""Source setup, confirmed columns, and read-only saved workbook review."""
from datetime import date
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QPlainTextEdit, QPushButton,
    QScrollArea, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    BORDER_COLOR, BODY_TEXT_COLOR, ERROR_COLOR, EXTRACTION_FLAG_COLOR,
    EXTRACTION_SOURCE_FILTER, PRIMARY_ACCENT_COLOR, WHITE,
)
from app.workers.extraction_worker import ExtractionSetup
from extraction.models import Candidate, ColumnSpec, ExtractionProfile, ReviewCell, SourceDocument
from extraction.pipeline import ambiguous_date_columns


class ExtractionPanel(QWidget):
    """Emit frozen setups; workers do I/O and supply saved cells for review."""
    inspect_requested = Signal(object)
    propose_requested = Signal(object)
    extract_requested = Signal(object)
    cancel_requested = Signal()
    save_requested = Signal(object, bool)
    setup_changed = Signal()
    retry_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paths: tuple[Path, ...] = ()
        self._documents: tuple[SourceDocument, ...] = ()
        self._candidate: Candidate | None = None
        self._cells: dict[tuple[int, int], ReviewCell] = {}
        self._model, self._connected = "", False
        self._busy = self._confirmed = self._loading = self._pending_confirm = False
        self._column_settings: dict[str, ColumnSpec] = {}
        self._next_column = 0
        self.setAcceptDrops(True)
        self._build_ui()
        self._refresh_actions()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self._splitter)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._setup_widget = QWidget()
        setup = QVBoxLayout(self._setup_widget)
        setup.setSpacing(10)
        intro = QLabel("Create an Excel file from your documents\n"
                       "DOCX and text-layer PDF. One spreadsheet row per attachment.")
        intro.setWordWrap(True)
        setup.addWidget(intro)
        actions = QHBoxLayout()
        self._add_btn = QPushButton("Add source files")
        self._remove_btn = QPushButton("Remove selected")
        actions.addWidget(self._add_btn)
        actions.addWidget(self._remove_btn)
        setup.addLayout(actions)
        self._source_list = QListWidget()
        self._source_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._source_list.setMaximumHeight(100)
        setup.addWidget(self._source_list)
        self._source_summary = QLabel("Drop source files here or use Add source files.")
        self._source_summary.setWordWrap(True)
        setup.addWidget(self._source_summary)
        setup.addWidget(QLabel("What information do you need?"))
        self._request_edit = QPlainTextEdit()
        self._request_edit.setPlaceholderText("Extract the customer, invoice number, total and due date.")
        self._request_edit.setMaximumHeight(95)
        setup.addWidget(self._request_edit)
        proposal_actions = QHBoxLayout()
        self._inspect_btn = QPushButton("Inspect sources")
        self._suggest_btn = QPushButton("Suggest columns")
        proposal_actions.addWidget(self._inspect_btn)
        proposal_actions.addWidget(self._suggest_btn)
        setup.addLayout(proposal_actions)
        setup.addWidget(QLabel("Columns: edit the suggestion or add your own"))
        self._columns_table = QTableWidget(0, 3)
        self._columns_table.setHorizontalHeaderLabels(["Name", "Description", "Type"])
        self._columns_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._columns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._columns_table.setColumnWidth(0, 125)
        self._columns_table.setColumnWidth(2, 90)
        self._columns_table.setMinimumHeight(135)
        setup.addWidget(self._columns_table)
        column_actions = QHBoxLayout()
        self._add_column_btn = QPushButton("Add column")
        self._remove_column_btn = QPushButton("Remove column")
        column_actions.addWidget(self._add_column_btn)
        column_actions.addWidget(self._remove_column_btn)
        setup.addLayout(column_actions)
        details = QGroupBox("Selected column details")
        details_layout = QVBoxLayout(details)
        self._numeric_details = QWidget()
        numeric = QFormLayout(self._numeric_details)
        numeric.setContentsMargins(0, 0, 0, 0)
        self._thousands_edit, self._decimal_edit = QLineEdit(","), QLineEdit(".")
        self._thousands_edit.setToolTip("Comma, full stop, space, apostrophe, or empty.")
        self._decimal_edit.setToolTip("Full stop or comma.")
        for edit in (self._thousands_edit, self._decimal_edit):
            edit.setMaxLength(1)
        numeric.addRow("Thousands separator", self._thousands_edit)
        numeric.addRow("Decimal separator", self._decimal_edit)
        details_layout.addWidget(self._numeric_details)
        self._date_details = QWidget()
        dates = QFormLayout(self._date_details)
        dates.setContentsMargins(0, 0, 0, 0)
        self._date_order_combo = QComboBox()
        self._date_order_combo.addItem("Choose date order", None)
        self._date_order_combo.addItem("Day / month / year", "DMY")
        self._date_order_combo.addItem("Month / day / year", "MDY")
        dates.addRow("Ambiguous numeric dates", self._date_order_combo)
        details_layout.addWidget(self._date_details)
        self._details_hint = QLabel("Text identifiers preserve their leading zeros.")
        self._details_hint.setWordWrap(True)
        details_layout.addWidget(self._details_hint)
        setup.addWidget(details)
        self._confirm_btn = QPushButton("Confirm columns")
        self._extract_btn = QPushButton("Extract to Excel")
        setup.addWidget(self._confirm_btn)
        setup.addWidget(self._extract_btn)
        setup.addStretch()
        scroll.setWidget(self._setup_widget)
        scroll.setMinimumWidth(350)
        self._splitter.addWidget(scroll)

        review_widget = QWidget()
        review = QVBoxLayout(review_widget)
        review.addWidget(QLabel("Review the saved workbook"))
        self._coverage_view = QPlainTextEdit()
        self._coverage_view.setReadOnly(True)
        self._coverage_view.setMinimumHeight(55)
        self._coverage_view.setMaximumHeight(100)
        review.addWidget(self._coverage_view)
        self._grid = QTableWidget()
        self._grid.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._grid.setAlternatingRowColors(True)
        self._grid.horizontalHeader().setStretchLastSection(True)
        review.addWidget(self._grid, 3)
        review.addWidget(QLabel("Evidence for the selected cell"))
        self._evidence = QPlainTextEdit()
        self._evidence.setReadOnly(True)
        self._evidence.setPlaceholderText("Select a value to inspect its quote, anchor and issues.")
        review.addWidget(self._evidence, 2)
        self._ack_checkbox = QCheckBox("I reviewed flagged values and incomplete coverage.")
        review.addWidget(self._ack_checkbox)
        self._save_btn = QPushButton("Save As")
        review.addWidget(self._save_btn)
        self._splitter.addWidget(review_widget)
        self._splitter.setSizes([480, 640])
        footer = QHBoxLayout()
        self._status = QLabel("Choose sources and describe the spreadsheet you need.")
        self._status.setWordWrap(True)
        self._retry_btn = QPushButton("Retry connection")
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setEnabled(False)
        footer.addWidget(self._status, 1)
        footer.addWidget(self._retry_btn)
        footer.addWidget(self._cancel_btn)
        layout.addLayout(footer)
        self.setStyleSheet(
            f"QTableWidget, QListWidget, QPlainTextEdit, QLineEdit {{ background: {WHITE}; "
            f"color: {BODY_TEXT_COLOR}; border: 1px solid {BORDER_COLOR}; }}"
            f"QPushButton {{ padding: 6px 10px; }}"
        )
        self._extract_btn.setStyleSheet(
            f"QPushButton:enabled {{ background: {PRIMARY_ACCENT_COLOR}; color: {WHITE}; }}")
        self._add_btn.clicked.connect(self._add_sources)
        self._remove_btn.clicked.connect(self._remove_sources)
        self._inspect_btn.clicked.connect(lambda: self.inspect_requested.emit(self.snapshot(False)))
        self._suggest_btn.clicked.connect(lambda: self.propose_requested.emit(self.snapshot(False)))
        self._request_edit.textChanged.connect(self._setup_edited)
        self._add_column_btn.clicked.connect(self._add_column)
        self._remove_column_btn.clicked.connect(self._remove_column)
        self._columns_table.itemChanged.connect(self._setup_edited)
        self._columns_table.currentCellChanged.connect(self._update_details)
        self._thousands_edit.textChanged.connect(self._details_edited)
        self._decimal_edit.textChanged.connect(self._details_edited)
        self._date_order_combo.currentIndexChanged.connect(self._details_edited)
        self._confirm_btn.clicked.connect(self._confirm_columns)
        self._extract_btn.clicked.connect(lambda: self.extract_requested.emit(self.snapshot()))
        self._cancel_btn.clicked.connect(self.cancel_requested)
        self._retry_btn.clicked.connect(self.retry_requested)
        self._grid.currentCellChanged.connect(self._show_evidence)
        self._ack_checkbox.toggled.connect(self._refresh_actions)
        self._save_btn.clicked.connect(lambda: self.save_requested.emit(
            self._candidate, self._ack_checkbox.isChecked()))
        self.clear_review()
        self._update_details()

    def _add_sources(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Choose source documents", "",
                                               EXTRACTION_SOURCE_FILTER)
        if paths:
            self.set_paths(self._paths + tuple(Path(p) for p in paths))

    def _remove_sources(self) -> None:
        selected = {self._source_list.row(item) for item in self._source_list.selectedItems()}
        self.set_paths(tuple(path for i, path in enumerate(self._paths) if i not in selected))

    def set_paths(self, paths: tuple[Path, ...]) -> None:
        """Keep every attachment independently; never copy user sources."""
        if self._busy:
            return
        if any(Path(p).suffix.lower() not in (".docx", ".pdf") for p in paths):
            self.show_status("Choose DOCX or text-layer PDF files.", True)
            return
        self._paths = tuple(Path(p) for p in paths)
        self._documents = ()
        self._source_list.clear()
        self._source_list.addItems([path.name for path in self._paths])
        self._source_summary.setText(f"{len(paths)} attachment(s). Sources stay read-only.")
        self._setup_edited()
        self._update_details()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept local supported attachments when setup is editable."""
        urls = event.mimeData().urls()
        if (not self._busy and urls and all(u.isLocalFile()
                and Path(u.toLocalFile()).suffix.lower() in (".docx", ".pdf") for u in urls)):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Append drops, preserving duplicate attachments."""
        if not self._busy:
            self.set_paths(self._paths + tuple(Path(u.toLocalFile()) for u in event.mimeData().urls()))
            event.acceptProposedAction()

    def _setup_edited(self, *_args) -> None:
        if self._loading:
            return
        self._confirmed = self._pending_confirm = False
        self.clear_review()
        self.setup_changed.emit()
        self._refresh_actions()

    def set_columns(self, columns: tuple[ColumnSpec, ...]) -> None:
        """Install editable suggestions; unknown types fall back to text."""
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
        self.show_status("Edit names, descriptions and types, then confirm columns.")

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
        kinds.addItems(["text", "integer", "decimal", "date"])
        kinds.setCurrentText(spec.kind)
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
            kind = self._columns_table.cellWidget(row, 2).currentText()
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
        kind = self._columns_table.cellWidget(row, 2).currentText() if spec else "text"
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

    def _confirm_columns(self) -> None:
        try:
            columns = self.current_columns()
            if not columns:
                raise ValueError("Add at least one column.")
            if not self._documents:
                self._pending_confirm = True
                self.inspect_requested.emit(self.snapshot(False))
                return
            if ambiguous_date_columns(self._documents, columns):
                raise ValueError("Choose day/month order in the date column details, then confirm.")
        except ValueError as exc:
            self.show_status(str(exc), True)
            return
        self._confirmed = True
        self.show_status("Columns confirmed. Ready to extract.")
        self._refresh_actions()

    def snapshot(self, include_columns: bool = True) -> ExtractionSetup:
        """Freeze editable settings for one worker, without sharing a live widget."""
        return ExtractionSetup(self._paths, self._request_edit.toPlainText().strip(),
                               self.current_columns() if include_columns else (),
                               ExtractionProfile(self._model))

    def show_inspection(self, documents: tuple[SourceDocument, ...]) -> None:
        """Show page costs/coverage and reveal date-order controls only when needed."""
        self._documents = documents
        pages = sum(d.page_cost for d in documents)
        self._source_summary.setText(f"{len(documents)} attachment(s), {pages} pages "
                                     "(DOCX counts are estimates).")
        self._set_coverage("\n".join(
            f"{d.source_id} ({d.label}) | {i.anchor} | {i.code}: {i.safe_message}"
            for d in documents for i in d.issues))
        self._update_details()
        if self._pending_confirm:
            self._pending_confirm = False
            self._confirm_columns()

    def show_candidate(self, candidate: Candidate, cells: tuple[ReviewCell, ...]) -> None:
        """Display saved values, types, flags, and evidence without reconstructing extraction."""
        self._candidate = candidate
        self._cells = {(c.row - 2, c.column - 2): c for c in cells}
        rows = max((c.row - 1 for c in cells), default=0)
        cols = max((c.column - 1 for c in cells), default=1)
        self._grid.setRowCount(rows)
        self._grid.setColumnCount(cols)
        labels = ["File"] + [""] * (cols - 1)
        for (row, col), cell in self._cells.items():
            entry = cell.evidence[0]
            labels[col] = entry["Field"]
            self._grid.setItem(row, 0, QTableWidgetItem(entry["File"]))
            text = cell.value.isoformat()[:10] if isinstance(cell.value, date) else str(cell.value)
            if cell.data_type == "n" and isinstance(cell.value, (int, float)):
                # These are the numeric formats owned by the candidate writer.
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
            if any(e["Status"] == "flagged" for e in cell.evidence):
                item.setBackground(QColor(EXTRACTION_FLAG_COLOR))
            self._grid.setItem(row, col, item)
        self._grid.setHorizontalHeaderLabels(labels)
        self._grid.resizeColumnsToContents()
        coverage = {f"{e['Record']} ({e['File']}) | {e['Anchor']} | {e['Issue']}"
                    for cell in cells for e in cell.evidence if e["Status"] == "coverage"}
        self._set_coverage("\n".join(sorted(coverage)))
        self._ack_checkbox.setChecked(False)
        self._ack_checkbox.setVisible(bool(candidate.issues))
        self.show_status("Workbook ready. Select values to review their evidence.")
        if cells:
            self._grid.setCurrentCell(0, 1)
            self._show_evidence(0, 1)
        self._refresh_actions()

    def _show_evidence(self, row: int, col: int, *_args) -> None:
        cell = self._cells.get((row, col))
        if cell:
            self._evidence.setPlainText("\n\n".join("\n".join(
                f"{key}: {entry[key] or ''}" for key in
                ("Record", "File", "Field", "Value", "Quote", "Anchor", "Status", "Issue"))
                for entry in cell.evidence))
        else:
            self._evidence.clear()

    def clear_review(self) -> None:
        """Invalidate saved review and acknowledgement before setup changes/reruns."""
        self._candidate, self._cells = None, {}
        self._grid.clear()
        self._grid.setRowCount(0)
        self._grid.setColumnCount(0)
        self._evidence.clear()
        self._set_coverage("")
        self._ack_checkbox.setChecked(False)
        self._ack_checkbox.hide()
        self._refresh_actions()

    @Slot(str)
    @Slot(str, bool)
    def show_status(self, message: str, is_error: bool = False) -> None:
        """Show actionable, sanitized status as plain text."""
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        self._status.setText(message)
        self._status.setStyleSheet(f"color: {ERROR_COLOR if is_error else BODY_TEXT_COLOR};")

    def show_failure(self, message: str, issues: tuple) -> None:
        """Retain setup and any save review, with independent coverage issues."""
        self.show_status(message, True)
        if issues:
            self._set_coverage("\n".join(
                f"{i.source_id} | {i.anchor} | {i.code}: {i.safe_message}" for i in issues))

    def _set_coverage(self, text: str) -> None:
        self._coverage_view.setPlainText(text)
        self._coverage_view.setVisible(bool(text))

    def set_model(self, model: str) -> None:
        """Use the explicitly selected model for subsequent frozen requests."""
        self._model = model
        self._refresh_actions()

    def set_ollama_connected(self, connected: bool) -> None:
        """Gate new model calls; offline manual setup and saved review remain available."""
        self._connected = connected
        self._retry_btn.setVisible(not connected)
        self._refresh_actions()

    def set_busy(self, busy: bool, saving: bool = False) -> None:
        """Freeze setup during a worker; copying after Save As is allowed to finish."""
        self._busy = busy
        self._setup_widget.setEnabled(not busy)
        self._cancel_btn.setEnabled(busy and not saving)
        self._refresh_actions()

    def _refresh_actions(self, *_args) -> None:
        ready = not self._busy and bool(self._paths)
        self._inspect_btn.setEnabled(ready)
        self._suggest_btn.setEnabled(ready and self._connected and bool(self._model)
                                     and bool(self._request_edit.toPlainText().strip()))
        self._confirm_btn.setEnabled(ready and self._columns_table.rowCount() > 0)
        self._extract_btn.setEnabled(ready and self._confirmed and self._connected
                                     and bool(self._model) and bool(self._request_edit.toPlainText().strip()))
        self._save_btn.setEnabled(not self._busy and self._candidate is not None
                                  and (not self._candidate.issues or self._ack_checkbox.isChecked()))
