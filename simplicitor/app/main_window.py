# simplicitor/app/main_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt

from app.config.defaults import (
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, APP_NAME, BACKGROUND_COLOR,
)
from app.config.settings import Settings
from app.widgets.status_bar import TopBar
from app.widgets.create_panel import CreatePanel
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Root application window.

    Hosts the TopBar, CreatePanel (left), and EditPanel (right) in a
    horizontal splitter. Opens the SettingsDialog on gear button click.

    Phase 2 adds: Ollama connection worker wired to TopBar.
    Phase 3 adds: generate_requested wired to GenerateWorker.
    Phase 4 adds: save_requested wired to ManipulateWorker.
    """

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self._connect_signals()
        self._apply_styles()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top bar
        self._top_bar = TopBar()
        self._top_bar.setFixedHeight(48)
        root_layout.addWidget(self._top_bar)

        # Two-panel horizontal splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        self._create_panel = CreatePanel(self._settings)
        self._edit_panel = EditPanel(self._settings)

        splitter.addWidget(self._create_panel)
        splitter.addWidget(self._edit_panel)
        splitter.setSizes([500, 500])

        root_layout.addWidget(splitter)

    def _connect_signals(self) -> None:
        self._top_bar.settings_requested.connect(self._open_settings)
        # TODO: Phase 2 — wire OllamaWorker → top_bar.set_connected / set_disconnected
        # TODO: Phase 2 — wire top_bar.model_changed → worker model selection
        # TODO: Phase 3 — wire create_panel.generate_requested → GenerateWorker
        # TODO: Phase 4 — wire edit_panel.save_requested → ManipulateWorker

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background-color: {BACKGROUND_COLOR}; }}")

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Open the settings modal dialog."""
        dialog = SettingsDialog(self._settings, parent=self)
        dialog.exec()
        logger.info("Settings dialog closed")
