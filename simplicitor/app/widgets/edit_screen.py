"""Selective Word editing: a virtualized plain-text reader and explicit review/save steps."""
from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QTextCharFormat, QTextLayout, QTextOption
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QListView,
    QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QStyledItemDelegate, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    BODY_TEXT_COLOR, BORDER_COLOR, CHOICE_SELECTED_COLOR, EDIT_MAX_INSTRUCTION_CHARS,
    EDIT_MAX_SELECTION_CHARS, EDIT_REMOVED_BG_COLOR, EDIT_REMOVED_TEXT_COLOR,
    FONT_SIZE_BODY_PT, PRIMARY_ACCENT_COLOR, APP_FONT_FAMILY,
    INFO_BANNER_BG_COLOR, WARNING_BG_COLOR, WARNING_TEXT_COLOR, ERROR_BG_COLOR, ERROR_COLOR,
    BACKGROUND_COLOR, MUTED_TEXT_COLOR,
)
from app.config.styles import workspace_styles
from app.widgets.step_indicator import StepIndicator
from editing.body_map import selection_problem
from editing.reading_view import DisplayBlock
from editing.save import suggested_name

WORD_FILTER = "Word document (*.docx)"
DROP_BORDER_COLOR = "#8996A9"  # the approved mockup's drop outline


def _reason(block: DisplayBlock) -> str:
    if block.kind != "paragraph":
        return block.reason or "This part is read-only."
    return f"This paragraph contains {block.reason} and cannot be edited yet."


