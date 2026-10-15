"""Opt-in causal experiment, not an application fix or ordinary suite fixture.

Return one-shot workers to the GUI thread after their original run method returns,
before QThread finishes and delivers deferred deletion. This tests whether native
worker destruction overlapping GUI work is necessary for the observed lock cycle.
It deliberately leaves engines, result slots and the original run methods intact.
"""
from collections import Counter
from functools import wraps
import threading

from PySide6.QtCore import QCoreApplication, QThread, Slot
import pytest


MOVES = Counter()


@pytest.fixture(autouse=True)
def retire_finished_workers_in_gui(monkeypatch):
    """Move only idle, childless extraction/edit workers, legally from their own thread."""
    from app.workers.edit_worker import EditWorker
    from app.workers.extraction_worker import ExtractionWorker

    def wrap(original):
        @wraps(original)
        @Slot()
        def run(worker):
            try:
                return original(worker)
            finally:
                app = QCoreApplication.instance()
                current = QThread.currentThread()
                if worker.thread() == current and current != app.thread():
                    assert not worker.children(), "Experiment applies only to childless workers"
                    assert worker.moveToThread(app.thread())
                    assert worker.thread() == app.thread()
                    MOVES[(type(worker).__name__, threading.get_native_id())] += 1
        return run

    for cls in (EditWorker, ExtractionWorker):
        monkeypatch.setattr(cls, "run", wrap(cls.run))


def pytest_sessionfinish(session):
    """Retain the exact number of real worker retirements exercised by this experiment."""
    from tests.freeze_probe import _PROBE, write_json
    if _PROBE is not None:
        write_json(_PROBE.directory / "retirements.json", {
            "workers": sum(MOVES.values()),
            "by_worker_and_native_id": {f"{name}:{native}": count
                                        for (name, native), count in sorted(MOVES.items())},
        })
