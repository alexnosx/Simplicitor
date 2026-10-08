# simplicitor/app/main_window.py
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QFileDialog, QMainWindow, QVBoxLayout, QWidget

from app.config.defaults import (
    APP_NAME, BACKGROUND_COLOR, OLLAMA_BASE_URL,
    WINDOW_MIN_HEIGHT, WINDOW_MIN_WIDTH, EXTRACTION_MODEL_PARAM_THRESHOLD,
    WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT,
    FILE_TYPE_EXTENSIONS, TEMPLATE_FILE_TYPE,
    LEGACY_EDIT_DISABLED_MESSAGE,
    EXTRACTION_SAVE_FILTER,
)
from app.utils.file_utils import resource_path, truncate_path
from app.config.settings import Settings
from app.services.ollama_client import OllamaClient
from app.widgets.capability_banner import CapabilityBanner
from app.widgets.create_panel import CreatePanel
from app.widgets.create_workspace import CreateWorkspace
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog
from app.widgets.status_bar import TopBar
from app.widgets.template_dialog import TemplateDialog
from app.workers.generate_worker import GenerateWorker
from app.workers.manipulate_worker import ManipulateWorker
from app.workers.ollama_worker import OllamaWorker
from app.workers.template_worker import TemplateGenerateWorker
from app.workers.extraction_worker import ExtractionSetup, ExtractionWorker
from extraction.jobs import cleanup_old_jobs, create_job, discard_job, same_path
from extraction.models import Candidate
from templates_engine.config import ensure_default_templates, get_app_data_dir

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Root application window.

    Hosts source extraction and the existing prompt/template panel in Create.
    Ollama discovery, extraction, and generation run on worker threads.
    """

    # Internal signal: emitting this triggers an immediate Ollama connectivity
    # re-check on the worker thread (cross-thread queued connection).
    _recheck_connection = Signal()
    _model_params_requested = Signal(str)
    _stop_ollama_requested = Signal()

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._loaded_template: dict | None = None
        self._current_model = ""
        self._banner_dismissed_for = ""
        self._generating = self._closing = self._cancel_pending = False
        self._ollama_stop_pending = False
        self._extraction_thread = self._extraction_worker = None
        self._extraction_job: Path | None = None
        self._app_data = get_app_data_dir()
        self._cleanup_error = False
        try:
            cleanup_old_jobs(self._app_data, datetime.now(timezone.utc))
        except OSError:
            self._cleanup_error = True
        self._build_ui()
        self._connect_signals()
        self._apply_styles()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)
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

        # Non-blocking selected-model recommendation.
        self._capability_banner = CapabilityBanner()
        root_layout.addWidget(self._capability_banner)

        self._workspace = CreateWorkspace(self._settings)
        self._create_panel = self._workspace.prompt_panel
        self._extraction_panel = self._workspace.extraction_panel
        # Retain disabled legacy handlers/imports, without mounting Edit in the workspace.
        self._edit_panel = EditPanel(self._settings, self)
        self._edit_panel.setEnabled(False)
        self._edit_panel.show_status(LEGACY_EDIT_DISABLED_MESSAGE, is_error=True)
        self._edit_panel.hide()
        root_layout.addWidget(self._workspace, stretch=1)
        if self._cleanup_error:
            self._extraction_panel.show_status("Some old temporary jobs could not be removed. "
                                               "Check application-data write access.", True)

    def _connect_signals(self) -> None:
        self._top_bar.settings_requested.connect(self._open_settings)
        self._start_ollama_worker()
        self._create_panel.generate_requested.connect(self._on_generate_requested)
        self._create_panel.template_requested.connect(self._on_template_requested)
        self._create_panel.file_type_changed.connect(self._on_file_type_changed)
        self._edit_panel.save_requested.connect(self._on_save_requested)
        self._top_bar.model_changed.connect(self._on_model_changed)
        self._capability_banner.dismissed.connect(self._on_banner_dismissed)
        panel = self._extraction_panel
        panel.inspect_requested.connect(lambda setup: self._start_extraction("inspect", setup))
        panel.propose_requested.connect(lambda setup: self._start_extraction("propose", setup))
        panel.extract_requested.connect(lambda setup: self._start_extraction("extract", setup))
        panel.cancel_requested.connect(self._cancel_extraction)
        panel.save_requested.connect(self._on_extraction_save_requested)
        panel.setup_changed.connect(self._discard_review_job)

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
        self._ollama_thread.finished.connect(self._ollama_worker.deleteLater)
        self._ollama_thread.finished.connect(self._on_ollama_thread_finished)
        self._stop_ollama_requested.connect(self._ollama_worker.stop, Qt.ConnectionType.QueuedConnection)
        self._ollama_worker.stopped.connect(self._ollama_thread.quit, Qt.ConnectionType.DirectConnection)
        self._model_params_requested.connect(self._ollama_worker.request_model_params,
                                             Qt.ConnectionType.QueuedConnection)

        # Connectivity → TopBar
        self._ollama_worker.connected.connect(self._on_ollama_connected)
        self._ollama_worker.disconnected.connect(self._on_ollama_disconnected)

        # Model params → capability banner
        self._ollama_worker.model_params_ready.connect(self._on_model_params_ready)

        # Retry buttons + internal recheck → immediate poll
        self._create_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._edit_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._extraction_panel.retry_requested.connect(self._ollama_worker.retry_now)
        self._recheck_connection.connect(self._ollama_worker.retry_now)

        self._ollama_thread.start()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_model_changed(self, model: str) -> None:
        """Store the currently selected model name when the user changes the dropdown.

        Args:
            model: The newly selected Ollama model name.
        """
        self._current_model = model
        self._banner_dismissed_for = ""
        self._capability_banner.hide_banner()
        self._extraction_panel.set_model(model)
        if model and not self._closing:
            self._model_params_requested.emit(model)

    @Slot(str, object)
    def _on_model_params_ready(self, model_name: str, param_count: int) -> None:
        """Apply metadata only to the selected model; the recommendation never blocks.

        Args:
            model_name: The name of the currently active Ollama model.
            param_count: Approximate parameter count reported by Ollama for the model.
        """
        if model_name != self._current_model or not model_name or self._closing:
            return
        if param_count < EXTRACTION_MODEL_PARAM_THRESHOLD:
            if model_name != self._banner_dismissed_for:
                self._capability_banner.show_banner()
        else:
            self._capability_banner.hide_banner()
        self._create_panel.set_model_small(0 < param_count < EXTRACTION_MODEL_PARAM_THRESHOLD)

    def _on_banner_dismissed(self) -> None:
        """Record which model the user dismissed the banner for."""
        self._banner_dismissed_for = self._current_model
        logger.debug("Capability banner dismissed for model: %s", self._current_model)

    @Slot(list, str)
    def _on_ollama_connected(self, models: list[str], current_model: str) -> None:
        """Handle Ollama connected signal — update panels and track the running model.

        Args:
            models: Full list of installed model names.
            current_model: The model currently loaded in Ollama, or "" if none.
        """
        if self._closing:
            return
        self._top_bar.set_connected(models, current_model)
        self._create_panel.set_ollama_connected(True)
        self._extraction_panel.set_ollama_connected(True)
        self._top_bar._model_combo.setEnabled(not self._operation_busy() and bool(models or current_model))

    @Slot()
    def _on_ollama_disconnected(self) -> None:
        self._top_bar.set_disconnected()
        self._create_panel.set_ollama_connected(False)
        self._extraction_panel.set_ollama_connected(False)
        self._extraction_panel.set_model("")
        self._current_model = ""
        self._capability_banner.hide_banner()

    def _operation_busy(self) -> bool:
        return self._generating or self._extraction_thread is not None

    def _discard_review_job(self) -> None:
        if self._extraction_job is not None and self._extraction_thread is None:
            try:
                discard_job(self._extraction_job)
                self._extraction_job = None
            except OSError:
                self._extraction_panel.show_status("Could not clear the temporary job. "
                                                   "Close any open temporary workbook and retry.", True)

    def _start_extraction(self, action: str, setup: ExtractionSetup, **kwargs) -> None:
        if self._operation_busy() or self._closing:
            return
        panel = self._extraction_panel
        if action != "save":
            panel.clear_review()
            self._discard_review_job()
            if self._extraction_job is not None:
                return
        if action == "extract":
            if not panel._confirmed:
                panel.show_status("Confirm the columns before extracting.", True)
                return
            try:
                self._extraction_job = create_job(self._app_data)
            except OSError:
                panel.show_status("Could not create a temporary job. Check application-data access.", True)
                return
            kwargs["job_dir"] = self._extraction_job
        self._cancel_pending = False
        worker = ExtractionWorker(action, setup, self._ollama_client, **kwargs)
        thread = QThread(self)
        self._extraction_worker, self._extraction_thread = worker, thread
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(panel.show_status)
        worker.inspection_ready.connect(self._on_inspection_ready)
        worker.columns_ready.connect(self._on_columns_ready)
        worker.candidate_ready.connect(self._on_candidate_ready)
        worker.failed.connect(self._on_extraction_failed)
        worker.cancelled.connect(self._on_extraction_cancelled)
        worker.saved.connect(self._on_extraction_saved)
        worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_extraction_thread_finished)
        panel.set_busy(True, saving=action == "save")
        self._workspace.set_busy(True)
        self._top_bar._model_combo.setEnabled(False)
        thread.start()

    @Slot(object)
    def _on_inspection_ready(self, documents: tuple) -> None:
        if not self._cancel_pending and not self._closing:
            self._extraction_panel.show_inspection(documents)

    @Slot(object)
    def _on_columns_ready(self, columns: tuple) -> None:
        if not self._cancel_pending and not self._closing:
            self._extraction_panel.set_columns(columns)

    @Slot(object, object)
    def _on_candidate_ready(self, candidate: Candidate, cells: tuple) -> None:
        if not self._cancel_pending and not self._closing:
            self._extraction_panel.show_candidate(candidate, cells)

    @Slot(str, object)
    def _on_extraction_failed(self, message: str, issues: tuple) -> None:
        if not self._closing:
            self._extraction_panel.show_failure(message, issues)

    @Slot()
    def _on_extraction_cancelled(self) -> None:
        if not self._closing:
            self._extraction_panel.show_status("Cancelled. Your setup is retained.")

    @Slot(str)
    def _on_extraction_saved(self, path: str) -> None:
        if not self._closing:
            self._extraction_panel.show_status(f"Workbook saved successfully: {path}")

    def _cancel_extraction(self) -> None:
        if self._extraction_worker is not None and self._extraction_worker.action != "save":
            self._cancel_pending = True
            self._extraction_worker.cancel()
            self._extraction_panel.clear_review()
            self._extraction_panel.show_status("Cancelling after the current local operation...")
            self._extraction_panel._cancel_btn.setEnabled(False)

    @Slot()
    def _on_extraction_thread_finished(self) -> None:
        self._extraction_thread.wait()
        self._extraction_thread.deleteLater()
        action = self._extraction_worker.action
        self._extraction_thread = self._extraction_worker = None
        if action == "extract" and (self._cancel_pending or self._closing
                                    or self._extraction_panel._candidate is None):
            self._discard_review_job()
        self._extraction_panel.set_busy(False)
        self._workspace.set_busy(False)
        self._top_bar._model_combo.setEnabled(bool(self._top_bar.current_model()))
        self._close_when_idle()

    def _on_extraction_save_requested(self, candidate: Candidate, acknowledge: bool) -> None:
        panel = self._extraction_panel
        if (self._operation_busy() or self._closing or candidate is None
                or candidate != panel._candidate or (candidate.issues and not acknowledge)):
            return
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save extracted workbook", str(Path(self._settings.generated_dir) / "extraction.xlsx"),
            EXTRACTION_SAVE_FILTER, options=QFileDialog.Option(0))
        if not destination:
            return
        path = Path(destination)
        if any(same_path(path, source) for source in candidate.source_paths):
            panel.show_status("Save As cannot replace a source file. Choose another destination.", True)
            return
        if path.suffix.lower() != ".xlsx":
            panel.show_status("Save As requires an .xlsx destination.", True)
            return
        self._start_extraction("save", panel.snapshot(False), candidate=candidate, destination=path,
                               acknowledge_issues=acknowledge)

    @Slot()
    def _on_ollama_thread_finished(self) -> None:
        self._ollama_thread.wait()
        self._ollama_thread.deleteLater()
        self._ollama_thread = self._ollama_worker = None
        self._close_when_idle()

    def _close_when_idle(self) -> None:
        if self._closing:
            QTimer.singleShot(0, self.close)

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

        if self._operation_busy() or self._closing:
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

        # Route to the template engine when a template is loaded and PowerPoint is
        # selected; otherwise the from-scratch generator handles all file types.
        if self._loaded_template is not None and file_type == TEMPLATE_FILE_TYPE:
            self._start_template_generation(output_path, prompt)
            return
        self._start_freeform_generation(file_type, output_path, prompt)

    def _start_freeform_generation(self, file_type: str, output_path: str, prompt: str) -> None:
        """Run the from-scratch GenerateWorker (Word / Excel / PowerPoint from scratch)."""
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
        self._generate_thread.finished.connect(self._on_generate_thread_finished)

        self._generating = True
        self._generate_thread.start()
        logger.info("Generation started: file_type=%s, model=%s", file_type, self._current_model)

    def _on_generate_started(self) -> None:
        """Called when GenerateWorker begins execution."""
        self._create_panel.set_generating(True)
        self._create_panel.clear_status()
        self._workspace.set_busy(True)

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
        self._workspace.set_busy(False)
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
        self._workspace.set_busy(False)
        self._create_panel.show_status(msg, is_error=True)
        logger.error("Generation failed: %s", msg)
        self._recheck_connection.emit()  # update indicator immediately if Ollama went down

    def _on_generate_thread_finished(self) -> None:
        """Clear the thread and worker references once finished (their C++ objects
        are deleteLater'd; null the Python refs so nothing touches a freed object)."""
        self._generate_thread = None
        self._generate_worker = None
        self._close_when_idle()

    # ── Template flow ────────────────────────────────────────────────────────

    def _on_template_requested(self) -> None:
        """Open the template picker. Guards on a running model (same affordance as the
        freeform create flow). Selecting a template loads it onto the Create screen;
        generation then runs from the main Generate button."""
        if not self._current_model:
            logger.warning("Template flow requested but no model selected")
            self._create_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return
        # Startup seeds the defaults once; re-seed here so a Templates folder changed
        # in Settings after launch is never empty (keeps the picker populated and the
        # hard-stop dialog's use-a-built-in recovery branch available). Idempotent:
        # existing defaults, even edited ones, are left untouched.
        ensure_default_templates(Path(self._settings.templates_dir))
        dialog = TemplateDialog(self._settings.templates_dir, parent=self)
        dialog.template_selected.connect(self._on_template_selected)
        dialog.exec()

    def _on_template_selected(self, manifest, template_dir, name: str) -> None:
        """Store the picked template and relabel the Create panel button."""
        self._loaded_template = {"manifest": manifest, "dir": template_dir, "name": name}
        self._create_panel.set_template_loaded(True)
        logger.info("Template loaded: %s", name)

    def _on_file_type_changed(self, file_type: str) -> None:
        """Clear the loaded template when the file type leaves PowerPoint."""
        if file_type != TEMPLATE_FILE_TYPE and self._loaded_template is not None:
            self._loaded_template = None
            self._create_panel.set_template_loaded(False)
            logger.debug("Loaded template cleared (file type now %s)", file_type)

    def _start_template_generation(self, output_path: str, prompt: str) -> None:
        """Run the loaded template through the generate + render pipeline off-thread."""
        lt = self._loaded_template
        self._template_worker = TemplateGenerateWorker(
            lt["manifest"], str(lt["dir"]), prompt, output_path,
            self._current_model, self._ollama_client,
        )
        self._template_thread = QThread(self)
        self._template_worker.moveToThread(self._template_thread)

        self._template_thread.started.connect(self._template_worker.run)
        self._template_worker.started.connect(self._on_template_started)
        self._template_worker.completed.connect(self._on_template_completed)
        self._template_worker.failed.connect(self._on_template_failed)
        self._template_worker.completed.connect(self._template_thread.quit)
        self._template_worker.failed.connect(self._template_thread.quit)
        self._template_thread.finished.connect(self._template_worker.deleteLater)
        self._template_thread.finished.connect(self._template_thread.deleteLater)
        self._template_thread.finished.connect(self._on_template_thread_finished)

        self._generating = True
        self._template_thread.start()
        logger.info("Template generation started: model=%s", self._current_model)

    def _on_template_started(self) -> None:
        """Called when TemplateGenerateWorker begins execution."""
        self._create_panel.set_generating(True)
        self._create_panel.clear_status()
        self._workspace.set_busy(True)

    def _on_template_completed(self, path: str, issues: object) -> None:
        """Called when the template pipeline writes the deck. Clears the loaded template
        (reset-after-generate) and surfaces the result like the freeform flow."""
        self._generating = False
        self._create_panel.set_generating(False)
        self._workspace.set_busy(False)
        self._create_panel.clear_prompt()
        primary = "File created successfully"
        if issues:
            primary += f" ({len(issues)} formatting note(s))"
        self._create_panel.show_status(
            primary, is_error=False, secondary=truncate_path(path), tooltip=path
        )
        self._create_panel.show_open_file_btn(path)
        self._loaded_template = None
        self._create_panel.set_template_loaded(False)
        logger.info("Template generation completed: %s", path)

    def _on_template_failed(self, msg: str) -> None:
        """Called when the template pipeline fails. Keeps the loaded template for retry."""
        self._generating = False
        self._create_panel.set_generating(False)
        self._workspace.set_busy(False)
        self._create_panel.show_status(msg, is_error=True)
        logger.error("Template generation failed: %s", msg)
        self._recheck_connection.emit()  # update indicator immediately if Ollama went down

    def _on_template_thread_finished(self) -> None:
        """Clear the thread and worker references once finished (their C++ objects
        are deleteLater'd; null the Python refs so nothing touches a freed object)."""
        self._template_thread = None
        self._template_worker = None
        self._close_when_idle()

    def _on_save_requested(self, file_path: str, prompt: str) -> None:
        """Start the ManipulateWorker in response to edit_panel.save_requested.

        Args:
            file_path: Absolute path to the uploaded file to manipulate.
            prompt: The user's natural-language change instruction.
        """
        self._edit_panel.show_status(LEGACY_EDIT_DISABLED_MESSAGE, is_error=True)
        return

        if self._operation_busy() or self._closing:
            return
        if not self._current_model:
            logger.warning("Save requested but no model selected")
            self._edit_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return

        if (getattr(self, "_manipulate_thread", None) is not None
                and self._manipulate_thread.isRunning()):
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
        self._manipulate_thread.finished.connect(self._on_manipulate_thread_finished)

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

    def _on_manipulate_thread_finished(self) -> None:
        """Clear the thread and worker references once finished (their C++ objects
        are deleteLater'd; null the Python refs so nothing touches a freed object)."""
        self._manipulate_thread = None
        self._manipulate_worker = None

    def _open_settings(self) -> None:
        """Open the settings modal dialog."""
        dialog = SettingsDialog(self._settings, parent=self)
        dialog.exec()
        logger.info("Settings dialog closed")

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def closeEvent(self, event: QCloseEvent) -> None:
        """Cooperate with workers; never destroy a live thread or delete an open job."""
        self._closing = True
        if self._extraction_worker is not None:
            self._cancel_extraction()
        if getattr(self, "_ollama_worker", None) is not None and not self._ollama_stop_pending:
            self._ollama_stop_pending = True
            self._stop_ollama_requested.emit()
        waiting = False
        for name in ("_ollama_thread", "_extraction_thread", "_generate_thread",
                     "_manipulate_thread", "_template_thread"):
            thread = getattr(self, name, None)
            if thread is not None:
                if thread.isRunning():
                    if name != "_ollama_thread":
                        thread.quit()
                    thread.wait(100)
                # Finished slots must release references and job ownership on the
                # GUI thread before last-window close can stop its event loop.
                waiting = True
        if waiting:
            event.ignore()
            self._extraction_panel.show_status("Waiting for local processing to stop before closing...")
            return
        self._discard_review_job()
        super().closeEvent(event)
