# simplicitor/app/workers/ollama_worker.py
# Phase 2: Ollama connection polling
from PySide6.QtCore import QObject, Signal


class OllamaWorker(QObject):
    """Polls Ollama connectivity on a background QThread (Phase 2).

    Signals:
        connected: emitted with (model_names, current_model) when Ollama responds.
        disconnected: emitted when Ollama stops responding.
    """

    connected = Signal(list, str)   # model_names: list[str], current_model: str
    disconnected = Signal()

    def poll(self) -> None:
        """Check connectivity and emit connected/disconnected. Called by QTimer."""
        pass  # Phase 2
