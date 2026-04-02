# tests/test_ollama_client.py
# TDD tests for the Phase 2 OllamaClient REST implementation.
from unittest.mock import MagicMock, patch

import requests

from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaStatus,
)

BASE_URL = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Return a minimal mock that looks like a requests.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    return mock


# ---------------------------------------------------------------------------
# OllamaStatus dataclass (sanity check — must not be removed)
# ---------------------------------------------------------------------------

class TestOllamaStatus:
    def test_defaults(self) -> None:
        s = OllamaStatus()
        assert s.connected is False
        assert s.models == []
        assert s.current_model == ""

    def test_custom_values(self) -> None:
        s = OllamaStatus(connected=True, models=["llama3"], current_model="llama3")
        assert s.connected is True
        assert s.models == ["llama3"]
        assert s.current_model == "llama3"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TestCustomExceptions:
    def test_ollama_connection_error_is_exception(self) -> None:
        exc = OllamaConnectionError("oops")
        assert isinstance(exc, Exception)

    def test_ollama_generation_error_is_exception(self) -> None:
        exc = OllamaGenerationError("bad response")
        assert isinstance(exc, Exception)

    def test_exceptions_are_distinct(self) -> None:
        assert OllamaConnectionError is not OllamaGenerationError


# ---------------------------------------------------------------------------
# OllamaClient.__init__
# ---------------------------------------------------------------------------

class TestOllamaClientInit:
    def test_stores_base_url(self) -> None:
        client = OllamaClient(BASE_URL)
        assert client._base_url == BASE_URL


# ---------------------------------------------------------------------------
# check_connection
# ---------------------------------------------------------------------------

