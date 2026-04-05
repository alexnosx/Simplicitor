# tests/test_manipulate_worker.py
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.ollama_client import OllamaConnectionError, OllamaGenerationError
from app.workers.manipulate_worker import ManipulateWorker


def make_worker(
    file_path: str = str(Path(tempfile.gettempdir()) / "doc.txt"),
    prompt: str = "Make it shorter",
    model: str = "llama3",
    client=None,
    backup_dir: str = str(Path(tempfile.gettempdir()) / "backups"),
) -> ManipulateWorker:
    if client is None:
        client = MagicMock()
        client.generate.return_value = "Modified content"
    return ManipulateWorker(
        file_path=file_path,
        prompt=prompt,
        model=model,
        client=client,
        backup_dir=backup_dir,
    )


def test_manipulate_worker_has_signals():
    w = make_worker()
    assert hasattr(w, "started")
    assert hasattr(w, "progress")
    assert hasattr(w, "completed")
    assert hasattr(w, "failed")


def test_manipulate_worker_emits_completed_on_success(qtbot, tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("Hello world", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    client = MagicMock()
    client.generate.return_value = "Hello modified world"

    worker = ManipulateWorker(str(txt), "Make it better", "llama3", client, str(backup_dir))
    with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
        worker.run()

    saved_path, backup_path = blocker.args
    assert Path(saved_path).read_text(encoding="utf-8") == "Hello modified world"
    assert Path(backup_path).exists()
    assert Path(backup_path).read_text(encoding="utf-8") == "Hello world"


def test_manipulate_worker_emits_started(qtbot, tmp_path):
    txt = tmp_path / "f.txt"
    txt.write_text("x")
    client = MagicMock()
    client.generate.return_value = "y"
    worker = ManipulateWorker(str(txt), "change", "llama3", client, str(tmp_path / "bk"))
    started = []
    worker.started.connect(lambda: started.append(True))
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.run()
    assert started


def test_manipulate_worker_emits_progress(qtbot, tmp_path):
    txt = tmp_path / "f.txt"
    txt.write_text("x")
    client = MagicMock()
    client.generate.return_value = "y"
    worker = ManipulateWorker(str(txt), "change", "llama3", client, str(tmp_path / "bk"))
    messages = []
    worker.progress.connect(messages.append)
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.run()
    assert len(messages) >= 2


def test_manipulate_worker_fails_on_ollama_error(qtbot, tmp_path):
    txt = tmp_path / "f.txt"
    txt.write_text("x")
    client = MagicMock()
    client.generate.side_effect = OllamaConnectionError("refused")
    worker = ManipulateWorker(str(txt), "change", "llama3", client, str(tmp_path / "bk"))
    with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
        worker.run()
    assert "AI" in blocker.args[0]


def test_manipulate_worker_fails_on_empty_file(qtbot, tmp_path):
    txt = tmp_path / "empty.txt"
    txt.write_text("")
    client = MagicMock()
    worker = ManipulateWorker(str(txt), "change", "llama3", client, str(tmp_path / "bk"))
    with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
        worker.run()
    assert "empty" in blocker.args[0].lower()
    client.generate.assert_not_called()


def test_manipulate_worker_fails_on_missing_prompt_file(qtbot, tmp_path):
    txt = tmp_path / "f.txt"
    txt.write_text("content")
    client = MagicMock()
    worker = ManipulateWorker(str(txt), "change", "llama3", client, str(tmp_path / "bk"))
    with patch("app.workers.manipulate_worker.PROMPTS_DIR", tmp_path / "nonexistent"):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    assert "configuration" in blocker.args[0].lower()
    client.generate.assert_not_called()


def test_manipulate_worker_emits_failed_on_unreadable_file(qtbot, tmp_path):
    f = tmp_path / "bad.docx"
    f.write_bytes(b"not a real docx")
    client = MagicMock()
    worker = ManipulateWorker(str(f), "change", "llama3", client, str(tmp_path / "bk"))
    with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
        worker.run()
    assert blocker.args[0]  # non-empty error message
