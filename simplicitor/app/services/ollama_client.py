# simplicitor/app/services/ollama_client.py
# Phase 2: Ollama REST client
from dataclasses import dataclass, field

import requests

from app.config.defaults import (
    OLLAMA_GENERATE_ENDPOINT,
    OLLAMA_PS_ENDPOINT,
    OLLAMA_SHOW_ENDPOINT,
    OLLAMA_TAGS_ENDPOINT,
    OLLAMA_TIMEOUT_S,
)


class OllamaConnectionError(Exception):
    """Raised when a network-level error prevents reaching the Ollama API."""
    pass


class OllamaGenerationError(Exception):
    """Raised when the Ollama API returns an unexpected or error response during generation."""
    pass


@dataclass
class OllamaStatus:
    """Snapshot of Ollama connectivity state."""
    connected: bool = False
    models: list[str] = field(default_factory=list)
    current_model: str = ""


class OllamaClient:
    """HTTP client for the Ollama local API.

    All network methods raise ``OllamaConnectionError`` on
    ``requests.RequestException``. The ``generate`` method additionally raises
    ``OllamaGenerationError`` when the server returns a non-200 status or the
    response JSON does not contain a ``"response"`` key.

    ``check_connection`` is the sole exception: it never raises and returns a
    plain bool, making it safe to call from a polling loop.
    """

    def __init__(self, base_url: str) -> None:
        """Initialise the client with the Ollama server base URL.

        Args:
            base_url: Root URL of the Ollama server, e.g. ``"http://localhost:11434"``.
        """
        self._base_url = base_url

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def check_connection(self) -> bool:
        """Return ``True`` if Ollama is reachable, ``False`` otherwise.

        Performs a GET to ``/api/tags`` with a 3-second timeout.  Never raises;
        any exception is caught and results in ``False``.
        """
        try:
            response = requests.get(f"{self._base_url}{OLLAMA_TAGS_ENDPOINT}", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    def get_models(self) -> list[str]:
        """Return the list of installed model names from ``/api/tags``.

        Returns:
            A list of model name strings (may be empty).

        Raises:
            OllamaConnectionError: If the request fails for any network reason.
        """
        try:
            response = requests.get(f"{self._base_url}{OLLAMA_TAGS_ENDPOINT}")
            response.raise_for_status()
            models = response.json()["models"]
            return [m["name"] for m in models]
        except requests.RequestException as exc:
            raise OllamaConnectionError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc

    def get_running_model(self) -> str:
        """Return the name of the currently loaded model from ``/api/ps``.

        Returns:
            The model name string, or ``""`` if no model is currently running.

        Raises:
            OllamaConnectionError: If the request fails for any network reason.
        """
        try:
            response = requests.get(f"{self._base_url}{OLLAMA_PS_ENDPOINT}")
            response.raise_for_status()
            models = response.json()["models"]
            return models[0]["name"] if models else ""
        except requests.RequestException as exc:
            raise OllamaConnectionError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc

    def get_model_info(self, name: str) -> dict:
        """Return the raw info dict for a model via ``POST /api/show``.

        Args:
            name: The model name to query (e.g. ``"llama3"``).

        Returns:
            The response JSON as a ``dict``.

        Raises:
            OllamaConnectionError: If the request fails for any network reason.
        """
        try:
            response = requests.post(f"{self._base_url}{OLLAMA_SHOW_ENDPOINT}", json={"name": name})
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise OllamaConnectionError(f"Could not reach Ollama at {self._base_url}: {exc}") from exc

    def get_model_params(self, model_name: str) -> int:
        """Return the parameter count for a model.

        Tries ``info["modelinfo"]["general.parameter_count"]`` first, then falls
        back to parsing ``info["details"]["parameter_size"]`` (e.g. ``"7.2B"``).

        Returns:
            Integer parameter count, or ``0`` if it cannot be determined.
            Never raises.
        """
        try:
            info = self.get_model_info(model_name)
        except OllamaConnectionError:
            return 0

        try:
            return int(info["modelinfo"]["general.parameter_count"])
        except (KeyError, TypeError, ValueError):
            pass

        # Fallback: parse a human-readable size string like "7.2B" or "350M"
        try:
            size_str: str = info["details"]["parameter_size"]
            multipliers = {"B": 1_000_000_000, "M": 1_000_000, "K": 1_000}
            for suffix, multiplier in multipliers.items():
                if size_str.upper().endswith(suffix):
                    numeric_part = size_str[:-1]  # strip trailing letter
                    return int(float(numeric_part) * multiplier)
        except (KeyError, TypeError, ValueError, AttributeError):
            pass

        return 0

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        model: str,
        prompt: str,
        system: str,
        output_format: dict | None = None,
    ) -> str:
        """Send a generation request to ``/api/generate`` and return the response text.

        Args:
            model: The Ollama model name to use.
            prompt: The user prompt text.
            system: The system message text.
            output_format: Optional JSON schema dict passed as Ollama's ``format`` parameter.

        Returns:
            The ``"response"`` field from the Ollama API JSON reply.

        Raises:
            OllamaConnectionError: If the HTTP request fails for any network reason.
            OllamaGenerationError: If the server returns a non-200 status code or
                the response body does not contain a ``"response"`` key.
        """
        body: dict = {
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
        }
        if output_format is not None:
            body["format"] = output_format

        try:
            response = requests.post(
                f"{self._base_url}{OLLAMA_GENERATE_ENDPOINT}",
                json=body,
                timeout=OLLAMA_TIMEOUT_S,
            )
        except requests.RequestException as exc:
            raise OllamaConnectionError(str(exc)) from exc

        if response.status_code != 200:
            raise OllamaGenerationError(
                f"Ollama returned status {response.status_code}: {response.text}"
            )

        data = response.json()
        if "response" not in data:
            raise OllamaGenerationError(
                f"Ollama response missing 'response' key. Got: {list(data.keys())}"
            )

        return data["response"]