class TestCheckConnection:
    @patch("app.services.ollama_client.requests.get")
    def test_returns_true_on_200(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200)
        client = OllamaClient(BASE_URL)
        assert client.check_connection() is True

    @patch("app.services.ollama_client.requests.get")
    def test_returns_false_on_non_200(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(500)
        client = OllamaClient(BASE_URL)
        assert client.check_connection() is False

    @patch("app.services.ollama_client.requests.get", side_effect=requests.ConnectionError)
    def test_returns_false_on_connection_error(self, _mock_get: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        assert client.check_connection() is False

    @patch("app.services.ollama_client.requests.get", side_effect=requests.Timeout)
    def test_returns_false_on_timeout(self, _mock_get: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        assert client.check_connection() is False

    @patch("app.services.ollama_client.requests.get")
    def test_hits_correct_endpoint(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200)
        OllamaClient(BASE_URL).check_connection()
        mock_get.assert_called_once_with(f"{BASE_URL}/api/tags", timeout=3)

    @patch("app.services.ollama_client.requests.get", side_effect=requests.RequestException)
    def test_does_not_raise(self, _mock_get: MagicMock) -> None:
        # Must never raise — only return bool
        client = OllamaClient(BASE_URL)
        result = client.check_connection()
        assert result is False


# ---------------------------------------------------------------------------
# get_models
# ---------------------------------------------------------------------------

class TestGetModels:
    @patch("app.services.ollama_client.requests.get")
    def test_returns_model_names(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            200,
            {"models": [{"name": "llama3"}, {"name": "mistral"}]},
        )
        client = OllamaClient(BASE_URL)
        assert client.get_models() == ["llama3", "mistral"]

    @patch("app.services.ollama_client.requests.get")
    def test_returns_empty_list_when_no_models(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200, {"models": []})
        client = OllamaClient(BASE_URL)
        assert client.get_models() == []

    @patch("app.services.ollama_client.requests.get")
    def test_hits_correct_endpoint(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200, {"models": []})
        OllamaClient(BASE_URL).get_models()
        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert call_url == f"{BASE_URL}/api/tags"

    @patch("app.services.ollama_client.requests.get", side_effect=requests.ConnectionError)
    def test_raises_connection_error_on_network_failure(self, _mock_get: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.get_models()
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass

    @patch("app.services.ollama_client.requests.get", side_effect=requests.Timeout)
    def test_raises_connection_error_on_timeout(self, _mock_get: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.get_models()
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass


# ---------------------------------------------------------------------------
# get_running_model
# ---------------------------------------------------------------------------

class TestGetRunningModel:
    @patch("app.services.ollama_client.requests.get")
    def test_returns_first_model_name(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(
            200,
            {"models": [{"name": "llama3"}, {"name": "mistral"}]},
        )
        client = OllamaClient(BASE_URL)
        assert client.get_running_model() == "llama3"

    @patch("app.services.ollama_client.requests.get")
    def test_returns_empty_string_when_no_model_running(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200, {"models": []})
        client = OllamaClient(BASE_URL)
        assert client.get_running_model() == ""

    @patch("app.services.ollama_client.requests.get")
    def test_hits_ps_endpoint(self, mock_get: MagicMock) -> None:
        mock_get.return_value = _mock_response(200, {"models": []})
        OllamaClient(BASE_URL).get_running_model()
        call_url = mock_get.call_args[0][0]
        assert call_url == f"{BASE_URL}/api/ps"

    @patch("app.services.ollama_client.requests.get", side_effect=requests.ConnectionError)
    def test_raises_connection_error_on_network_failure(self, _mock_get: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.get_running_model()
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass

    @patch("app.services.ollama_client.requests.get")
    def test_get_running_model_raises_on_timeout(self, mock_get: MagicMock) -> None:
        import pytest
        mock_get.side_effect = requests.Timeout()
        client = OllamaClient(BASE_URL)
        with pytest.raises(OllamaConnectionError):
            client.get_running_model()


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------

class TestGetModelInfo:
    @patch("app.services.ollama_client.requests.post")
    def test_returns_response_json(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {"general.parameter_count": 7_000_000_000}, "details": {}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        result = client.get_model_info("llama3")
        assert result == payload

    @patch("app.services.ollama_client.requests.post")
    def test_posts_to_correct_endpoint(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {})
        OllamaClient(BASE_URL).get_model_info("llama3")
        call_url = mock_post.call_args[0][0]
        assert call_url == f"{BASE_URL}/api/show"

    @patch("app.services.ollama_client.requests.post")
    def test_sends_name_in_body(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {})
        OllamaClient(BASE_URL).get_model_info("llama3")
        kwargs = mock_post.call_args[1]
        assert kwargs.get("json") == {"name": "llama3"}

    @patch("app.services.ollama_client.requests.post", side_effect=requests.ConnectionError)
    def test_raises_connection_error(self, _mock_post: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.get_model_info("llama3")
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass


# ---------------------------------------------------------------------------
# get_model_params
# ---------------------------------------------------------------------------

class TestGetModelParams:
    @patch("app.services.ollama_client.requests.post")
    def test_uses_modelinfo_key_when_present(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {"general.parameter_count": 8_000_000_000}, "details": {}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 8_000_000_000

    @patch("app.services.ollama_client.requests.post")
    def test_falls_back_to_details_billion(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {}, "details": {"parameter_size": "7.2B"}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 7_200_000_000

    @patch("app.services.ollama_client.requests.post")
    def test_falls_back_to_details_million(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {}, "details": {"parameter_size": "350M"}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 350_000_000

    @patch("app.services.ollama_client.requests.post")
    def test_falls_back_to_details_kilo(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {}, "details": {"parameter_size": "500K"}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 500_000

    @patch("app.services.ollama_client.requests.post")
    def test_returns_zero_when_keys_missing(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {})
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 0

    @patch("app.services.ollama_client.requests.post")
    def test_returns_zero_on_unparseable_size(self, mock_post: MagicMock) -> None:
        payload = {"modelinfo": {}, "details": {"parameter_size": "unknown"}}
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 0

    @patch("app.services.ollama_client.requests.post", side_effect=requests.ConnectionError)
    def test_returns_zero_on_network_failure(self, _mock_post: MagicMock) -> None:
        # get_model_params should never raise; swallows OllamaConnectionError too
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 0

    @patch("app.services.ollama_client.requests.post")
    def test_prefers_modelinfo_over_details(self, mock_post: MagicMock) -> None:
        """modelinfo key takes precedence over details fallback."""
        payload = {
            "modelinfo": {"general.parameter_count": 13_000_000_000},
            "details": {"parameter_size": "7B"},
        }
        mock_post.return_value = _mock_response(200, payload)
        client = OllamaClient(BASE_URL)
        assert client.get_model_params("llama3") == 13_000_000_000


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

class TestGenerate:
    @patch("app.services.ollama_client.requests.post")
    def test_returns_response_text(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {"response": "Hello, world!"})
        client = OllamaClient(BASE_URL)
        result = client.generate("llama3", "Say hi", "You are helpful")
        assert result == "Hello, world!"

    @patch("app.services.ollama_client.requests.post")
    def test_posts_to_correct_endpoint(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {"response": "ok"})
        OllamaClient(BASE_URL).generate("llama3", "prompt", "system")
        call_url = mock_post.call_args[0][0]
        assert call_url == f"{BASE_URL}/api/generate"

    @patch("app.services.ollama_client.requests.post")
    def test_sends_correct_body_without_format(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {"response": "ok"})
        OllamaClient(BASE_URL).generate("llama3", "the prompt", "the system")
        body = mock_post.call_args[1]["json"]
        assert body["model"] == "llama3"
        assert body["prompt"] == "the prompt"
        assert body["system"] == "the system"
        assert body["stream"] is False
        assert "format" not in body

    @patch("app.services.ollama_client.requests.post")
    def test_sends_format_when_provided(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {"response": "ok"})
        fmt = {"type": "object", "properties": {}}
        OllamaClient(BASE_URL).generate("llama3", "p", "s", output_format=fmt)
        body = mock_post.call_args[1]["json"]
        assert body["format"] == fmt

    @patch("app.services.ollama_client.requests.post", side_effect=requests.ConnectionError)
    def test_raises_connection_error_on_network_failure(self, _mock_post: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.generate("llama3", "p", "s")
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass

    @patch("app.services.ollama_client.requests.post")
    def test_raises_generation_error_on_non_200(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(500, {"error": "model error"})
        client = OllamaClient(BASE_URL)
        try:
            client.generate("llama3", "p", "s")
            assert False, "Expected OllamaGenerationError"
        except OllamaGenerationError:
            pass

    @patch("app.services.ollama_client.requests.post")
    def test_raises_generation_error_when_response_key_missing(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_response(200, {"no_response_key": True})
        client = OllamaClient(BASE_URL)
        try:
            client.generate("llama3", "p", "s")
            assert False, "Expected OllamaGenerationError"
        except OllamaGenerationError:
            pass

    @patch("app.services.ollama_client.requests.post", side_effect=requests.Timeout)
    def test_raises_connection_error_on_timeout(self, _mock_post: MagicMock) -> None:
        client = OllamaClient(BASE_URL)
        try:
            client.generate("llama3", "p", "s")
            assert False, "Expected OllamaConnectionError"
        except OllamaConnectionError:
            pass
