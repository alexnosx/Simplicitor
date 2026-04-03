# tests/test_generate_worker.py
# Phase 3: Tests for GenerateWorker

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.workers.generate_worker import GenerateWorker
from app.services.ollama_client import OllamaConnectionError, OllamaGenerationError


def make_worker(
    file_type: str = "Word (.docx)",
    save_path: str = "/tmp/out.docx",
    prompt: str = "Write something",
    model: str = "llama3",
) -> GenerateWorker:
    client = MagicMock()
    client.generate.return_value = '{"title": "T", "sections": []}'
    return GenerateWorker(
        file_type=file_type,
        save_path=save_path,
        prompt=prompt,
        model=model,
        client=client,
    )


def test_generate_worker_has_signals():
    w = make_worker()
    assert hasattr(w, "started")
    assert hasattr(w, "progress")
    assert hasattr(w, "completed")
    assert hasattr(w, "failed")


def test_generate_worker_emits_completed_on_success(qtbot, tmp_path):
    out = tmp_path / "out.docx"
    client = MagicMock()
    client.generate.return_value = (
        '{"title": "T", "sections": [{"heading": "H", "content": "Hello", "type": "text"}]}'
    )
    worker = GenerateWorker("Word (.docx)", str(out), "Make a report", "llama3", client)
    with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
        worker.run()
    assert blocker.args[0] == str(out)
    assert out.exists()


def test_generate_worker_emits_failed_on_ollama_connection_error(qtbot, tmp_path):
    client = MagicMock()
    client.generate.side_effect = OllamaConnectionError("connection refused")
    worker = GenerateWorker("Word (.docx)", str(tmp_path / "out.docx"), "prompt", "llama3", client)
    with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
        worker.run()
    assert "AI generation failed" in blocker.args[0]


def test_generate_worker_emits_failed_on_ollama_generation_error(qtbot, tmp_path):
    client = MagicMock()
    client.generate.side_effect = OllamaGenerationError("bad response")
    worker = GenerateWorker("Word (.docx)", str(tmp_path / "out.docx"), "prompt", "llama3", client)
    with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
        worker.run()
    assert "AI generation failed" in blocker.args[0]


def test_generate_worker_retries_on_parse_failure(qtbot, tmp_path):
    out = tmp_path / "out.docx"
    client = MagicMock()
    # First call returns bad JSON, second call returns valid JSON
    client.generate.side_effect = [
        "not json",
        '{"title": "T", "sections": [{"heading": "", "content": "text", "type": "text"}]}',
    ]
    worker = GenerateWorker("Word (.docx)", str(out), "prompt", "llama3", client)
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.run()
    assert client.generate.call_count == 2


def test_generate_worker_fails_after_two_bad_responses(qtbot, tmp_path):
    client = MagicMock()
    client.generate.return_value = "still not json"
    worker = GenerateWorker("Word (.docx)", str(tmp_path / "out.docx"), "prompt", "llama3", client)
    with qtbot.waitSignal(worker.failed, timeout=5000):
        worker.run()
    assert client.generate.call_count == 2


def test_generate_worker_emits_started_signal(qtbot, tmp_path):
    out = tmp_path / "out.docx"
    client = MagicMock()
    client.generate.return_value = (
        '{"title": "T", "sections": [{"heading": "H", "content": "C", "type": "text"}]}'
    )
    worker = GenerateWorker("Word (.docx)", str(out), "prompt", "llama3", client)
    started_emitted = []
    worker.started.connect(lambda: started_emitted.append(True))
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.run()
    assert started_emitted, "started signal was not emitted"


def test_generate_worker_emits_progress_signals(qtbot, tmp_path):
    out = tmp_path / "out.docx"
    client = MagicMock()
    client.generate.return_value = (
        '{"title": "T", "sections": [{"heading": "H", "content": "C", "type": "text"}]}'
    )
    worker = GenerateWorker("Word (.docx)", str(out), "prompt", "llama3", client)
    progress_messages = []
    worker.progress.connect(progress_messages.append)
    with qtbot.waitSignal(worker.completed, timeout=5000):
        worker.run()
    assert len(progress_messages) >= 2


def test_generate_worker_missing_prompt_file_emits_failed(qtbot, tmp_path):
    """Worker should emit failed if the system prompt file cannot be read."""
    out = tmp_path / "out.docx"
    client = MagicMock()
    worker = GenerateWorker("Word (.docx)", str(out), "prompt", "llama3", client)

    # Patch the prompts directory to a nonexistent path
    with patch("app.workers.generate_worker.PROMPTS_DIR", tmp_path / "nonexistent"):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    assert "System configuration error" in blocker.args[0]
    # OllamaClient.generate should NOT have been called
    client.generate.assert_not_called()


def test_generate_worker_excel_success(qtbot, tmp_path):
    out = tmp_path / "out.xlsx"
    client = MagicMock()
    client.generate.return_value = (
        '{"sheet_name": "Budget", "headers": ["Item", "Cost"], "rows": [["Rent", "1000"]], "formulas": []}'
    )
    worker = GenerateWorker("Excel (.xlsx)", str(out), "Budget spreadsheet", "llama3", client)
    with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
        worker.run()
    assert blocker.args[0] == str(out)
    assert out.exists()


def test_generate_worker_pptx_success(qtbot, tmp_path):
    out = tmp_path / "out.pptx"
    client = MagicMock()
    client.generate.return_value = (
        '{"title": "My Deck", "slides": [{"title": "Intro", "bullets": ["Point 1"], "type": "content"}]}'
    )
    worker = GenerateWorker("PowerPoint (.pptx)", str(out), "A presentation", "llama3", client)
    with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
        worker.run()
    assert blocker.args[0] == str(out)
    assert out.exists()
