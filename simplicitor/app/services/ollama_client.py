# simplicitor/app/services/ollama_client.py
# Phase 2: Ollama REST client
import logging
from dataclasses import dataclass, field

import requests

from app.config.defaults import (
    OLLAMA_CHAT_COMPLETIONS_ENDPOINT,
    OLLAMA_GENERATE_ENDPOINT,
    OLLAMA_PS_ENDPOINT,
    OLLAMA_SHOW_ENDPOINT,
    OLLAMA_TAGS_ENDPOINT,
    OLLAMA_TIMEOUT_S,
    OLLAMA_MANIPULATION_TIMEOUT_S,
)

logger = logging.getLogger(__name__)


class OllamaConnectionError(Exception):
    """Raised when a network-level error prevents reaching the Ollama API."""
    pass


class OllamaTimeoutError(OllamaConnectionError):
    """Raised when an Ollama API call exceeds its timeout."""
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
            response = requests.get(f"{self._base_url}{OLLAMA_TAGS_ENDPOINT}", timeout=OLLAMA_TIMEOUT_S)
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
            response = requests.get(f"{self._base_url}{OLLAMA_PS_ENDPOINT}", timeout=OLLAMA_TIMEOUT_S)
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
            response = requests.post(f"{self._base_url}{OLLAMA_SHOW_ENDPOINT}", json={"name": name}, timeout=OLLAMA_TIMEOUT_S)
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
        output_format: dict | str | None = None,
        timeout: int | None = None,
    ) -> str:
        """Send a generation request to ``/api/generate`` and return the response text.

        Args:
            model: The Ollama model name to use.
            prompt: The user prompt text.
            system: The system message text.
            output_format: Optional value passed as Ollama's ``format`` parameter.
                Use ``"json"`` to request JSON output (universally supported), or a
                JSON Schema dict for structured output (newer Ollama / model support required).
            timeout: Request timeout in seconds. Defaults to ``OLLAMA_TIMEOUT_S``.

        Returns:
            The ``"response"`` field from the Ollama API JSON reply.

        Raises:
            OllamaTimeoutError: If the request exceeds the timeout.
            OllamaConnectionError: If the HTTP request fails for any other network reason.
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

        effective_timeout = timeout if timeout is not None else OLLAMA_TIMEOUT_S

        try:
            response = requests.post(
                f"{self._base_url}{OLLAMA_GENERATE_ENDPOINT}",
                json=body,
                timeout=effective_timeout,
            )
        except requests.Timeout as exc:
            raise OllamaTimeoutError(str(exc)) from exc
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

    def chat_completion(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        timeout: int | None = None,
        max_tokens: int | None = None,
        json_mode: bool = True,
    ) -> str:
        """Send a chat completion request to ``/v1/chat/completions`` and return the content string.

        Args:
            messages: List of message dicts with "role" and "content" keys.
            model: The Ollama model name to use.
            temperature: Sampling temperature (default 0.3 for structured output).
            timeout: Request timeout in seconds. Defaults to ``OLLAMA_TIMEOUT_S``.
            max_tokens: Maximum tokens to generate. None means Ollama's default applies.
                Pass an explicit value to raise the output budget on repair attempts.
            json_mode: When True (default), include ``response_format={"type": "json_object"}``
                in the request body so Ollama applies grammar-constrained decoding. Pass False
                to opt out — the caller is responsible for getting JSON via prompt instructions
                in that case. The templated path opts out because grammar-constrained mode on
                gemma4-class models degenerates into dead-end token streams.

        Returns:
            The ``choices[0]["message"]["content"]`` string from the response.

        Raises:
            OllamaTimeoutError: If the request exceeds the timeout.
            OllamaConnectionError: If the HTTP request fails for any other network reason.
            OllamaGenerationError: If the server returns a non-200 status or the response
                does not contain ``choices[0]["message"]["content"]``.
        """
        body: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        effective_timeout = timeout if timeout is not None else OLLAMA_TIMEOUT_S

        try:
            response = requests.post(
                f"{self._base_url}{OLLAMA_CHAT_COMPLETIONS_ENDPOINT}",
                json=body,
                timeout=effective_timeout,
            )
        except requests.Timeout as exc:
            raise OllamaTimeoutError(str(exc)) from exc
        except requests.RequestException as exc:
            raise OllamaConnectionError(str(exc)) from exc

        if response.status_code != 200:
            raise OllamaGenerationError(
                f"Ollama returned status {response.status_code}: {response.text}"
            )

        try:
            data = response.json()
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "unknown")
        except (KeyError, IndexError, ValueError) as exc:
            raise OllamaGenerationError(
                f"Unexpected response format from Ollama chat completion: {exc}"
            ) from exc

        if finish_reason != "stop":
            logger.warning(
                "chat_completion finish_reason=%s (model=%s)",
                finish_reason,
                model,
            )
        return content
