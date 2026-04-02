# simplicitor/app/widgets/settings_dialog.py
import subprocess
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QDialogButtonBox, QFileDialog,
)
from PySide6.QtGui import QFont

from app.config.defaults import (
    APP_FONT_FAMILY, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
    BORDER_COLOR, WHITE, BORDER_RADIUS_PX, BODY_TEXT_COLOR, BACKGROUND_COLOR,
)
from app.config.settings import Settings


class SettingsDialog(QDialog):
    """Modal settings dialog.

    Presents four editable directory paths. Changes are applied and
    persisted when the user clicks Save. Cancel discards changes.
    """

    def __init__(self, settings: Settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self._build_ui()
        self._apply_styles()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        heading_font = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        heading_font.setWeight(QFont.Weight.DemiBold)
        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

        heading = QLabel("Settings")
        heading.setFont(heading_font)
        layout.addWidget(heading)

        form = QFormLayout()
        form.setSpacing(10)

        self._generated_edit = self._make_path_edit(
            self._settings.generated_dir, "Select Generated Files Location"
        )
        self._uploads_edit = self._make_path_edit(
            self._settings.uploads_dir, "Select Uploads Location"
        )
        self._backups_edit = self._make_path_edit(
            self._settings.backups_dir, "Select Backups Location"
        )
        self._logs_edit = self._make_path_edit(
            self._settings.logs_dir, "Select Logs Location"
        )

        def add_row(label: str, edit: QLineEdit) -> None:
            lbl = QLabel(label)
            lbl.setFont(body_font)
            row = self._make_browse_row(edit, label)
            form.addRow(lbl, row)

        add_row("Generated files:", self._generated_edit)
        add_row("Uploaded files:", self._uploads_edit)
        add_row("Backups:", self._backups_edit)
        add_row("Logs:", self._logs_edit)

        layout.addLayout(form)

        # Extra buttons row
        extra_row = QHBoxLayout()
        self._view_logs_btn = QPushButton("View Logs Folder")
        self._view_logs_btn.setFont(body_font)
        self._view_logs_btn.clicked.connect(self._open_logs_folder)
        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.setFont(body_font)
        self._reset_btn.clicked.connect(self._reset_to_defaults)
        extra_row.addWidget(self._view_logs_btn)
        extra_row.addStretch()
        extra_row.addWidget(self._reset_btn)
        layout.addLayout(extra_row)

        # Save / Cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _make_path_edit(self, value: str, dialog_title: str) -> QLineEdit:
        """Create a QLineEdit pre-filled with value."""
        edit = QLineEdit(value)
        edit.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        edit._dialog_title = dialog_title  # stored for browse button
        return edit

    def _make_browse_row(self, edit: QLineEdit, dialog_title: str) -> QHBoxLayout:
        """Wrap a QLineEdit with a Browse (…) button."""
        row = QHBoxLayout()
        row.setSpacing(6)
        browse_btn = QPushButton("…")
        browse_btn.setFixedSize(28, 28)
        browse_btn.clicked.connect(lambda: self._browse(edit, dialog_title))
        row.addWidget(edit)
        row.addWidget(browse_btn)
        return row

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}"
            f"QLineEdit {{ background-color: {WHITE}; border: 1px solid {BORDER_COLOR}; "
            f"border-radius: {BORDER_RADIUS_PX}px; padding: 4px 8px; color: {BODY_TEXT_COLOR}; }}"
        )

    # ── Private handlers ──────────────────────────────────────────────────────

    def _browse(self, edit: QLineEdit, title: str) -> None:
        chosen = QFileDialog.getExistingDirectory(self, title, edit.text())
        if chosen:
            edit.setText(chosen)

    def _open_logs_folder(self) -> None:
        """Open the logs directory in Windows Explorer."""
        logs_dir = self._logs_edit.text()
        if sys.platform == "win32":
            try:
                subprocess.Popen(["explorer", logs_dir])
            except OSError:
                pass  # explorer not available (e.g. in CI)

    def _reset_to_defaults(self) -> None:
        self._settings.reset_to_defaults()
        self._generated_edit.setText(self._settings.generated_dir)
        self._uploads_edit.setText(self._settings.uploads_dir)
        self._backups_edit.setText(self._settings.backups_dir)
        self._logs_edit.setText(self._settings.logs_dir)

    def _on_save(self) -> None:
        """Persist edited paths to Settings and close."""
        self._settings.set("generated_dir", self._generated_edit.text())
        self._settings.set("uploads_dir", self._uploads_edit.text())
        self._settings.set("backups_dir", self._backups_edit.text())
        self._settings.set("logs_dir", self._logs_edit.text())
        self._settings.save()
        self.accept()
