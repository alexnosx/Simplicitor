"""The legacy worker is retained for imports but refuses all editing."""
from unittest.mock import MagicMock

import pytest

from app.workers.manipulate_worker import ManipulateWorker


@pytest.mark.parametrize("suffix", [".docx", ".xlsx", ".pptx", ".pdf", ".txt"])
@pytest.mark.parametrize("prompt", ["Make it shorter", "Change the colors"])
def test_disabled_worker_does_not_read_or_write(tmp_path, monkeypatch, suffix, prompt):
    source = tmp_path / ("document" + suffix)
    source.write_bytes(b"original sentinel")
    backup = tmp_path / "backups"
    client = MagicMock()
    reads = []

    def forbidden_read(*args):
        reads.append(True)
        raise AssertionError("Retired worker cannot extract a source")

    monkeypatch.setattr(
        "app.workers.manipulate_worker.FileManipulator.extract_text", forbidden_read
    )
    worker = ManipulateWorker(str(source), prompt, "model", client, str(backup))
    failures = []
    worker.failed.connect(failures.append)
    worker.run()

    assert failures and "disabled" in failures[0].lower()
    assert not reads
    assert source.read_bytes() == b"original sentinel"
    assert not backup.exists()
    client.generate.assert_not_called()


def test_disabled_worker_does_not_need_prompt_or_existing_source(tmp_path, monkeypatch):
    monkeypatch.setattr("app.workers.manipulate_worker.PROMPTS_DIR", tmp_path / "missing")
    worker = ManipulateWorker(
        str(tmp_path / "missing.docx"), "Revise", "model", MagicMock(), str(tmp_path / "bk")
    )
    failures, completions = [], []
    worker.failed.connect(failures.append)
    worker.completed.connect(lambda *args: completions.append(args))
    worker.run()
    assert failures and "disabled" in failures[0].lower()
    assert not completions
    assert not (tmp_path / "bk").exists()
