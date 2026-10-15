"""One-shot workers finish off-thread but are deleted on the GUI thread."""
from pathlib import Path
import threading
from types import SimpleNamespace

from docx import Document
from PySide6.QtCore import QObject, QThread, Qt
import pytest

from app.services.ollama_client import OllamaConnectionError
from app.workers.edit_worker import EditSetup, EditWorker
from app.workers.extraction_worker import ExtractionSetup, ExtractionWorker
from app.workers.generate_worker import GenerateWorker
from app.workers.manipulate_worker import ManipulateWorker
from app.workers.template_worker import TemplateGenerateWorker
from extraction.models import ExtractionProfile
from templates_engine.manifest import load_manifest


def _worker(kind, outcome, tmp_path, monkeypatch):
    """Use real worker processing, replacing only the model or template-engine boundary."""
    if kind in ("edit", "extraction"):
        source = tmp_path / "synthetic.docx"
        document = Document()
        document.add_paragraph("Synthetic amount 90.")
        document.save(source)
        if outcome == "failure":
            source.write_bytes(b"not a DOCX package")
        if kind == "edit":
            worker = EditWorker("open", EditSetup(path=source))
        else:
            worker = ExtractionWorker("inspect", ExtractionSetup(
                (source,), "", (), ExtractionProfile("synthetic:8b")), None)
        if outcome == "cancelled":
            worker.cancel()
        return worker, (worker.finished,), Qt.ConnectionType.DirectConnection

    if kind == "generate":
        valid = ('{"title":"Synthetic","sections":'
                 '[{"heading":"Terms","content":"Synthetic text.","type":"text"}]}')
        replies = iter(("not json", valid) if outcome == "retry-success" else
                       ("not json", "not json") if outcome == "retry-failure" else (valid,))

        def generate(*_args, **_kwargs):
            if outcome == "failure":
                raise OllamaConnectionError("synthetic offline response")
            return next(replies)

        file_type = "unknown" if outcome == "unknown-type" else "Word (.docx)"
        if outcome == "missing-prompt":
            monkeypatch.setattr("app.workers.generate_worker.PROMPTS_DIR", tmp_path / "missing")
        worker = GenerateWorker(file_type, str(tmp_path / "output.docx"),
                                "A synthetic document", "synthetic:8b",
                                SimpleNamespace(generate=generate))
    elif kind == "template":
        manifest = load_manifest(Path(__file__).parent / "templates_engine" /
                                 "fixtures" / "render_manifest.yaml")

        def pipeline(*_args, **_kwargs):
            if outcome == "failure":
                raise OllamaConnectionError("synthetic offline response")
            return {"path": tmp_path / "output.pptx", "issues": []}

        monkeypatch.setattr("app.workers.template_worker.pipeline.run", pipeline)
        worker = TemplateGenerateWorker(manifest, str(tmp_path), "A synthetic deck",
                                        str(tmp_path / "output.pptx"), "synthetic:8b", None)
    else:
        worker = ManipulateWorker(str(tmp_path / "absent.docx"), "Retired operation",
                                  "synthetic:8b", None, str(tmp_path / "backups"))
    return worker, (worker.completed, worker.failed), Qt.ConnectionType.AutoConnection


@pytest.mark.parametrize("kind,outcome", [
    ("edit", "success"), ("edit", "failure"), ("edit", "cancelled"),
    ("extraction", "success"), ("extraction", "failure"), ("extraction", "cancelled"),
    ("generate", "success"), ("generate", "failure"), ("generate", "unknown-type"),
    ("generate", "missing-prompt"), ("generate", "retry-success"),
    ("generate", "retry-failure"),
    ("template", "success"), ("template", "failure"), ("manipulate", "disabled"),
])
def test_one_shot_worker_is_childless_when_returned_and_deleted_on_gui_thread(
        kind, outcome, qapp, qtbot, tmp_path, monkeypatch):
    """Catch native deletion, premature terminal emission and child ownership regressions."""
    worker, endings, connection_type = _worker(kind, outcome, tmp_path, monkeypatch)
    assert not worker.children()
    thread = QThread()
    worker.moveToThread(thread)
    moves, endings_seen, destroyed = [], [], []
    native_move = QObject.moveToThread

    def observe_move(obj, destination):
        moves.append((obj.thread() == QThread.currentThread(),
                      destination == qapp.thread(), len(obj.children())))
        return native_move(obj, destination)

    def observe_ending(*_args):
        endings_seen.append((worker.thread() == qapp.thread(),
                             QThread.currentThread() != qapp.thread()))

    def observe_destruction(*_args):
        destroyed.append((QThread.currentThread() == qapp.thread(), threading.get_native_id()))

    monkeypatch.setattr(type(worker), "moveToThread", observe_move)
    worker.destroyed.connect(observe_destruction, Qt.ConnectionType.DirectConnection)
    thread.started.connect(worker.run)
    for ending in endings:
        ending.connect(observe_ending, Qt.ConnectionType.DirectConnection)
        ending.connect(thread.quit, connection_type)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    try:
        qtbot.waitUntil(lambda: thread.wait(0) and bool(destroyed), timeout=5000)
        assert destroyed == [(True, threading.get_native_id())]
        assert moves == [(True, True, 0)]
        assert endings_seen == [(True, True)]
    finally:
        thread.quit()
        qtbot.waitUntil(lambda: thread.wait(0), timeout=5000)
        thread.deleteLater()
