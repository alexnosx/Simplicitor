# simplicitor/app/workers/ollama_worker.py
# Phase 2: Ollama connection polling
import logging

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from app.config.defaults import OLLAMA_POLL_INTERVAL_MS, OLLAMA_POLL_TIMEOUT_S
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class OllamaWorker(QObject):
    """Polls Ollama connectivity on a background QThread (Phase 2).

    Uses the QThread + moveToThread pattern — never subclasses QThread.
    The QTimer is created in ``setup()`` (not ``__init__``) so it lives on
    the worker thread after ``moveToThread`` has been called.

    Signals:
        connected: emitted with (model_names, current_model) when Ollama responds.
        disconnected: emitted when Ollama stops responding.
        model_params_ready: emitted with (selected_model, param_count) for an
            explicit queued metadata request, independently of the loaded model.
    """

    connected = Signal(list, str)       # model_names: list[str], current_model: str
    disconnected = Signal()
    # Use object for param_count so Python's arbitrary-precision int passes through
    # without the 32-bit overflow that affects Signal(str, int) on PySide6.
    model_params_ready = Signal(str, object)  # model_name, param_count: int
    stopped = Signal()

    def __init__(self, client: OllamaClient) -> None:
        """Initialise the worker with an OllamaClient instance.

        Args:
            client: The OllamaClient used for all network calls.
        """
        super().__init__()
        self._client = client
        self._timer: QTimer | None = None
        self._was_connected: bool = False

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def setup(self) -> None:
        """Slot called when the owning QThread starts (connect thread.started → this).

        Creates and starts the polling QTimer on the worker thread, then calls
        ``_poll()`` immediately for a fast first-check without waiting for the
        first timer fire.
        """
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.setInterval(OLLAMA_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._poll)
        self._timer.start()
        self._poll()

    @Slot()
    def stop(self) -> None:
        """Slot — stop the polling timer if it is running."""
        if self._timer is not None:
            self._timer.stop()
        self.stopped.emit()

    @Slot(str)
    def request_model_params(self, model_name: str) -> None:
        """Look up the selected model on this worker thread; unknown size is zero."""
        try:
            count = self._client.get_model_params(model_name, timeout=OLLAMA_POLL_TIMEOUT_S)
        except Exception:
            count = 0
        self.model_params_ready.emit(model_name, count)

    @Slot()
    def retry_now(self) -> None:
        """Public slot — trigger an immediate poll (used by Retry buttons in the UI)."""
        self._poll()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @Slot()
    def _poll(self) -> None:
        """Check Ollama connectivity and emit the appropriate signal.

        Reports discovery only. Selection-driven metadata has its own slot.
        """
        try:
            is_connected = self._client.check_connection()

            if is_connected:
                # Short timeouts: a hung Ollama socket must not stall a poll
                # tick for the full OLLAMA_TIMEOUT_S.
                models: list[str] = self._client.get_models(timeout=OLLAMA_POLL_TIMEOUT_S)
                running_model: str = self._client.get_running_model(timeout=OLLAMA_POLL_TIMEOUT_S)

                logger.info(
                    "Ollama connected: %d model(s) installed, running=%r",
                    len(models),
                    running_model or "(none)",
                )
                self._was_connected = True
                self.connected.emit(models, running_model)
            else:
                self._was_connected = False
                self.disconnected.emit()

        except Exception as exc:  # pragma: no cover — defensive catch-all
            logger.warning("OllamaWorker._poll() raised an unexpected exception: %s", exc)
            self._was_connected = False
            self.disconnected.emit()
