# simplicitor/app/workers/ollama_worker.py
# Phase 2: Ollama connection polling
import logging

from PySide6.QtCore import QObject, QTimer, Signal

from app.config.defaults import OLLAMA_POLL_INTERVAL_MS
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
        model_params_ready: emitted with (model_name, param_count) only when
            transitioning from disconnected to connected, not on every poll.
    """

    connected = Signal(list, str)       # model_names: list[str], current_model: str
    disconnected = Signal()
    # Use object for param_count so Python's arbitrary-precision int passes through
    # without the 32-bit overflow that affects Signal(str, int) on PySide6.
    model_params_ready = Signal(str, object)  # model_name, param_count: int

    def __init__(self, client: OllamaClient) -> None:
        """Initialise the worker with an OllamaClient instance.

        Args:
            client: The OllamaClient used for all network calls.
        """
        super().__init__()
        self._client = client
        self._timer: QTimer | None = None
        self._was_connected: bool = False
        self._last_running_model: str = ""

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

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

    def stop(self) -> None:
        """Slot — stop the polling timer if it is running."""
        if self._timer is not None:
            self._timer.stop()

    def retry_now(self) -> None:
        """Public slot — trigger an immediate poll (used by Retry buttons in the UI)."""
        self._poll()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _poll(self) -> None:
        """Check Ollama connectivity and emit the appropriate signal.

        Emits ``model_params_ready`` on first connection and whenever the
        running model changes (including when it goes to empty string).
        Never raises.
        """
        try:
            is_connected = self._client.check_connection()

            if is_connected:
                models: list[str] = self._client.get_models()
                running_model: str = self._client.get_running_model()

                first_connection = not self._was_connected
                model_changed = running_model != self._last_running_model

                if first_connection or model_changed:
                    if running_model:
                        try:
                            param_count: int = self._client.get_model_params(running_model)
                            self.model_params_ready.emit(running_model, param_count)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Could not fetch model params: %s", exc)
                    else:
                        # Model was unloaded — signal 0 params so the banner hides
                        self.model_params_ready.emit("", 0)
                    self._last_running_model = running_model

                self._was_connected = True
                self.connected.emit(models, running_model)
            else:
                self._was_connected = False
                self._last_running_model = ""
                self.disconnected.emit()

        except Exception as exc:  # pragma: no cover — defensive catch-all
            logger.warning("OllamaWorker._poll() raised an unexpected exception: %s", exc)
            self._was_connected = False
            self._last_running_model = ""
            self.disconnected.emit()
