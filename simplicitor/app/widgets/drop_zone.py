# simplicitor/app/widgets/drop_zone.py
import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import QFileDialog, QLabel, QWidget

from app.config.defaults import (
    BODY_TEXT_COLOR,
    BORDER_COLOR,
    BORDER_RADIUS_PX,
    EDIT_EXTENSIONS,
    EDIT_FILE_FILTER,
    PRIMARY_ACCENT_COLOR,
)

logger = logging.getLogger(__name__)

_STYLE_NORMAL = (
    f"DropZone {{ border: 2px dashed {BORDER_COLOR}; border-radius: {BORDER_RADIUS_PX}px; "
    f"color: {BODY_TEXT_COLOR}; background: transparent; }}"
)
_STYLE_HOVER = (
    f"DropZone {{ border: 2px solid {PRIMARY_ACCENT_COLOR}; border-radius: {BORDER_RADIUS_PX}px; "
    f"color: {BODY_TEXT_COLOR}; background: transparent; }}"
)


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
        self.setText("Drop a file here  or  click to browse")
        self.setObjectName("DropZone")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(80)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_STYLE_NORMAL)

    # ── Drag events ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag if it contains at least one supported file type."""
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls()]
            if any(Path(p).suffix.lower() in EDIT_EXTENSIONS for p in paths):
                event.acceptProposedAction()
                self.setStyleSheet(_STYLE_HOVER)
                return
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        """Restore normal style when drag leaves the zone."""
        self.setStyleSheet(_STYLE_NORMAL)

    def dropEvent(self, event: QDropEvent) -> None:
        """Emit file_dropped for the first accepted file in the drop."""
        self.setStyleSheet(_STYLE_NORMAL)
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
