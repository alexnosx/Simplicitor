# simplicitor/app/main_window.py
import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

from app.config.defaults import (
    APP_NAME, BACKGROUND_COLOR, OLLAMA_BASE_URL,
    WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, SMALL_MODEL_PARAM_THRESHOLD,
)
from app.config.settings import Settings
from app.services.ollama_client import OllamaClient
from app.widgets.capability_banner import CapabilityBanner
from app.widgets.create_panel import CreatePanel
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog
from app.widgets.status_bar import TopBar
from app.workers.ollama_worker import OllamaWorker

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Root application window.

    Hosts the TopBar, CreatePanel (left), and EditPanel (right) in a
    horizontal splitter. Opens the SettingsDialog on gear button click.

    Phase 2: OllamaWorker runs on a background QThread and drives TopBar
    and CreatePanel connectivity state via signals.
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

        # Capability banner (hidden by default; shown when model has < 7B params)
        self._capability_banner = CapabilityBanner()
        root_layout.addWidget(self._capability_banner)

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
        self._start_ollama_worker()
        # TODO: Phase 3 — wire create_panel.generate_requested → GenerateWorker
        # TODO: Phase 4 — wire edit_panel.save_requested → ManipulateWorker

    def _apply_styles(self) -> None:
        self.setStyleSheet(f"QMainWindow {{ background-color: {BACKGROUND_COLOR}; }}")

    # ── Ollama worker ─────────────────────────────────────────────────────────

    def _start_ollama_worker(self) -> None:
        """Create the OllamaWorker, move it to a background QThread, and start polling."""
        # TODO: ASSUMPTION — URL uses default; Phase 5 can add settings-driven URL
        self._ollama_client = OllamaClient(OLLAMA_BASE_URL)
        self._ollama_thread = QThread(self)
        self._ollama_worker = OllamaWorker(self._ollama_client)
        self._ollama_worker.moveToThread(self._ollama_thread)

        # Lifecycle: run setup() as soon as the thread starts
        self._ollama_thread.started.connect(self._ollama_worker.setup)

        # Connectivity → TopBar
        self._ollama_worker.connected.connect(self._top_bar.set_connected)
        self._ollama_worker.disconnected.connect(self._top_bar.set_disconnected)

        # Connectivity → CreatePanel enable / disable
        self._ollama_worker.connected.connect(
            lambda models, _: self._create_panel.set_ollama_connected(True)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._create_panel.set_ollama_connected(False)
        )

        # Connectivity → EditPanel
        self._ollama_worker.connected.connect(
            lambda models, _: self._edit_panel.set_ollama_connected(True)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._edit_panel.set_ollama_connected(False)
        )

        # Model params → capability banner
        self._ollama_worker.model_params_ready.connect(self._on_model_params_ready)

        # Retry buttons → immediate poll
        self._create_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._edit_panel.retry_requested.connect(self._ollama_worker.retry_now)

        # Capability banner dismiss
        self._capability_banner.dismissed.connect(self._on_banner_dismissed)

        # Model selection tracking
        self._current_model: str = ""
        self._banner_dismissed_for: str = ""
        self._top_bar.model_changed.connect(self._on_model_changed)

        self._ollama_thread.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_model_changed(self, model: str) -> None:
        """Store the currently selected model name when the user changes the dropdown.

        Args:
            model: The newly selected Ollama model name.
        """
        self._current_model = model
        logger.debug("Model changed to: %s", model)

    def _on_model_params_ready(self, model_name: str, param_count: int) -> None:
        """Show capability banner if model has fewer than SMALL_MODEL_PARAM_THRESHOLD params.

        Args:
            model_name: The name of the currently active Ollama model.
            param_count: Approximate parameter count reported by Ollama for the model.
        """
        # Keep _current_model in sync with what the worker reports as running
        if model_name:
            self._current_model = model_name
        if 0 < param_count < SMALL_MODEL_PARAM_THRESHOLD:
            if model_name != self._banner_dismissed_for:
                self._capability_banner.show_banner()
        else:
            self._capability_banner.hide_banner()
        logger.debug("Model params ready: %s (%d params)", model_name, param_count)

    def _on_banner_dismissed(self) -> None:
        """Record which model the user dismissed the banner for."""
        self._banner_dismissed_for = self._current_model
        logger.debug("Capability banner dismissed for model: %s", self._current_model)

    def _open_settings(self) -> None:
        """Open the settings modal dialog."""
        dialog = SettingsDialog(self._settings, parent=self)
        dialog.exec()
        logger.info("Settings dialog closed")

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Gracefully stop the background Ollama worker before closing."""
        if hasattr(self, "_ollama_worker"):
            self._ollama_worker.stop()
        if hasattr(self, "_ollama_thread"):
            self._ollama_thread.quit()
            self._ollama_thread.wait(2000)
        super().closeEvent(event)
