# simplicitor/main.py
import sys
from pathlib import Path

# Add the simplicitor/ directory to sys.path so "from app.xxx import yyy" works
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_BODY_PT,
)
from app.config.styles import input_styles
from app.config.settings import Settings
from app.utils.logging_setup import setup_logging
from app.utils.file_utils import resource_path
from app.main_window import MainWindow
from templates_engine.config import ensure_default_templates, get_app_data_dir


def main() -> None:
    """Application entry point."""
    config_dir = get_app_data_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    settings = Settings(config_dir)
    setup_logging(settings.logs_dir)
    # Ensure the curated default templates are present in the user's Templates folder.
    ensure_default_templates(Path(settings.templates_dir))

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    icon_path = resource_path("assets/icons/simplicitor.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(input_styles())

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
