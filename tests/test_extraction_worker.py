"""Qt adapter tests exercise the real read/propose/extract/write route."""
import json
from pathlib import Path

from docx import Document
from PySide6.QtCore import QThread
import pytest

from app.workers.extraction_worker import ExtractionSetup, ExtractionWorker
from extraction.jobs import create_job
from extraction.models import ColumnSpec, ExtractionProfile
from extraction.xlsx_writer import read_candidate


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "source.docx"
    doc = Document()
    doc.add_paragraph("ID 00123")
    doc.save(path)
    return ExtractionSetup((path,), "Extract the ID", (ColumnSpec("id", "ID", "Identifier"),),
                           ExtractionProfile("qwen3:8b"))


class Client:
    def __init__(self):
        self.calls = []

    def generate(self, model, prompt, system, **kwargs):
        self.calls.append((model, prompt, kwargs))
        if "columns" in kwargs["output_format"]["properties"]:
            return json.dumps({"columns": [{"label": "ID", "description": "Identifier",
                                            "kind": "nonsense"}]})
        return json.dumps({"records": [{"record_id": "source-1", "fields": {
            "id": {"value": "00123", "quote": "ID 00123", "anchor": "source-1#p:0"}}}]})


def test_inspect_has_no_model_call_and_proposal_uses_first_source(setup, qtbot):
    client = Client()
    worker = ExtractionWorker("inspect", setup, client)
    with qtbot.waitSignal(worker.inspection_ready) as inspected:
        worker.run()
    assert inspected.args[0][0].original_path == setup.paths[0]
    assert client.calls == []
    worker = ExtractionWorker("propose", setup, client)
    with qtbot.waitSignal(worker.columns_ready) as proposed:
        worker.run()
    assert proposed.args[0][0].kind == "text"
    assert "ID 00123" in client.calls[0][1]
    assert client.calls[0][2]["think"] is False


def test_extract_emits_reopened_candidate_and_closes_handles(setup, tmp_path, qtbot):
    job = create_job(tmp_path)
    worker = ExtractionWorker("extract", setup, Client(), job_dir=job)
    with qtbot.waitSignal(worker.candidate_ready) as ready:
        worker.run()
    candidate, cells = ready.args
    assert cells == read_candidate(candidate)
    assert cells[0].value == "00123"
    candidate.path.unlink()  # no workbook handle remains open on Windows


@pytest.mark.parametrize("late", [False, True])
def test_cancel_before_or_after_response_never_emits_candidate(setup, tmp_path, qtbot, late):
    job = create_job(tmp_path)
    client = Client()
    worker = ExtractionWorker("extract", setup, client, job_dir=job)
    original = client.generate
    if late:
        def generate(*args, **kwargs):
            worker.cancel()
            return original(*args, **kwargs)
        client.generate = generate
    else:
        worker.cancel()
    ready = []
    worker.candidate_ready.connect(lambda *args: ready.append(args))
    with qtbot.waitSignal(worker.cancelled):
        worker.run()
    assert ready == [] and not job.exists()


def test_failed_request_is_sanitized_and_setup_retained(setup, tmp_path, qtbot, caplog):
    class Broken(Client):
        def generate(self, *args, **kwargs):
            raise RuntimeError("private-source.docx secret content")
    job = create_job(tmp_path)
    worker = ExtractionWorker("extract", setup, Broken(), job_dir=job)
    with qtbot.waitSignal(worker.failed) as failed:
        worker.run()
    assert "secret" not in repr(failed.args) + caplog.text
    assert worker.setup == setup and not job.exists()


def test_worker_runs_on_qthread_and_finishes(setup, qtbot):
    thread = QThread()
    worker = ExtractionWorker("inspect", setup, Client())
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    with qtbot.waitSignal(thread.finished, timeout=5000):
        thread.start()
    assert not thread.isRunning()
