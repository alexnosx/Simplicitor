# tests/test_ollama_worker.py
# Tests for OllamaWorker — uses mocked OllamaClient so no real network calls are made.
# Timer fires are avoided by calling worker._poll() directly.
import pytest
from unittest.mock import MagicMock, patch

from app.workers.ollama_worker import OllamaWorker
from app.services.ollama_client import OllamaClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_worker(qtbot, *, connected: bool = False, models: list[str] | None = None,
                 running_model: str = "", param_count: int = 0) -> OllamaWorker:
    """Return an OllamaWorker with a fully mocked OllamaClient.

    OllamaWorker is a QObject (not a QWidget), so we cannot use qtbot.addWidget.
    We register a finalizer via qtbot.waitSignal-compatible teardown instead.
    """
    client = MagicMock(spec=OllamaClient)
    client.check_connection.return_value = connected
    client.get_models.return_value = models if models is not None else []
    client.get_running_model.return_value = running_model
    client.get_model_params.return_value = param_count
    worker = OllamaWorker(client)
    return worker


# ---------------------------------------------------------------------------
# Signal presence
# ---------------------------------------------------------------------------

def test_worker_has_connected_signal(qtbot) -> None:
    """OllamaWorker exposes the 'connected' signal."""
    worker = _make_worker(qtbot)
    assert hasattr(worker, "connected")


def test_worker_has_disconnected_signal(qtbot) -> None:
    """OllamaWorker exposes the 'disconnected' signal."""
    worker = _make_worker(qtbot)
    assert hasattr(worker, "disconnected")


def test_worker_has_model_params_ready_signal(qtbot) -> None:
    """OllamaWorker exposes the 'model_params_ready' signal."""
    worker = _make_worker(qtbot)
    assert hasattr(worker, "model_params_ready")


# ---------------------------------------------------------------------------
# retry_now delegates to _poll
# ---------------------------------------------------------------------------

def test_retry_now_calls_poll(qtbot) -> None:
    """retry_now() must call _poll() exactly once."""
    worker = _make_worker(qtbot)
    with patch.object(worker, "_poll") as mock_poll:
        worker.retry_now()
    mock_poll.assert_called_once()


# ---------------------------------------------------------------------------
# _poll when connected
# ---------------------------------------------------------------------------

def test_poll_emits_connected_when_ollama_is_up(qtbot) -> None:
    """_poll() emits connected(models, running_model) when check_connection is True."""
    worker = _make_worker(qtbot, connected=True, models=["llama3:8b", "mistral:7b"],
                          running_model="llama3:8b")
    with qtbot.waitSignal(worker.connected, timeout=1000) as blocker:
        worker._poll()
    models, running = blocker.args
    assert models == ["llama3:8b", "mistral:7b"]
    assert running == "llama3:8b"


def test_poll_connected_does_not_emit_disconnected(qtbot) -> None:
    """_poll() must NOT emit disconnected when Ollama is reachable."""
    worker = _make_worker(qtbot, connected=True, models=["llama3:8b"], running_model="llama3:8b")
    received = []
    worker.disconnected.connect(lambda: received.append(True))
    worker._poll()
    assert received == []


# ---------------------------------------------------------------------------
# _poll when disconnected
# ---------------------------------------------------------------------------

def test_poll_emits_disconnected_when_ollama_is_down(qtbot) -> None:
    """_poll() emits disconnected() when check_connection is False."""
    worker = _make_worker(qtbot, connected=False)
    with qtbot.waitSignal(worker.disconnected, timeout=1000):
        worker._poll()


def test_poll_disconnected_does_not_emit_connected(qtbot) -> None:
    """_poll() must NOT emit connected when Ollama is unreachable."""
    worker = _make_worker(qtbot, connected=False)
    received = []
    worker.connected.connect(lambda m, r: received.append(True))
    worker._poll()
    assert received == []


# ---------------------------------------------------------------------------
# model_params_ready — only on transition disconnected → connected
# ---------------------------------------------------------------------------

def test_model_params_ready_emitted_on_first_connection(qtbot) -> None:
    """model_params_ready is emitted when transitioning from disconnected to connected."""
    worker = _make_worker(qtbot, connected=True, models=["llama3:8b"],
                          running_model="llama3:8b", param_count=8_000_000_000)
    # _was_connected starts False, so first successful poll is a transition.
    with qtbot.waitSignal(worker.model_params_ready, timeout=1000) as blocker:
        worker._poll()
    model_name, param_count = blocker.args
    assert model_name == "llama3:8b"
    assert param_count == 8_000_000_000


def test_model_params_ready_not_emitted_on_subsequent_polls(qtbot) -> None:
    """model_params_ready must NOT be emitted on every connected poll, only on transition."""
    worker = _make_worker(qtbot, connected=True, models=["llama3:8b"],
                          running_model="llama3:8b", param_count=8_000_000_000)
    # First poll — triggers the transition
    worker._poll()
    assert worker._was_connected is True

    # Second and third polls — already connected, no re-emission
    emitted = []
    worker.model_params_ready.connect(lambda n, c: emitted.append((n, c)))
    worker._poll()
    worker._poll()
    assert emitted == []


def test_model_params_ready_not_emitted_when_disconnected(qtbot) -> None:
    """model_params_ready is never emitted when Ollama is down."""
    worker = _make_worker(qtbot, connected=False)
    emitted = []
    worker.model_params_ready.connect(lambda n, c: emitted.append((n, c)))
    worker._poll()
    assert emitted == []


def test_model_params_ready_emitted_again_after_reconnect(qtbot) -> None:
    """model_params_ready is emitted again when Ollama reconnects after a drop."""
    client = MagicMock(spec=OllamaClient)
    client.get_models.return_value = ["llama3:8b"]
    client.get_running_model.return_value = "llama3:8b"
    client.get_model_params.return_value = 8_000_000_000
    worker = OllamaWorker(client)

    # First: connect
    client.check_connection.return_value = True
    worker._poll()
    assert worker._was_connected is True

    # Then: disconnect
    client.check_connection.return_value = False
    worker._poll()
    assert worker._was_connected is False

    # Then: reconnect — should emit model_params_ready again
    client.check_connection.return_value = True
    with qtbot.waitSignal(worker.model_params_ready, timeout=1000):
        worker._poll()


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------

def test_poll_handles_exception_gracefully(qtbot) -> None:
    """Exceptions inside _poll() must not propagate; disconnected is emitted instead."""
    client = MagicMock(spec=OllamaClient)
    client.check_connection.side_effect = RuntimeError("network exploded")
    worker = OllamaWorker(client)

    with qtbot.waitSignal(worker.disconnected, timeout=1000):
        worker._poll()  # must not raise


def test_poll_handles_get_models_exception(qtbot) -> None:
    """If get_models() raises after a successful check_connection, emit disconnected."""
    from app.services.ollama_client import OllamaConnectionError
    client = MagicMock(spec=OllamaClient)
    client.check_connection.return_value = True
    client.get_models.side_effect = OllamaConnectionError("models endpoint down")
    worker = OllamaWorker(client)

    with qtbot.waitSignal(worker.disconnected, timeout=1000):
        worker._poll()


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

def test_worker_starts_with_was_connected_false(qtbot) -> None:
    """_was_connected must start as False so the first connection triggers a transition."""
    worker = _make_worker(qtbot)
    assert worker._was_connected is False


def test_worker_timer_is_none_before_setup(qtbot) -> None:
    """_timer must be None before setup() is called (timer is created on the worker thread)."""
    worker = _make_worker(qtbot)
    assert worker._timer is None
