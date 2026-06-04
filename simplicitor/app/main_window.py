# simplicitor/app/main_window.py
import logging
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from app.config.defaults import (
    APP_NAME, BACKGROUND_COLOR, OLLAMA_BASE_URL,
    WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, SMALL_MODEL_PARAM_THRESHOLD,
    FILE_TYPE_EXTENSIONS,
)
from app.utils.file_utils import resource_path, truncate_path
from app.config.settings import Settings
from app.services.ollama_client import OllamaClient
from app.widgets.capability_banner import CapabilityBanner
from app.widgets.create_panel import CreatePanel
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog
from app.widgets.status_bar import TopBar
from app.widgets.template_dialog import TemplateDialog
from app.workers.generate_worker import GenerateWorker
from app.workers.manipulate_worker import ManipulateWorker
from app.workers.ollama_worker import OllamaWorker
from app.workers.template_worker import TemplateGenerateWorker

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

    # Internal signal: emitting this triggers an immediate Ollama connectivity
    # re-check on the worker thread (cross-thread queued connection).
    _recheck_connection = Signal()

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
        icon_path = resource_path("assets/icons/simplicitor.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central = QWidget()
        central.setStyleSheet(f"background-color: {BACKGROUND_COLOR};")
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

        # Two-panel area — QFrame panels in a horizontal layout with padding and gap
        self._create_panel = CreatePanel(self._settings)
        self._edit_panel = EditPanel(self._settings)

        panels_layout = QHBoxLayout()
        panels_layout.setContentsMargins(16, 16, 16, 16)
        panels_layout.setSpacing(12)
        panels_layout.addWidget(self._create_panel, 1)
        panels_layout.addWidget(self._edit_panel, 1)

        root_layout.addLayout(panels_layout, stretch=1)

    def _connect_signals(self) -> None:
        self._top_bar.settings_requested.connect(self._open_settings)
        self._start_ollama_worker()
        self._create_panel.generate_requested.connect(self._on_generate_requested)
        self._create_panel.template_requested.connect(self._on_template_requested)
        self._edit_panel.save_requested.connect(self._on_save_requested)

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

        # Connectivity → panels (named method also keeps _current_model in sync)
        self._ollama_worker.connected.connect(self._on_ollama_connected)
        self._ollama_worker.disconnected.connect(
            lambda: self._create_panel.set_ollama_connected(False)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._create_panel.set_model_small(False)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._edit_panel.set_ollama_connected(False)
        )

        # Model params → capability banner
        self._ollama_worker.model_params_ready.connect(self._on_model_params_ready)

        # Retry buttons + internal recheck → immediate poll
        self._create_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._edit_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._recheck_connection.connect(self._ollama_worker.retry_now)

        # Capability banner dismiss
        self._capability_banner.dismissed.connect(self._on_banner_dismissed)

        # Model selection tracking
        self._current_model: str = ""
        self._banner_dismissed_for: str = ""
        self._top_bar.model_changed.connect(self._on_model_changed)

        # Generation in-progress guard (explicit flag; more reliable than QThread.isRunning())
        self._generating: bool = False

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
        self._create_panel.set_model_small(0 < param_count < SMALL_MODEL_PARAM_THRESHOLD)
        logger.debug("Model params ready: %s (%d params)", model_name, param_count)

    def _on_banner_dismissed(self) -> None:
        """Record which model the user dismissed the banner for."""
        self._banner_dismissed_for = self._current_model
        logger.debug("Capability banner dismissed for model: %s", self._current_model)

    def _on_ollama_connected(self, models: list[str], current_model: str) -> None:
        """Handle Ollama connected signal — update panels and track the running model.

        Args:
            models: Full list of installed model names.
            current_model: The model currently loaded in Ollama, or "" if none.
        """
        self._create_panel.set_ollama_connected(True)
        self._edit_panel.set_ollama_connected(True)
        if current_model:
            self._current_model = current_model

    def _build_output_path(self, file_type: str, save_dir: str, prompt: str) -> str:
        """Build an auto-generated output file path.

        Filename: first 5 words of prompt (sanitized) + YYYYMMDD_HHMMSS + extension.

        Args:
            file_type: One of the GENERATE_FILE_TYPES values.
            save_dir: Directory path where the file should be saved.
            prompt: The user's natural-language prompt.

        Returns:
            Absolute file path string.
        """
        words = re.sub(r"[^\w\s]", "", prompt).split()[:5]
        base = "_".join(words) if words else "document"
        base = re.sub(r"[^\w]", "_", base)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = FILE_TYPE_EXTENSIONS.get(file_type, ".docx")
        filename = f"{base}_{timestamp}{ext}"
        return str(Path(save_dir) / filename)

    def _on_generate_requested(self, file_type: str, save_dir: str, prompt: str) -> None:
        """Start the GenerateWorker in response to create_panel.generate_requested.

        Args:
            file_type: Selected file type from the Create panel dropdown.
            save_dir: Directory where the generated file should be saved.
            prompt: The user's natural-language prompt.
        """
        if not self._current_model:
            logger.warning("Generate requested but no model selected")
            self._create_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return

        if self._generating:
            logger.warning("Generate requested while previous generation still running; ignoring")
            return

        effective_save_dir = save_dir or self._settings.generated_dir
        try:
            Path(effective_save_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create output directory %s: %s", effective_save_dir, exc)
            self._create_panel.show_status(
                "Cannot create the output folder. Check the path is valid and you have write permission.",
                is_error=True,
            )
            return
        output_path = self._build_output_path(file_type, effective_save_dir, prompt)

        self._generate_worker = GenerateWorker(
            file_type, output_path, prompt, self._current_model, self._ollama_client
        )
        self._generate_thread = QThread(self)
        self._generate_worker.moveToThread(self._generate_thread)

        self._generate_thread.started.connect(self._generate_worker.run)
        self._generate_worker.started.connect(self._on_generate_started)
        self._generate_worker.progress.connect(self._on_generate_progress)
        self._generate_worker.completed.connect(self._on_generate_completed)
        self._generate_worker.failed.connect(self._on_generate_failed)
        self._generate_worker.completed.connect(self._generate_thread.quit)
        self._generate_worker.failed.connect(self._generate_thread.quit)
        self._generate_thread.finished.connect(self._generate_worker.deleteLater)
        self._generate_thread.finished.connect(self._generate_thread.deleteLater)

        self._generating = True
        self._generate_thread.start()
        logger.info("Generation started: file_type=%s, model=%s", file_type, self._current_model)

    def _on_generate_started(self) -> None:
        """Called when GenerateWorker begins execution."""
        self._create_panel.set_generating(True)
        self._create_panel.clear_status()

    def _on_generate_progress(self, msg: str) -> None:
        """Called as GenerateWorker reports progress.

        Args:
            msg: Human-readable progress message.
        """
        self._create_panel.show_status(msg, is_error=False)

    def _on_generate_completed(self, path: str) -> None:
        """Called when GenerateWorker successfully writes the output file.

        Args:
            path: Absolute path to the generated file.
        """
        self._generating = False
        self._create_panel.set_generating(False)
        self._create_panel.clear_prompt()
        self._create_panel.show_status(
            "File created successfully",
            is_error=False,
            secondary=truncate_path(path),
            tooltip=path,
        )
        self._create_panel.show_open_file_btn(path)
        logger.info("Generation completed: %s", path)

    def _on_generate_failed(self, msg: str) -> None:
        """Called when GenerateWorker cannot complete generation.

        Args:
            msg: User-friendly error message.
        """
        self._generating = False
        self._create_panel.set_generating(False)
        self._create_panel.show_status(msg, is_error=True)
        logger.error("Generation failed: %s", msg)
        self._recheck_connection.emit()  # update indicator immediately if Ollama went down

    # ── Template flow (Phase K) ─────────────────────────────────────────────

    def _on_template_requested(self) -> None:
        """Open the template-based PPTX dialog. Guards on a running model
        (same affordance as the freeform create flow)."""
        if not self._current_model:
            logger.warning("Template flow requested but no model selected")
            self._create_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return
        dialog = TemplateDialog(self._settings, parent=self)
        dialog.generate_requested.connect(
            lambda manifest, request: self._start_template_worker(dialog, manifest, request)
        )
        dialog.exec()
        # Dialog dismissed: tear down any worker thread it left behind.
        self._teardown_template_thread()
        self._recheck_connection.emit()

    def _start_template_worker(self, dialog: TemplateDialog, manifest, request: str) -> None:
        """Create and start the MainWindow-owned template worker thread, routing
        its signals to the dialog's on_generate_* slots."""
        if getattr(self, "_template_thread", None) is not None and self._template_thread.isRunning():
            logger.warning("Template generation already running; ignoring")
            return
        self._template_worker = TemplateGenerateWorker(
            manifest, request, self._current_model, self._ollama_client
        )
        self._template_thread = QThread(self)
        self._template_worker.moveToThread(self._template_thread)

        self._template_thread.started.connect(self._template_worker.run)
        self._template_worker.started.connect(dialog.on_generate_started)
        self._template_worker.progress.connect(dialog.on_generate_progress)
        self._template_worker.completed.connect(dialog.on_generate_completed)
        self._template_worker.failed.connect(dialog.on_generate_failed)
        self._template_worker.completed.connect(self._template_thread.quit)
        self._template_worker.failed.connect(self._template_thread.quit)
        self._template_thread.finished.connect(self._template_worker.deleteLater)
        self._template_thread.finished.connect(self._template_thread.deleteLater)
        self._template_thread.finished.connect(self._on_template_thread_finished)

        self._template_thread.start()
        logger.info("Template generation started: model=%s", self._current_model)

    def _on_template_thread_finished(self) -> None:
        """Clear the thread and worker references once finished (their C++ objects
        are deleteLater'd; null the Python refs so nothing touches a freed object)."""
        self._template_thread = None
        self._template_worker = None

    def _teardown_template_thread(self) -> None:
        """Quit + bounded-wait the template thread if still running. Safe if absent.

        A blocked Ollama HTTP call cannot be interrupted; the bounded wait matches the
        existing closeEvent pattern for the generate/manipulate threads. The dialog
        blocks its own close during an in-flight generation, so this normally runs
        against an idle/finished thread. See NOTES.md follow-up on the
        blocked-call-at-app-quit limit (cancellation is out of Phase K scope)."""
        thread = getattr(self, "_template_thread", None)
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(2000)
        self._template_thread = None

    def _on_save_requested(self, file_path: str, prompt: str) -> None:
        """Start the ManipulateWorker in response to edit_panel.save_requested.

        Args:
            file_path: Absolute path to the uploaded file to manipulate.
            prompt: The user's natural-language change instruction.
        """
        if not self._current_model:
            logger.warning("Save requested but no model selected")
            self._edit_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return

        if hasattr(self, "_manipulate_thread") and self._manipulate_thread.isRunning():
            logger.warning("Save requested while previous manipulation still running; ignoring")
            return

        self._manipulate_worker = ManipulateWorker(
            file_path=file_path,
            prompt=prompt,
            model=self._current_model,
            client=self._ollama_client,
            backup_dir=self._settings.backups_dir,
        )
        self._manipulate_thread = QThread(self)
        self._manipulate_worker.moveToThread(self._manipulate_thread)

        self._manipulate_thread.started.connect(self._manipulate_worker.run)
        self._manipulate_worker.started.connect(self._on_manipulate_started)
        self._manipulate_worker.progress.connect(self._on_manipulate_progress)
        self._manipulate_worker.completed.connect(self._on_manipulate_completed)
        self._manipulate_worker.failed.connect(self._on_manipulate_failed)
        self._manipulate_worker.completed.connect(self._manipulate_thread.quit)
        self._manipulate_worker.failed.connect(self._manipulate_thread.quit)
        self._manipulate_thread.finished.connect(self._manipulate_worker.deleteLater)
        self._manipulate_thread.finished.connect(self._manipulate_thread.deleteLater)

        self._manipulate_thread.start()
        logger.info("Manipulation started: file=%s, model=%s", file_path, self._current_model)

    def _on_manipulate_started(self) -> None:
        """Called when ManipulateWorker begins execution."""
        self._edit_panel.set_saving(True)
        self._edit_panel.clear_status()

    def _on_manipulate_progress(self, msg: str) -> None:
        """Called as ManipulateWorker reports progress.

        Args:
            msg: Human-readable progress message.
        """
        self._edit_panel.show_status(msg, is_error=False)

    def _on_manipulate_completed(self, saved_path: str, backup_path: str) -> None:
        """Called when ManipulateWorker successfully writes the output file.

        Args:
            saved_path: Absolute path to the saved (modified) file.
            backup_path: Absolute path to the backup file.
        """
        self._edit_panel.set_saving(False)
        self._edit_panel.clear_prompt()
        secondary = (
            f"Saved: {truncate_path(saved_path)}\n"
            f"Backup: {truncate_path(backup_path)}"
        )
        self._edit_panel.show_status(
            "File saved. Backup created.",
            is_error=False,
            secondary=secondary,
            tooltip=f"Saved: {saved_path}\nBackup: {backup_path}",
        )
        self._edit_panel.show_open_file_btn(saved_path)
        logger.info("Manipulation completed: %s (backup: %s)", saved_path, backup_path)

    def _on_manipulate_failed(self, msg: str) -> None:
        """Called when ManipulateWorker cannot complete manipulation.

        Args:
            msg: User-friendly error message.
        """
        self._edit_panel.set_saving(False)
        self._edit_panel.show_status(msg, is_error=True)
        logger.error("Manipulation failed: %s", msg)
        self._recheck_connection.emit()  # update indicator immediately if Ollama went down

    def _open_settings(self) -> None:
        """Open the settings modal dialog."""
        dialog = SettingsDialog(self._settings, parent=self)
        dialog.exec()
        logger.info("Settings dialog closed")

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Gracefully stop the background workers before closing."""
        if hasattr(self, "_ollama_worker"):
            self._ollama_worker.stop()
        if hasattr(self, "_ollama_thread"):
            self._ollama_thread.quit()
            self._ollama_thread.wait(2000)
        if hasattr(self, "_generate_thread"):
            self._generate_thread.quit()
            self._generate_thread.wait(2000)
        if hasattr(self, "_manipulate_thread"):
            self._manipulate_thread.quit()
            self._manipulate_thread.wait(2000)
        if getattr(self, "_template_thread", None) is not None:
            self._template_thread.quit()
            self._template_thread.wait(2000)
        super().closeEvent(event)
