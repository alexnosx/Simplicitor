# simplicitor/main.py
import sys
from pathlib import Path

# Add the simplicitor/ directory to sys.path so "from app.xxx import yyy" works
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from app.config.defaults import APP_NAME, APP_FONT_FAMILY, FONT_SIZE_BODY_PT
from app.config.settings import Settings
from app.utils.logging_setup import setup_logging
from app.main_window import MainWindow


def _config_dir() -> Path:
    """Return the per-user config directory for Simplicitor settings.

    Uses %APPDATA%/Simplicitor on Windows, falling back to ~/.simplicitor.
    """
    appdata = Path.home() / "AppData" / "Roaming" / "Simplicitor"
    appdata.mkdir(parents=True, exist_ok=True)
    return appdata


def main() -> None:
    """Application entry point."""
    settings = Settings(_config_dir())
    setup_logging(settings.logs_dir)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
