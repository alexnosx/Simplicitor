# simplicitor/app/widgets/drop_zone.py
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QWidget

from app.config.defaults import (
    EDIT_EXTENSIONS,
    EDIT_FILE_FILTER,
)

logger = logging.getLogger(__name__)

_DROP_ZONE_IDLE = """
QLabel#DropZone {
    background-color: #FFFFFF;
    border: 2px dashed #9CA3AF;
    border-radius: 6px;
    padding: 24px;
    color: #1E1E1E;
    font-family: 'Segoe UI';
    font-size: 14px;
}
"""

_DROP_ZONE_HOVER = """
QLabel#DropZone {
    background-color: #EFF6FF;
    border: 2px dashed #2563EB;
    border-radius: 6px;
    padding: 24px;
    color: #1E40AF;
    font-family: 'Segoe UI';
    font-size: 14px;
    font-weight: 600;
}
"""


class DropZone(QLabel):
    """Drag-and-drop target that also opens a file dialog on click.

    Accepts .docx, .xlsx, .pptx, .txt, and .pdf files.
    Emits ``file_dropped`` with the absolute path of the accepted file.
    """

    file_dropped = Signal(str)  # absolute path to the accepted file

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the DropZone label.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText("<b>Drop a file here</b> or click to browse")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(80)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_DROP_ZONE_IDLE)

    # ── Drag events ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag if it contains at least one supported file type."""
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls()]
            if any(Path(p).suffix.lower() in EDIT_EXTENSIONS for p in paths):
                event.acceptProposedAction()
                self.setStyleSheet(_DROP_ZONE_HOVER)
                return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Restore normal style when drag leaves the zone."""
        self.setStyleSheet(_DROP_ZONE_IDLE)

    def dropEvent(self, event: QDropEvent) -> None:
        """Emit file_dropped for the first accepted file in the drop."""
        self.setStyleSheet(_DROP_ZONE_IDLE)
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in EDIT_EXTENSIONS:
                logger.debug("File dropped: %s", path)
                self.file_dropped.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()

    # ── Click to browse ───────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Open file dialog on left-click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._open_file_dialog()

    def _open_file_dialog(self) -> None:
        """Show file open dialog and emit file_dropped if a file is selected."""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", EDIT_FILE_FILTER)
        if path:
            logger.debug("File selected via dialog: %s", path)
            self.file_dropped.emit(path)
