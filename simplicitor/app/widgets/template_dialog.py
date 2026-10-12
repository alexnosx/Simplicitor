# simplicitor/app/widgets/template_dialog.py
# Template picker: select a built-in template, confirm its structure, and load it
# back onto the main Create screen. Generation and rendering happen on the main screen
# (template-aware Generate), not in this dialog.
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, ERROR_COLOR,
    FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)
from app.services.file_manipulator import ManipulationError
from templates_engine import config
from templates_engine.manifest import Manifest, load_manifest

logger = logging.getLogger(__name__)


class TemplateDialog(QDialog):
    """Modal template picker.

    A QStackedWidget over SELECTION -> CONFIRM. SELECTION lists the built-in templates
    only (uploads were removed in 2.2.0; imported templates stay on disk but are not
    offered); CONFIRM shows the manifest summary and, on "Next", emits
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
        self._sel_empty = QLabel("No built-in templates found.")
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
        heading = QLabel("Confirm your template")
        heading.setFont(self._heading_font())
        v.addWidget(heading)
        self._confirm_summary = QLabel()
        self._confirm_summary.setFont(self._body_font())
        self._confirm_summary.setWordWrap(True)
        v.addWidget(self._confirm_summary)
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
    def _refresh_templates(self) -> None:
        self._sel_error.setVisible(False)
        try:
            self._templates = [t for t in config.list_library(Path(self._templates_dir))
                               if t["source"] == "default"]
        except (ValueError, ManipulationError, OSError) as exc:
            logger.error("Could not list templates: %s", exc)
            self._templates = []
            self._show_selection_error("Could not read your templates folder.")
        self._template_list.clear()
        for t in self._templates:
            item = QListWidgetItem(t["name"])
            item.setData(Qt.ItemDataRole.UserRole, t["name"])
            self._template_list.addItem(item)
        self._sel_empty.setVisible(not self._templates)

    def _on_select_next(self) -> None:
        if self._template_list.currentItem() is None:
            self._show_selection_error("Select a template.")
            return
        self._select_current()

    def _select_current(self) -> None:
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
        self._stack.setCurrentWidget(self._confirm_page)

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
