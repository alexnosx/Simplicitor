# simplicitor/app/widgets/template_dialog.py
# Template picker: select (or upload) a template, confirm its structure, and load it
# back onto the main Create screen. Generation and rendering happen on the main screen
# (template-aware Generate), not in this dialog.
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, ERROR_COLOR,
    FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)
from app.services.file_manipulator import ManipulationError
from app.widgets.hard_stop_dialog import CHOICE_BUILTIN, HardStopDialog
from templates_engine import config
from templates_engine.manifest import Manifest, load_manifest

logger = logging.getLogger(__name__)


class TemplateDialog(QDialog):
    """Modal template picker.

    A QStackedWidget over SELECTION -> CONFIRM, with a hard-stop sub-dialog branching off
    the upload path. SELECTION lists and uploads templates; CONFIRM shows the manifest
    summary (and the detection report for uploads) and, on "Next", emits
    template_selected(manifest, template_dir, name) and closes. The picker performs no
    generation or rendering; the main Create screen drives that with the loaded template.
    """

    template_selected = Signal(object, object, str)  # (Manifest, template_dir, name)

    def __init__(self, templates_dir: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._templates_dir = templates_dir
        self._templates: list[dict] = []
        self._manifest: Manifest | None = None
        self._selected: dict | None = None
        self._template_dir: Path | None = None
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
        self._sel_upload_btn = QPushButton("Upload a .pptx…")
        self._sel_upload_btn.setFont(self._body_font())
        self._sel_upload_btn.clicked.connect(self._on_upload)
        row.addWidget(self._sel_upload_btn)
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
        heading = QLabel("Confirm your template")
        heading.setFont(self._heading_font())
        v.addWidget(heading)
        self._confirm_summary = QLabel()
        self._confirm_summary.setFont(self._body_font())
        self._confirm_summary.setWordWrap(True)
        v.addWidget(self._confirm_summary)
        self._confirm_report = QLabel()
        self._confirm_report.setFont(QFont(APP_FONT_FAMILY, 8))
        self._confirm_report.setWordWrap(True)
        self._confirm_report.setVisible(False)
        v.addWidget(self._confirm_report)
        v.addStretch()
        row = QHBoxLayout()
        self._confirm_back_btn = QPushButton("Back")
        self._confirm_back_btn.setFont(self._body_font())
        self._confirm_back_btn.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._selection_page)
        )
        self._confirm_next_btn = QPushButton("Next")
        self._confirm_next_btn.setFont(self._heading_font())
        self._confirm_next_btn.clicked.connect(self._on_confirm_next)
        row.addWidget(self._confirm_back_btn)
        row.addStretch()
        row.addWidget(self._confirm_next_btn)
        v.addLayout(row)
        return page

    # -- selection / confirm --
    def _refresh_templates(self, select_name: str | None = None) -> None:
        self._sel_error.setVisible(False)
        try:
            self._templates = config.list_library(Path(self._templates_dir))
        except (ValueError, ManipulationError, OSError) as exc:
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

    def _select_current(self, report: str = "") -> None:
        item = self._template_list.currentItem()
        if item is None:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
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
        self._selected = t
        self._template_dir = Path(t["path"])
        self._confirm_summary.setText(self._manifest_summary(manifest))
        if report:
            self._confirm_report.setText(report)
            self._confirm_report.setVisible(True)
        else:
            self._confirm_report.setVisible(False)
        self._stack.setCurrentWidget(self._confirm_page)

    def _on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a .pptx", "", "PowerPoint files (*.pptx)"
        )
        if path:
            self._do_import(path)

    def _do_import(self, path: str) -> None:
        """Import an uploaded deck (synchronous, wait cursor). Dispatches the
        import_template status-dict / exception contract; no substring matching."""
        self._clear_selection_error()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = config.import_template(path, user_root=Path(self._templates_dir))
        except ValueError as exc:
            logger.error("Template import rejected (bad file): %s", exc)
            self._show_selection_error("That file is not a usable PowerPoint deck.")
            return
        except ManipulationError as exc:
            logger.error("Template import write failure: %s", exc)
            self._show_selection_error(
                "Could not save the imported template. Check disk space and permissions."
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        status = result["status"]
        if status == "exists":
            self._show_selection_error(
                f"A template named '{result['name']}' already exists. "
                "Delete or rename it, then upload again."
            )
            return
        if status == "hard_stop":
            self._apply_hard_stop_choice(self._prompt_hard_stop(result["message"]))
            return
        if status != "ok":
            logger.error("Unexpected import status: %r", status)
            self._show_selection_error("Unexpected error during import. Please try again.")
            return
        self._refresh_templates(select_name=result["name"])
        self._select_current(report=result.get("report", ""))

    def _prompt_hard_stop(self, message: str) -> str:
        default_available = any(t["source"] == "default" for t in self._templates)
        dlg = HardStopDialog(message, default_available, parent=self)
        dlg.exec()
        return dlg.choice()

    def _apply_hard_stop_choice(self, choice: str) -> None:
        if choice == CHOICE_BUILTIN:
            self._stack.setCurrentWidget(self._selection_page)
            self._focus_first_default()
        else:
            self.reject()  # cancel and rebuild: abandon the flow

    def _focus_first_default(self) -> None:
        for i in range(self._template_list.count()):
            name = self._template_list.item(i).data(Qt.ItemDataRole.UserRole)
            t = next((x for x in self._templates if x["name"] == name), None)
            if t and t["source"] == "default":
                self._template_list.setCurrentRow(i)
                return

    def _manifest_summary(self, manifest: Manifest) -> str:
        lines = [f"Template: {manifest.name}", "", "Slide types:"]
        for name, sdef in manifest.slide_types.items():
            fields = ", ".join(
                f"{f.name} ({f.kind}{'*' if f.required else ''})" for f in sdef.fields
            )
            lines.append(f"  - {name}: {fields or '(no fields)'}")
        return "\n".join(lines)

    def _on_confirm_next(self) -> None:
        """Load the selected template back onto the main screen and close."""
        if self._manifest is None or self._selected is None:
            return
        self.template_selected.emit(self._manifest, self._template_dir, self._selected["name"])
        self.accept()

    # -- inline status helpers --
    def _show_selection_error(self, msg: str) -> None:
        self._sel_error.setText(msg)
        self._sel_error.setVisible(True)

    def _clear_selection_error(self) -> None:
        self._sel_error.setVisible(False)
