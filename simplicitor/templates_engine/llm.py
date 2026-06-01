# templates_engine/llm.py
# Phase I: Module-level facade over OllamaClient for the chat-completions path.
from app.config.defaults import OLLAMA_BASE_URL
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaTimeoutError,
)


def _client(client: OllamaClient | None = None) -> OllamaClient:
    if client is not None:
        return client
    return OllamaClient(base_url=OLLAMA_BASE_URL)


def preflight(model: str, client: OllamaClient | None = None) -> None:
    """Check Ollama is reachable and the model is available.

    Raises:
        OllamaTimeoutError: If Ollama is reachable but get_models times out.
        OllamaConnectionError: If Ollama is unreachable.
        OllamaGenerationError: If the model is not in the installed list.
    """
    c = _client(client)
    try:
        models = c.get_models()
    except OllamaTimeoutError as exc:
        raise OllamaTimeoutError(
            f"Ollama timed out during model list. Is it overloaded? ({exc})"
        ) from exc
    except OllamaConnectionError as exc:
        raise OllamaConnectionError(
            f"Ollama is not responding. Check that Ollama is running. ({exc})"
        ) from exc

    if not any(m == model or m.startswith(f"{model}:") for m in models):
        raise OllamaGenerationError(
            f"Model '{model}' is not available in Ollama. "
            f"Run 'ollama pull {model}' to download it."
        )


def generate(
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    client: OllamaClient | None = None,
) -> str:
    """Call Ollama chat completions and return the response content string.

    Args:
        messages: OpenAI-format message list.
        model: Ollama model name.
        temperature: Sampling temperature (default 0.3 for structured output).
        client: Optional injected OllamaClient for testing.

    Returns:
        The raw content string from the model (expected to be JSON).

    Raises:
        OllamaTimeoutError: If the request times out.
        OllamaConnectionError: If the request fails at the network level.
        OllamaGenerationError: If the response is malformed or non-200.
    """
    return _client(client).chat_completion(messages, model, temperature)
