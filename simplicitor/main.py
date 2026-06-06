# simplicitor/main.py
import sys
from pathlib import Path

# Add the simplicitor/ directory to sys.path so "from app.xxx import yyy" works
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

from app.config.defaults import (
    APP_NAME, APP_FONT_FAMILY, FONT_SIZE_BODY_PT,
    BORDER_COLOR, PRIMARY_ACCENT_COLOR, BODY_TEXT_COLOR, PANEL_BG_COLOR,
    DISABLED_COLOR, WHITE, BORDER_RADIUS_PX,
)
from app.config.settings import Settings
from app.utils.logging_setup import setup_logging
from app.utils.file_utils import resource_path
from app.main_window import MainWindow
from templates_engine.config import ensure_default_templates


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
    # Ensure the curated default templates are present in the user's Templates folder.
    ensure_default_templates(Path(settings.templates_dir))

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
    icon_path = resource_path("assets/icons/simplicitor.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(
        f"QLineEdit, QPlainTextEdit, QListWidget, QComboBox {{"
        f"    background-color: {WHITE};"
        f"    border: 1px solid {BORDER_COLOR};"
        f"    border-radius: {BORDER_RADIUS_PX}px;"
        f"    padding: 6px 8px;"
        f"    font-family: 'Segoe UI';"
        f"    font-size: 13px;"
        f"    color: {BODY_TEXT_COLOR};"
        f"}}"
        f"QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{"
        f"    border: 1px solid {PRIMARY_ACCENT_COLOR};"
        f"    outline: none;"
        f"}}"
        f"QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled {{"
        f"    background-color: #F9FAFB;"
        f"    color: {DISABLED_COLOR};"
        f"}}"
        f"QListWidget::item {{"
        f"    padding: 6px 8px;"
        f"    border-radius: 2px;"
        f"}}"
        f"QListWidget::item:selected {{"
        f"    background-color: {PRIMARY_ACCENT_COLOR};"
        f"    color: {WHITE};"
        f"}}"
        f"QListWidget::item:hover:!selected {{"
        f"    background-color: #EFF6FF;"
        f"}}"
    )

    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
