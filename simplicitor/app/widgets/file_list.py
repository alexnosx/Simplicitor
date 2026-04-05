# simplicitor/app/widgets/file_list.py
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget

logger = logging.getLogger(__name__)


class FileList(QListWidget):
    """Displays uploaded files ordered most-recent-first.

    Each item stores the absolute file path as UserRole data so it can be
    retrieved without parsing the display text.

    Emits ``file_selected`` whenever the selected item changes.
    """

    file_selected = Signal(str)  # absolute file path

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the FileList.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.currentItemChanged.connect(self._on_item_changed)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_file(self, file_path: str) -> None:
        """Insert *file_path* at the top of the list and select it.

        Args:
            file_path: Absolute path to the uploaded file.
        """
        name = Path(file_path).name
        timestamp = datetime.now().strftime("%H:%M:%S")
        item = QListWidgetItem(f"{name}  ·  {timestamp}")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.insertItem(0, item)
        self.setCurrentRow(0)
        logger.debug("Added to file list: %s", file_path)

    def selected_file(self) -> str | None:
        """Return the absolute path of the currently selected file, or None.

        Returns:
            Absolute path string if a file is selected, otherwise None.
        """
        item = self.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_item_changed(self, current: QListWidgetItem | None, _previous) -> None:
        if current:
            path = current.data(Qt.ItemDataRole.UserRole)
            self.file_selected.emit(path)
