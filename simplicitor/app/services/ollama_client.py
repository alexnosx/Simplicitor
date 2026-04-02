# simplicitor/app/services/ollama_client.py
# Phase 2: Ollama REST client
from dataclasses import dataclass, field


@dataclass
class OllamaStatus:
    """Snapshot of Ollama connectivity state."""
    connected: bool = False
    models: list[str] = field(default_factory=list)
    current_model: str = ""


class OllamaClient:
    """HTTP client for the Ollama local API (Phase 2).

    All methods raise OllamaConnectionError on network failure.
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def check_connection(self) -> bool:
        """Return True if Ollama is reachable."""
        return False  # Phase 2

    def get_models(self) -> list[str]:
        """Return list of installed model names."""
        return []  # Phase 2

    def get_running_model(self) -> str:
        """Return the currently loaded model name, or empty string."""
        return ""  # Phase 2

    def get_model_params(self, model_name: str) -> int:
        """Return parameter count for a model (used for small-model warning)."""
        return 0  # Phase 2

    def generate(self, model: str, prompt: str, system: str) -> str:
        """Send a generation request and return the response text."""
        return ""  # Phase 2/3
