"""The retired Edit entry points must reject work before touching files."""
from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.main_window import MainWindow
from app.workers.manipulate_worker import ManipulateWorker


@pytest.mark.parametrize("model_output", ["", "Original text", "Truncated"])
def test_worker_rejects_legacy_edit_without_io(tmp_path, model_output):
    source = tmp_path / "private.txt"
    source.write_text("Original text", encoding="utf-8")
    original = source.read_bytes()
    backup = tmp_path / "backup"
    client = MagicMock()
    client.generate.return_value = model_output
    worker = ManipulateWorker(str(source), "Revise", "model", client, str(backup))
    failures, completions, starts = [], [], []
    worker.failed.connect(failures.append)
    worker.completed.connect(lambda *args: completions.append(args))
    worker.started.connect(lambda: starts.append(True))

    worker.run()

    assert source.read_bytes() == original
    assert not backup.exists()
    assert failures and "disabled" in failures[0].lower()
    assert not completions and not starts
    client.generate.assert_not_called()


def test_main_window_blocks_programmatic_save(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(MainWindow, "_start_ollama_worker", lambda self: None)
    source = tmp_path / "private.docx"
    source.write_bytes(b"source sentinel")
    window = MainWindow(Settings(tmp_path))
    qtbot.addWidget(window)
    window._current_model = "model"
    window._ollama_client = MagicMock()
    constructed = MagicMock(side_effect=AssertionError("Edit worker must not be created"))
    monkeypatch.setattr("app.main_window.ManipulateWorker", constructed)

    window._on_save_requested(str(source), "Revise")

    assert not window._edit_panel.isEnabled()
    assert window._create_panel.isEnabled()
    assert "disabled" in window._edit_panel._status_banner._primary_label.text().lower()
    assert source.read_bytes() == b"source sentinel"
    constructed.assert_not_called()
