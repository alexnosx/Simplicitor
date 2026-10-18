"""Open existing local files and folders through the platform's desktop service."""
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


def open_local_path(path: str | Path) -> bool:
    """Return whether the desktop service accepted a readable local target."""
    try:
        target = Path(path).absolute()
        if not target.exists() or not os.access(target, os.R_OK):
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
    except (OSError, ValueError):
        return False
