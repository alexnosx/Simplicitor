# simplicitor/app/widgets/template_dialog.py
# Phase K: Template-based PPTX generation flow (modal state machine).
# Task 4a: scaffold - SELECTION + CONFIRM + generate_requested emission + close-block.
# (Upload/import + hard-stop routing land in 4b; worker-result slots + editable
#  preview + render land in 4c.)
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, BODY_TEXT_COLOR, ERROR_COLOR,
    FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)
from app.config.settings import Settings
from templates_engine import config
from templates_engine.manifest import Manifest, load_manifest

logger = logging.getLogger(__name__)


class TemplateDialog(QDialog):
    """Modal multi-step template-based PPTX generation flow.

    Task 4a scaffold: SELECTION and CONFIRM pages in a QStackedWidget. SELECTION
    lists templates from config.list_templates() and advances to CONFIRM on
    selection. CONFIRM shows a manifest-derived summary, takes a prompt, and emits
    generate_requested(manifest, user_request) for a MainWindow-owned worker
    (Task 6) to act on. The dialog blocks its own close while a generation is in
    flight.

    Upload/import + hard-stop routing (4b) and the worker-result slots + editable
    preview + render (4c) are added in later commits.
    """

    generate_requested = Signal(object, str)  # (Manifest, user_request)

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings  # consumed in 4c for the render output path
        self._templates: list[dict] = []
        self._manifest: Manifest | None = None
        self._generating = False
        self.setWindowTitle("Create from a template")
        self.setMinimumSize(640, 520)
        self._build_ui()
        self.setStyleSheet(f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}")
        self._refresh_templates()

    # -- fonts --
    def _heading_font(self) -> QFont:
        f = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        f.setWeight(QFont.Weight.DemiBold)
        return f

    def _body_font(self) -> QFont:
        return QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

    # -- build --
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self._stack = QStackedWidget()
        root.addWidget(self._stack)
        self._selection_page = self._build_selection_page()
        self._confirm_page = self._build_confirm_page()
        self._stack.addWidget(self._selection_page)
        self._stack.addWidget(self._confirm_page)
        self._stack.setCurrentWidget(self._selection_page)

    def _build_selection_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)
        heading = QLabel("Choose a template")
        heading.setFont(self._heading_font())
        v.addWidget(heading)
        self._template_list = QListWidget()
        self._template_list.setFont(self._body_font())
        v.addWidget(self._template_list, stretch=1)
        self._sel_empty = QLabel("No templates yet. Upload a .pptx to begin.")
        self._sel_empty.setFont(self._body_font())
        self._sel_empty.setVisible(False)
        v.addWidget(self._sel_empty)
        self._sel_error = QLabel()
        self._sel_error.setFont(self._body_font())
        self._sel_error.setStyleSheet(f"color: {ERROR_COLOR};")
        self._sel_error.setWordWrap(True)
        self._sel_error.setVisible(False)
        v.addWidget(self._sel_error)
        row = QHBoxLayout()
        row.addStretch()
        self._sel_next_btn = QPushButton("Next")
        self._sel_next_btn.setFont(self._body_font())
        self._sel_next_btn.clicked.connect(self._on_select_next)
        row.addWidget(self._sel_next_btn)
        v.addLayout(row)
        return page

    def _build_confirm_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)
        heading = QLabel("Confirm template and describe your deck")
        heading.setFont(self._heading_font())
        v.addWidget(heading)
        self._confirm_summary = QLabel()
        self._confirm_summary.setFont(self._body_font())
        self._confirm_summary.setWordWrap(True)
        v.addWidget(self._confirm_summary)
        prompt_label = QLabel("Describe the presentation you need")
        prompt_label.setFont(self._body_font())
        v.addWidget(prompt_label)
        self._confirm_prompt = QPlainTextEdit()
        self._confirm_prompt.setFont(self._body_font())
        self._confirm_prompt.setMinimumHeight(100)
        v.addWidget(self._confirm_prompt, stretch=1)
        self._confirm_status = QLabel()
        self._confirm_status.setFont(self._body_font())
        self._confirm_status.setWordWrap(True)
        self._confirm_status.setVisible(False)
        v.addWidget(self._confirm_status)
        row = QHBoxLayout()
        self._confirm_back_btn = QPushButton("Back")
        self._confirm_back_btn.setFont(self._body_font())
        self._confirm_back_btn.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._selection_page)
        )
        self._confirm_generate_btn = QPushButton("Generate")
        self._confirm_generate_btn.setFont(self._heading_font())
        self._confirm_generate_btn.clicked.connect(self._on_generate_clicked)
        row.addWidget(self._confirm_back_btn)
        row.addStretch()
        row.addWidget(self._confirm_generate_btn)
        v.addLayout(row)
        return page

    # -- selection / confirm --
    def _refresh_templates(self, select_name: str | None = None) -> None:
        from app.services.file_manipulator import ManipulationError
        self._sel_error.setVisible(False)
        try:
            self._templates = config.list_templates()
        except (ValueError, ManipulationError) as exc:
            logger.error("Could not list templates: %s", exc)
            self._templates = []
            self._show_selection_error("Could not read your templates folder.")
        self._template_list.clear()
        for t in self._templates:
            item = QListWidgetItem(f"{t['name']}  ({t['source']})")
            item.setData(Qt.ItemDataRole.UserRole, t["name"])
            self._template_list.addItem(item)
        self._sel_empty.setVisible(not self._templates)
        if select_name:
            for i in range(self._template_list.count()):
                if self._template_list.item(i).data(Qt.ItemDataRole.UserRole) == select_name:
                    self._template_list.setCurrentRow(i)
                    break

    def _on_select_next(self) -> None:
        if self._template_list.currentItem() is None:
            self._show_selection_error("Select a template, or upload a .pptx.")
            return
        self._select_current()

    def _select_current(self) -> None:
        name = self._template_list.currentItem().data(Qt.ItemDataRole.UserRole)
        t = next((x for x in self._templates if x["name"] == name), None)
        if t is None:
            self._show_selection_error("That template could not be found.")
            return
        try:
            manifest = load_manifest(t["manifest_path"])
        except (ValueError, OSError) as exc:
            logger.error("Could not load manifest for '%s': %s", name, exc)
            self._show_selection_error("That template's manifest could not be read.")
            return
        self._manifest = manifest
        self._confirm_summary.setText(self._manifest_summary(manifest))
        self._confirm_prompt.clear()
        self._set_confirm_status("", error=False)
        self._stack.setCurrentWidget(self._confirm_page)

    def _manifest_summary(self, manifest: Manifest) -> str:
        lines = [f"Template: {manifest.name}", "", "Slide types:"]
        for name, sdef in manifest.slide_types.items():
            fields = ", ".join(
                f"{f.name} ({f.kind}{'*' if f.required else ''})" for f in sdef.fields
            )
            lines.append(f"  - {name}: {fields or '(no fields)'}")
        return "\n".join(lines)

    def _on_generate_clicked(self) -> None:
        request = self._confirm_prompt.toPlainText().strip()
        if not request:
            self._set_confirm_status(
                "Describe the deck you want, then click Generate.", error=True
            )
            return
        self._set_generating(True)
        self._set_confirm_status("Starting…", error=False)
        self.generate_requested.emit(self._manifest, request)

    def _set_generating(self, flag: bool) -> None:
        self._generating = flag
        self._confirm_generate_btn.setEnabled(not flag)
        self._confirm_back_btn.setEnabled(not flag)
        self._confirm_generate_btn.setText("Generating…" if flag else "Generate")

    # -- inline status helpers --
    def _show_selection_error(self, msg: str) -> None:
        self._sel_error.setText(msg)
        self._sel_error.setVisible(True)

    def _set_confirm_status(self, msg: str, error: bool) -> None:
        self._confirm_status.setStyleSheet(
            f"color: {ERROR_COLOR if error else BODY_TEXT_COLOR};"
        )
        self._confirm_status.setText(msg)
        self._confirm_status.setVisible(bool(msg))

    # -- close discipline (block dismissal during in-flight generation) --
    def reject(self) -> None:
        if self._generating:
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self._generating:
            event.ignore()
            return
        super().closeEvent(event)