class DocumentModel(QAbstractListModel):
    """One display block per row; document content is data, never HTML."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.blocks = ()
        self.highlights = ()
        self.deletions = ()
        self.selected = set()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.blocks)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        block = self.blocks[index.row()]
        if role == Qt.ItemDataRole.UserRole:
            return block
        if role == Qt.ItemDataRole.DisplayRole:
            return block.text
        if role == Qt.ItemDataRole.ToolTipRole and block.reason:
            return _reason(block)
        return None

    def set_blocks(self, blocks, highlights=(), deletions=()) -> None:
        self.beginResetModel()
        self.blocks, self.highlights, self.selected = tuple(blocks), tuple(highlights), set()
        self.deletions = tuple(deletions)
        self.endResetModel()

    def select_range(self, selection) -> None:
        self.selected = set(range(selection[0], selection[1] + 1)) if selection else set()
        if self.blocks:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.blocks) - 1, 0))


class DocumentDelegate(QStyledItemDelegate):
    """Paint only controlled text formats and table cells, without interpreting markup."""

    @staticmethod
    def row_label(block: DisplayBlock) -> str:
        if block.reason or block.kind != "paragraph":
            title = {"header": "Header", "footer": "Footer", "table": "Table"}.get(block.kind, "")
            return "Read-only" + (f" · {title}" if title else "")
        return ""

    @staticmethod
    def text_formats(block: DisplayBlock, highlights=(), deletions=()) -> list:
        """Combine span formatting and Python-indexed highlights into Qt UTF-16 ranges."""
        text = block.text
        prefix = "• " if block.list_item else ""
        spans, offset = [], 0
        edges = {0, len(text)}
        for span in block.spans:
            end = offset + len(span.text)
            spans.append((offset, end, span))
            edges.update((offset, end))
            offset = end
        for start, end in (*highlights, *deletions):
            edges.update((start, end))
        result = []
        points = sorted(edges)
        for start, end in zip(points, points[1:]):
            if end <= start:
                continue
            fmt = QTextCharFormat()
            span = next((s for a, b, s in spans if a <= start < b), None)
            if span:
                fmt.setFontWeight(QFont.Weight.Bold if span.bold else QFont.Weight.Normal)
                fmt.setFontItalic(span.italic)
            if any(a <= start < b for a, b in highlights):
                fmt.setBackground(QColor("#DCFCE7"))
            if any(a <= start < b for a, b in deletions):
                fmt.setBackground(QColor(EDIT_REMOVED_BG_COLOR))
                fmt.setForeground(QColor(EDIT_REMOVED_TEXT_COLOR))
                fmt.setFontStrikeOut(True)
            item = QTextLayout.FormatRange()
            item.start = len((prefix + text[:start]).encode("utf-16-le")) // 2
            item.length = len(text[start:end].encode("utf-16-le")) // 2
            item.format = fmt
            result.append(item)
        return result

    def make_layout(self, block: DisplayBlock, highlights, width: int, deletions=()) -> QTextLayout:
        font = QFont(self.parent().font())
        font.setPointSize(FONT_SIZE_BODY_PT + (max(1, 5 - block.heading) if block.heading else 0))
        if block.heading:
            font.setBold(True)
        # QTextLayout treats LF as whitespace; its line separator preserves Word's
        # explicit line breaks without changing the character/highlight offsets.
        text = ("• " if block.list_item else "") + block.text.replace("\n", "\u2028")
        layout = QTextLayout(text, font)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)
        formats = self.text_formats(block, highlights, deletions)
        # Headings are a controlled display size/weight, not the document's rich text.
        if block.heading:
            for item in formats:
                item.format.setFontWeight(QFont.Weight.Bold)
        layout.setFormats(formats)
        layout.beginLayout()
        y = 0.0
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max(40, width))
            line.setPosition(QPointF(0, y))
            y += line.height()
        layout.endLayout()
        return layout

    def _height(self, block, highlights, width, deletions=()) -> int:
        label = 24 if self.row_label(block) else 0
        if block.kind == "table":
            columns = max((len(row) for row in block.cells), default=1)
            cell_width = max(40, (width - 24) // columns - 16)
            from editing.reading_view import Span
            return label + 16 + sum(max((self.make_layout(
                DisplayBlock("paragraph", spans=(Span(cell),)), (), cell_width).boundingRect().height()
                + 16 for cell in row), default=32) for row in block.cells)
        layout = self.make_layout(block, highlights, width - 32, deletions)
        return label + max(24, int(layout.boundingRect().height())) + 24

    def sizeHint(self, option, index) -> QSize:
        model = index.model()
        width = self.parent().viewport().width()
        highlights = model.highlights[index.row()] if index.row() < len(model.highlights) else ()
        deletions = model.deletions[index.row()] if index.row() < len(model.deletions) else ()
        return QSize(width, self._height(model.blocks[index.row()], highlights, width, deletions))

    def paint(self, painter: QPainter, option, index) -> None:
        model, row = index.model(), index.row()
        block = model.blocks[row]
        highlights = model.highlights[row] if row < len(model.highlights) else ()
        deletions = model.deletions[row] if row < len(model.deletions) else ()
        rect = option.rect.adjusted(4, 3, -4, -3)
        readonly = block.reason or block.kind != "paragraph"
        selected = block.index in model.selected and block.kind == "paragraph"
        painter.save()
        painter.fillRect(rect, QColor(BACKGROUND_COLOR if readonly else CHOICE_SELECTED_COLOR if selected else "white"))
        if selected or readonly:
            painter.setPen(QColor(PRIMARY_ACCENT_COLOR if selected else BORDER_COLOR))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.setPen(QColor(MUTED_TEXT_COLOR if readonly else BODY_TEXT_COLOR))
        painter.setFont(self.parent().font())
        x, y = rect.left() + 12, rect.top() + 9
        label = self.row_label(block)
        if label:
            painter.drawText(x, y + 14, label)
            y += 24
        if block.kind == "table":
            from editing.reading_view import Span
            columns = max((len(cells) for cells in block.cells), default=1)
            cell_width = max(40, (rect.width() - 24) // columns)
            for cells in block.cells:
                layouts = [self.make_layout(DisplayBlock("paragraph", spans=(Span(cell),)), (),
                                            cell_width - 16) for cell in cells]
                height = max((int(layout.boundingRect().height()) + 16 for layout in layouts), default=32)
                for col, layout in enumerate(layouts):
                    painter.setPen(QColor(BORDER_COLOR))
                    painter.drawRect(x + col * cell_width, y, cell_width, height)
                    painter.setPen(QColor(MUTED_TEXT_COLOR))
                    layout.draw(painter, QPointF(x + col * cell_width + 8, y + 8))
                y += height
        else:
            self.make_layout(block, highlights, rect.width() - 24, deletions).draw(
                painter, QPointF(x, y))
        painter.restore()


class DocumentView(QListView):
    """Virtualized reader with explicit whole-paragraph clicks, including read-only notices."""

    paragraph_clicked = Signal(int, bool)
    reason_shown = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setModel(DocumentModel(self))
        self.setItemDelegate(DocumentDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMouseTracking(True)
        self.interactive = True
        self._drag_row = None  # the row a left-button drag last selected to
        self.setStyleSheet(f"QListView {{ background: white; border: 1px solid {BORDER_COLOR}; }}"
                          f"QListView:focus {{ border: 1px solid {PRIMARY_ACCENT_COLOR}; }}")

    def set_blocks(self, blocks, highlights=(), deletions=()) -> None:
        self.model().set_blocks(blocks, highlights, deletions)

    def activate_row(self, row: int, shift: bool = False) -> None:
        if not self.interactive or not 0 <= row < len(self.model().blocks):
            return
        block = self.model().blocks[row]
        if block.reason or block.kind != "paragraph":
            self.reason_shown.emit(_reason(block))
        else:
            self.paragraph_clicked.emit(block.index, shift)

    def mousePressEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self.setCurrentIndex(index)
            block = self.model().blocks[index.row()]
            editable = self.interactive and block.kind == "paragraph" and not block.reason
            self._drag_row = index.row() if editable else None
            self.activate_row(index.row(), bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))

    def mouseMoveEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid() and self.interactive:
            block = self.model().blocks[index.row()]
            if block.reason or block.kind != "paragraph":
                self.reason_shown.emit(_reason(block))
            elif (event.buttons() & Qt.MouseButton.LeftButton and self._drag_row is not None
                  and index.row() != self._drag_row):
                # Dragging extends from the pressed paragraph, exactly like Shift-click.
                self._drag_row = index.row()
                self.paragraph_clicked.emit(block.index, True)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_row = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Space) and self.currentIndex().isValid():
            self.activate_row(self.currentIndex().row(), bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        else:
            super().keyPressEvent(event)


class DropArea(QLabel):
    """Drop target whose dashed outline is painted, so all four edges stay visible at any display scale."""

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(DROP_BORDER_COLOR), 1.5, Qt.PenStyle.DashLine))
        # Inset by the pen's half-width so no edge is clipped at fractional scales.
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 4, 4)
        painter.end()


class EditScreen(QWidget):
    """Keep edit-session inputs and emit requests; workers own all document processing."""

    open_requested = Signal(object)
    propose_requested = Signal(int, int, str, int)
    save_requested = Signal(object)
    cancel_requested = Signal()
    create_requested = Signal()
    busy_changed = Signal(bool)
    settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._busy = self._model_ready = False
        self._action = ""
        self._opened = self._candidate = self._selection = self._anchor = None
        self._view = ()
        self._attempt = 0
        self.setAcceptDrops(True)
        self.setObjectName("editWorkspace")
        self.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        self.setStyleSheet(workspace_styles())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Edit your Word document")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)
        layout.addWidget(QLabel("Select a part, describe the change, then review it before saving a new file."))
        self._steps = StepIndicator()
        self._steps.set_steps(["Open", "Select", "Describe", "Review", "Save"])
        layout.addWidget(self._steps)
        self._file_line = QWidget()
        file_layout = QHBoxLayout(self._file_line)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self._file_label = self._label("")
        self._choose_btn = self._button("Choose another file", self._browse)
        file_layout.addWidget(self._file_label, 1)
        file_layout.addWidget(self._choose_btn)
        layout.addWidget(self._file_line)
        self._original_note = self._label("Your original will not be overwritten.")
        layout.addWidget(self._original_note)
        self._close_status = self._label("Waiting for local processing to stop before closing...")
        self._close_status.setStyleSheet(f"padding: 10px; background: {INFO_BANNER_BG_COLOR}; color: {PRIMARY_ACCENT_COLOR};")
        layout.addWidget(self._close_status)
        self._error = self._label("")
        self._error.setStyleSheet(f"background: {ERROR_BG_COLOR}; color: {ERROR_COLOR}; padding: 10px; border: 1px solid {ERROR_COLOR};")
        layout.addWidget(self._error)
        self._pages = QStackedWidget()
        layout.addWidget(self._pages, 1)
        self._build_pages()
        self.reset()

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        return label

    @staticmethod
    def _button(text: str, handler, primary=False, secondary=False) -> QPushButton:
        button = QPushButton(text)
        button.setProperty("primary", primary)
        button.setProperty("secondary", secondary)
        button.clicked.connect(handler)
        return button

    def _card(self, title):
        card = QFrame()
        card.setObjectName("documentCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        heading = self._label(title)
        heading.setProperty("cardTitle", True)
        layout.addWidget(heading)
        return card, layout

    def _build_pages(self) -> None:
        self._open_page, opening = self._card("1. Open your Word document")
        self._drop_zone = DropArea("Drop a .docx here, or browse for a Word document.")
        self._drop_zone.setTextFormat(Qt.TextFormat.PlainText)
        self._drop_zone.setWordWrap(True)
        self._drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_zone.setStyleSheet("padding: 36px;")
        opening.addWidget(self._drop_zone)
        self._browse_btn = self._button("Browse .docx", self._browse, secondary=True)
        opening.addWidget(self._browse_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._open_busy_label = self._label("Reading the document...")
        self._open_cancel_btn = self._button("Cancel", self.cancel_requested.emit)
        opening.addWidget(self._open_busy_label)
        opening.addWidget(self._open_cancel_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        opening.addStretch()
        self._select_page = QWidget()
        selection = QHBoxLayout(self._select_page)
        selection.setContentsMargins(0, 0, 0, 0)
        reader_card, reader_layout = self._card("2. Select the part to edit")
        reader_layout.addWidget(self._label("Click a paragraph, or drag across several. Shift-click extends the selection."))
        self._reader = DocumentView()
        self._reader.paragraph_clicked.connect(self.select_paragraph)
        self._reader.reason_shown.connect(self._show_selection_notice)
        reader_layout.addWidget(self._reader, 1)
        self._selection_notice = self._label("")
        self._selection_notice.setStyleSheet(f"color: {PRIMARY_ACCENT_COLOR}; background: {INFO_BANNER_BG_COLOR}; padding: 8px;")
        reader_layout.addWidget(self._selection_notice)
        self._selection_status = self._label("No paragraphs selected.")
        reader_layout.addWidget(self._selection_status)
        buttons = QHBoxLayout()
        self._edit_part_btn = self._button("Edit this part", self._describe, primary=True)
        self._clear_btn = self._button("Clear selection", self._clear_selection)
        buttons.addWidget(self._edit_part_btn)
        buttons.addWidget(self._clear_btn)
        buttons.addStretch()
        reader_layout.addLayout(buttons)
        hint, hint_layout = self._card("3. Describe the change")
        hint_layout.addWidget(self._label("Choose a part on the left"))
        hint_layout.addWidget(self._label("Only the selected body paragraphs may change."))
        hint_layout.addWidget(self._label("Headings and list items count as whole paragraphs. Grey parts are read-only; hover or click to see why."))
        hint_layout.addStretch()
        selection.addWidget(reader_card, 2)
        selection.addWidget(hint, 1)
        self._describe_page = QWidget()
        describe = QHBoxLayout(self._describe_page)
        describe.setContentsMargins(0, 0, 0, 0)
        scope, scope_layout = self._card("2. Your selected part")
        self._scope = DocumentView()
        self._scope.interactive = False
        scope_layout.addWidget(self._scope, 1)
        instruction, instruction_layout = self._card("3. Describe the change")
        self._no_model = self._label("No local model selected.\nOpen Settings and select a local model before asking for a change.")
        self._no_model.setStyleSheet(f"padding: 12px; background: {WARNING_BG_COLOR}; border: 1px solid {WARNING_TEXT_COLOR};")
        self._settings_btn = self._button("Open Settings", self.settings_requested.emit, secondary=True)
        instruction_layout.addWidget(self._no_model)
        instruction_layout.addWidget(self._settings_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        instruction_layout.addWidget(self._label("Describe the change"))
        self._description = QPlainTextEdit()
        self._description.setPlaceholderText("For example: Change the payment period from 30 days to 45 days.")
        self._description.textChanged.connect(self._description_changed)
        instruction_layout.addWidget(self._description, 1)
        instruction_layout.addWidget(self._label("Everything outside your selection stays unchanged."))
        self._propose_btn = self._button("Review change", self._propose, primary=True)
        self._back_btn = self._button("Back to selection", lambda: self._show(self._select_page))
        instruction_layout.addWidget(self._propose_btn)
        instruction_layout.addWidget(self._back_btn)
        self._busy_label = self._label("The local AI is working...\nPreparing a proposal for the selected part.")
        self._busy_label.setStyleSheet(f"padding: 12px; background: {INFO_BANNER_BG_COLOR};")
        self._cancel_btn = self._button("Cancel", self.cancel_requested.emit)
        instruction_layout.addWidget(self._busy_label)
        instruction_layout.addWidget(self._cancel_btn)
        describe.addWidget(scope, 2)
        describe.addWidget(instruction, 1)
        self._review_page, reviewing = self._card("4. Review the selected part")
        self._deletion_notice = self._label("")
        self._deletion_notice.setStyleSheet(
            f"padding: 10px; background: {EDIT_REMOVED_BG_COLOR}; color: {EDIT_REMOVED_TEXT_COLOR};")
        self._deletion_notice.hide()
        reviewing.addWidget(self._deletion_notice)
        comparison = QHBoxLayout()
        self._before = DocumentView()
        self._after = DocumentView()
        self._before.setMinimumHeight(96)
        self._after.setMinimumHeight(96)
        for title, view in (("Before", self._before), ("After", self._after)):
            view.interactive = False
            column = QVBoxLayout()
            column.addWidget(self._label(title))
            column.addWidget(view, 1)
            comparison.addLayout(column, 1)
        reviewing.addLayout(comparison, 1)
        self._track_notice = self._label("Track Changes is on in this document. This change is saved without revision marks.")
        reviewing.addWidget(self._track_notice)
        self._review_note = self._label("Only the selected part is shown. Longer text can change page breaks.")
        reviewing.addWidget(self._review_note)
        review_actions = QHBoxLayout()
        self._use_btn = self._button("Use this change", lambda: self._show(self._save_page), primary=True)
        self._try_btn = self._button("Try again", self._try_again, secondary=True)
        self._cancel_review_btn = self._button("Cancel", self._cancel_review)
        for button in (self._use_btn, self._try_btn, self._cancel_review_btn):
            review_actions.addWidget(button)
        review_actions.addStretch()
        reviewing.addLayout(review_actions)
        self._save_page, saving = self._card("5. Save as a new file")
        self._suggested = self._label("")
        saving.addWidget(self._label("Your change is chosen. Save a new file to keep it; the original stays unchanged."))
        saving.addWidget(self._suggested)
        saving.addWidget(self._label("By default, save next to the original. Saving over another file asks first. The original cannot be replaced."))
        self._save_btn = self._button("Save as a new file", self._save_as, primary=True)
        self._return_btn = self._button("Back to review", lambda: self._show(self._review_page))
        saving.addWidget(self._save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        saving.addWidget(self._return_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._save_busy_label = self._label("Saving your new file...")
        saving.addWidget(self._save_busy_label)
        saving.addStretch()
        self._saved_page, saved = self._card("5. Your new file is ready")
        self._saved_path = self._label("")
        self._saved_note = self._label("The original is unchanged.")
        saved.addWidget(self._saved_path)
        saved.addWidget(self._saved_note)
        self._another_btn = self._button("Open another document", self._browse, secondary=True)
        saved.addWidget(self._another_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        saved.addStretch()
        review_scroll = QScrollArea()
        review_scroll.setFrameShape(QFrame.Shape.NoFrame)
        review_scroll.setWidgetResizable(True)
        review_scroll.setWidget(self._review_page)
        self._review_page = review_scroll
        for page in (self._open_page, self._select_page, self._describe_page, self._review_page,
                     self._save_page, self._saved_page):
            self._pages.addWidget(page)
        for widget in (self._open_busy_label, self._open_cancel_btn, self._busy_label,
                       self._cancel_btn, self._save_busy_label):
            widget.hide()

    def _show(self, page) -> None:
        self._resume_page = page
        if not self._busy:
            self._pages.setCurrentWidget(page)
        stage = {self._open_page: 0, self._select_page: 1, self._describe_page: 2,
                 self._review_page: 3, self._save_page: 4, self._saved_page: 4}
        self._steps.set_current(stage.get(page, 0))
        loaded = self._opened is not None and page not in (self._open_page, self._saved_page)
        self._file_line.setVisible(loaded)
        self._original_note.setVisible(loaded)

    def _show_selection_notice(self, text: str) -> None:
        self._selection_notice.setText(text)
        self._selection_notice.setVisible(bool(text))

    def select_paragraph(self, index: int, shift: bool = False) -> None:
        """Validate a continuous whole-body-paragraph range without replacing a bad selection."""
        if self._busy or self._opened is None:
            return
        anchor = self._anchor if shift and self._anchor is not None else index
        first, last = min(anchor, index), max(anchor, index)
        problem = selection_problem(self._opened.blocks, first, last)
        if problem:
            self._show_selection_notice(problem)
            return
        self._anchor, self._selection = anchor, (first, last)
        self._candidate = None
        self._attempt = 0
        self._reader.model().select_range(self._selection)
        count = last - first + 1
        self._selection_status.setText(f"{count} whole paragraph(s) selected.")
        length = sum(len(b.text) for b in self._opened.paragraphs[first:last + 1])
        self._edit_part_btn.setEnabled(length <= EDIT_MAX_SELECTION_CHARS)
        self._clear_btn.setEnabled(True)
        self._show_selection_notice("" if length <= EDIT_MAX_SELECTION_CHARS else
                                    "Select a shorter part (up to about 6,000 characters).")

    def _clear_selection(self) -> None:
        self._selection = self._anchor = self._candidate = None
        self._reader.model().select_range(None)
        self._selection_status.setText("No paragraphs selected.")
        self._edit_part_btn.setEnabled(False)
        self._clear_btn.setEnabled(False)
        self._show_selection_notice("")

    def _describe(self) -> None:
        if self._busy or not self._selection or not self._edit_part_btn.isEnabled():
            return
        first, last = self._selection
        self._scope.set_blocks(tuple(b for b in self._view if b.kind == "paragraph" and first <= b.index <= last))
        self._show(self._describe_page)

    def _description_changed(self) -> None:
        text = self._description.toPlainText()
        if len(text) > EDIT_MAX_INSTRUCTION_CHARS:
            cursor = self._description.textCursor()
            position = min(cursor.position(), EDIT_MAX_INSTRUCTION_CHARS)
            self._description.blockSignals(True)
            self._description.setPlainText(text[:EDIT_MAX_INSTRUCTION_CHARS])
            cursor = self._description.textCursor()
            cursor.setPosition(position)
            self._description.setTextCursor(cursor)
            self._description.blockSignals(False)
        self._propose_btn.setEnabled(bool(self._selection and self._description.toPlainText().strip()
                                         and self._model_ready and not self._busy))

    def _propose(self) -> None:
        if not self._busy and self._propose_btn.isEnabled() and self._selection:
            self._error.hide()
            self.propose_requested.emit(*self._selection, self._description.toPlainText(), self._attempt)

    def _try_again(self) -> None:
        self._candidate = None
        self._attempt += 1
        self._describe()

    def _cancel_review(self) -> None:
        self._candidate = None
        self._show(self._select_page)

    def _save_as(self) -> None:
        if self._busy or self._candidate is None or self._opened is None:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save edited Word document", str(self._opened.path.with_name(suggested_name(self._opened.path))),
            WORD_FILTER, options=QFileDialog.Option(0))
        if destination:
            self.save_requested.emit(Path(destination))

    def _browse(self) -> None:
        if self._busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open Word document", "", WORD_FILTER)
        if path:
            self.choose_path(Path(path))

    def confirm_discard(self) -> bool:
        """Ask once, without changing the session or scroll position; Keep editing is default."""
        if not self.has_work():
            return True
        dialog = QDialog(self)
        dialog.setWindowTitle("Discard changes")
        layout = QVBoxLayout(dialog)
        layout.addWidget(self._label(f"Discard your changes to {self._opened.path.name}?"))
        buttons = QHBoxLayout()
        discard = self._button("Discard", dialog.accept, primary=True)
        keep = self._button("Keep editing", dialog.reject)
        discard.setAutoDefault(False)
        keep.setDefault(True)
        buttons.addWidget(discard)
        buttons.addWidget(keep)
        layout.addLayout(buttons)
        keep.setFocus()
        return dialog.exec() == QDialog.DialogCode.Accepted

    def choose_path(self, path: Path) -> None:
        """Accept a picked/dropped file only after the existing work's discard decision."""
        if self._busy:
            return
        if path.suffix.lower() != ".docx":
            self.show_failure("Choose one Word document (.docx).", "failed")
            return
        if self.has_work() and not self.confirm_discard():
            return
        self.reset()
        self.open_requested.emit(path)

    def dragEnterEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if not self._busy and len(paths) == 1 and paths[0].suffix.lower() == ".docx":
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if not self._busy and len(paths) == 1 and paths[0].suffix.lower() == ".docx":
            self.choose_path(paths[0])
            event.acceptProposedAction()

    def show_opened(self, opened, view) -> None:
        """Start a fresh reading session from an accepted worker result."""
        self._opened, self._view = opened, tuple(view)
        self._candidate = self._selection = self._anchor = None
        self._attempt = 0
        self._description.clear()
        self._reader.set_blocks(view)
        self._clear_selection()
        self._file_label.setText(f"You are working on: {opened.path.name}")
        self._original_note.setText(
            f"Original in {opened.path.parent}. Your original will not be overwritten.")
        self._suggested.setText(f"Suggested name: {suggested_name(opened.path)}")
        self._error.hide()
        self._close_status.hide()
        self._show(self._select_page)

    def show_proposal(self, candidate, before, after) -> None:
        """Display only the selected before/after blocks and verified change highlights."""
        self._candidate = candidate
        self._before.set_blocks(before, deletions=candidate.before_deletions)
        self._after.set_blocks(after, candidate.highlights)
        notices = []
        if candidate.removed_paragraphs:
            count = candidate.removed_paragraphs
            notices.append(f"{count} original paragraph{'s' if count != 1 else ''} removed or merged.")
        if any(candidate.before_deletions):
            notices.append("Removed or replaced text is red and crossed out in Before.")
        elif candidate.removed_paragraphs:
            notices.append("Check Before and After.")
        self._deletion_notice.setText(" ".join(notices))
        self._deletion_notice.setVisible(bool(notices))
        self._track_notice.setVisible(bool(self._opened and self._opened.track_changes_on))
        self._error.hide()
        self._show(self._review_page)

    def show_saved(self, path) -> None:
        """End work ownership after a successful Save As; offer only opening another file."""
        self._candidate = self._selection = self._anchor = None
        self._description.clear()
        self._saved_path.setText(str(path))
        self._error.hide()
        self._show(self._saved_page)

    def show_failure(self, message: str, outcome: str) -> None:
        """Keep a candidate on save errors; close the session when the original changed."""
        self._close_status.hide()
        if outcome == "original":
            self.reset()
        elif self._candidate is not None:
            self._show(self._save_page)
        elif self._opened is not None:
            self._show(self._describe_page if self._selection else self._select_page)
        else:
            self._show(self._open_page)
        self._error.setText(message)
        self._error.show()

    def show_close_wait(self) -> None:
        """Show a pending close on the visible Edit screen while local processing finishes."""
        self._close_status.show()

    def show_cancelled(self) -> None:
        """Return to selection after cancelling a proposal; an unread file returns to Open."""
        self._candidate = None
        self._show(self._select_page if self._opened else self._open_page)

    def set_busy(self, busy: bool) -> None:
        """Freeze all session actions until the owning worker thread has finished."""
        self._busy = busy
        for button in (self._choose_btn, self._browse_btn, self._back_btn, self._use_btn,
                       self._try_btn, self._cancel_review_btn, self._save_btn, self._return_btn,
                       self._another_btn, self._settings_btn):
            button.setEnabled(not busy)
        self._description.setEnabled(not busy)
        self._reader.interactive = not busy
        self._open_busy_label.setVisible(busy and self._action == "open")
        self._open_cancel_btn.setVisible(busy and self._action == "open")
        self._open_cancel_btn.setEnabled(True)
        self._busy_label.setVisible(busy and self._action == "propose")
        self._cancel_btn.setVisible(busy and self._action == "propose")
        self._cancel_btn.setEnabled(True)
        self._save_busy_label.setVisible(busy and self._action == "save")
        self._propose_btn.setVisible(not (busy and self._action == "propose"))
        self._back_btn.setVisible(not (busy and self._action == "propose"))
        page = {"open": self._open_page, "propose": self._describe_page,
                "save": self._save_page}.get(self._action, self._resume_page)
        self._pages.setCurrentWidget(page if busy else self._resume_page)
        length = sum(len(b.text) for b in self._opened.paragraphs[self._selection[0]:self._selection[1] + 1]) if self._opened and self._selection else 0
        self._edit_part_btn.setEnabled(bool(self._selection and length <= EDIT_MAX_SELECTION_CHARS and not busy))
        self._clear_btn.setEnabled(bool(self._selection and not busy))
        self._description_changed()
        self.busy_changed.emit(busy)

    def set_model_ready(self, ready: bool) -> None:
        """A selected, connected model enables proposals; reading and saving need no model."""
        self._model_ready = ready
        self._no_model.setVisible(not ready)
        self._settings_btn.setVisible(not ready)
        self._description_changed()

    def has_work(self) -> bool:
        """Selection, description or an unsaved candidate requires a discard decision."""
        return bool(self._selection or self._description.toPlainText().strip() or self._candidate)

    def reset(self) -> None:
        """Discard the in-memory session without reading or writing any file."""
        self._opened = self._candidate = self._selection = self._anchor = None
        self._view = ()
        self._attempt = 0
        self._description.clear()
        self._reader.set_blocks(())
        self._before.set_blocks(())
        self._after.set_blocks(())
        self._scope.set_blocks(())
        self._clear_selection()
        self._error.hide()
        self._close_status.hide()
        self._track_notice.hide()
        self._deletion_notice.clear()
        self._deletion_notice.hide()
        self._show(self._open_page)
        self.set_model_ready(self._model_ready)
