"""Explicit regression experiment; excluded from the normal suite by filename.

Without -p tests.freeze_retire_probe these two assertions deliberately fail:
the existing one-shot workers are destroyed on their background threads.
"""
import threading

from docx import Document
from PySide6.QtCore import QThread, Qt
import pytest

from app.workers.edit_worker import EditSetup, EditWorker
from app.workers.extraction_worker import ExtractionSetup, ExtractionWorker
from extraction.models import ExtractionProfile


@pytest.mark.parametrize("kind", ["edit", "extraction"])
def test_worker_destruction_runs_on_gui_thread(kind, qapp, qtbot, tmp_path):
    """Pin the lifetime change, rather than infer success solely from an intermittent loop."""
    path = tmp_path / "synthetic.docx"
    document = Document()
    document.add_paragraph("Synthetic amount 90.")
    document.save(path)
    if kind == "edit":
        worker = EditWorker("open", EditSetup(path=path))
    else:
        worker = ExtractionWorker("inspect", ExtractionSetup(
            (path,), "", (), ExtractionProfile("synthetic:8b")), None)
    thread = QThread()
    worker.moveToThread(thread)
    destroyed = []

    def observe(*_args):
        destroyed.append((QThread.currentThread() == qapp.thread(), threading.get_native_id()))

    worker.destroyed.connect(observe, Qt.ConnectionType.DirectConnection)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit, Qt.ConnectionType.DirectConnection)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    try:
        qtbot.waitUntil(lambda: thread.wait(0) and bool(destroyed), timeout=5000)
        assert destroyed == [(True, threading.get_native_id())]
    finally:
        thread.quit()
        assert thread.wait(3000)
