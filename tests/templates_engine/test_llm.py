# tests/templates_engine/test_llm.py
# Phase I: Tests for the llm module-level facade.
import pytest
from unittest.mock import MagicMock
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaTimeoutError,
)
from templates_engine.llm import generate, preflight


def _mock_client(models=None, chat_return=None, raises=None):
    """Build a minimal OllamaClient mock for injection."""
    client = MagicMock(spec=OllamaClient)
    if raises is not None:
        client.get_models.side_effect = raises
        client.chat_completion.side_effect = raises
    else:
        client.get_models.return_value = models or []
        client.chat_completion.return_value = chat_return or '{"slides": []}'
    return client


def test_preflight_raises_connection_error_when_ollama_unreachable():
    mock = _mock_client(raises=OllamaConnectionError("refused"))
    with pytest.raises(OllamaConnectionError, match=r"[Oo]llama"):
        preflight("llama3", client=mock)


def test_preflight_raises_timeout_error_when_get_models_times_out():
    mock = _mock_client(raises=OllamaTimeoutError("timed out"))
    with pytest.raises(OllamaTimeoutError, match=r"[Oo]llama"):
        preflight("llama3", client=mock)


def test_preflight_raises_generation_error_when_model_not_available():
    mock = _mock_client(models=["other_model:latest"])
    with pytest.raises(OllamaGenerationError, match=r"llama3"):
        preflight("llama3", client=mock)


def test_preflight_succeeds_when_model_available():
    mock = _mock_client(models=["llama3:latest", "llama3"])
    preflight("llama3", client=mock)  # must not raise


def test_preflight_succeeds_bare_name_matches_tagged_install():
    # "llama3" requested, "llama3:latest" installed — common Ollama default
    mock = _mock_client(models=["llama3:latest"])
    preflight("llama3", client=mock)  # must not raise


def test_preflight_succeeds_tagged_name_matches_bare_install():
    # "llama3:latest" requested, "llama3" installed — reverse direction
    mock = _mock_client(models=["llama3"])
    preflight("llama3:latest", client=mock)  # must not raise


def test_preflight_fails_when_different_tags_do_not_cross_match():
    # "llama3:7b" requested, only "llama3:latest" installed — distinct models
    mock = _mock_client(models=["llama3:latest"])
    with pytest.raises(OllamaGenerationError, match=r"llama3:7b"):
        preflight("llama3:7b", client=mock)


def test_generate_returns_content_string():
    mock = _mock_client(chat_return='{"slides": []}')
    messages = [{"role": "user", "content": "Make a deck."}]
    result = generate(messages, "llama3", client=mock)
    assert result == '{"slides": []}'
    mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3)


def test_generate_timeout_propagates():
    mock = _mock_client(raises=OllamaTimeoutError("timed out"))
    with pytest.raises(OllamaTimeoutError):
        generate([{"role": "user", "content": "x"}], "llama3", client=mock)


def test_generate_threads_max_tokens_to_chat_completion():
    mock = _mock_client(chat_return='{"slides": []}')
    messages = [{"role": "user", "content": "Make a deck."}]
    generate(messages, "llama3", max_tokens=512, client=mock)
    mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3, max_tokens=512)


def test_generate_threads_timeout_to_chat_completion():
    mock = _mock_client(chat_return='{"slides": []}')
    messages = [{"role": "user", "content": "Make a deck."}]
    generate(messages, "llama3", timeout=180, client=mock)
    mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3, timeout=180)
