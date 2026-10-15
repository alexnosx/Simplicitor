"""Explicit calibration, excluded from ordinary test discovery by its filename."""
import sys
import threading

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot

from tests import freeze_probe


def test_monitor_observes_native_qthread_and_preserves_queued_gui_delivery(qapp, qtbot):
    probe = freeze_probe._PROBE
    assert probe is not None and probe.trace
    identities = []

    class Worker(QObject):
        done = Signal()

        @Slot()
        def run(self):
            identities.append(("worker", threading.get_ident(), QThread.currentThread() == qapp.thread()))
            self.done.emit()

    class Receiver(QObject):
        @Slot()
        def receive(self):
            identities.append(("receiver", threading.get_ident(), QThread.currentThread() == qapp.thread()))

    original = Receiver.receive
    for method, gui in ((Worker.run, False), (Receiver.receive, True)):
        probe.codes[method.__code__] = (method.__qualname__, gui)
        sys.monitoring.set_local_events(probe.tool, method.__code__,
                                        sys.monitoring.events.PY_START | sys.monitoring.events.PY_RETURN)
    receiver, thread = Receiver(), QThread()
    worker = Worker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.done.connect(receiver.receive)
    worker.done.connect(thread.quit, Qt.ConnectionType.DirectConnection)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    qtbot.waitUntil(lambda: len(identities) == 2, timeout=3000)
    assert thread.wait(3000)
    assert identities[0][0] == "worker" and identities[0][2] is False
    assert identities[1] == ("receiver", threading.get_ident(), True)
    assert probe.counts[Worker.run.__qualname__] == probe.counts[Receiver.receive.__qualname__] == 1
    assert Receiver.receive is original
    assert not probe.violations
