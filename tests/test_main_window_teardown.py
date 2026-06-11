# tests/test_main_window_teardown.py
# Worker-thread teardown after a completed run (NOTES.md follow-up 6): the
# deleteLater'd QThreads must never be touched again — closeEvent must not crash,
# and a second operation in the same session must start a fresh worker.
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QCloseEvent

import pytest

from app.config.settings import Settings
from app.main_window import MainWindow
from app.services.ollama_client import OllamaClient

WORD = "Word (.docx)"


class _FakeGenerateWorker(QObject):
    started = Signal()
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__()

    def run(self):
        self.completed.emit("C:/out/fake.docx")


class _FakeManipulateWorker(QObject):
    started = Signal()
    progress = Signal(str)
    completed = Signal(str, str)
    failed = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__()

    def run(self):
        self.completed.emit("C:/out/fake.docx", "C:/backups/fake_backup.docx")


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    # Keep the connectivity poll cheap and offline.
    monkeypatch.setattr(OllamaClient, "check_connection", lambda self: False)
    settings = Settings(tmp_path)
    settings.set("templates_dir", str(tmp_path / "templates"))
    win = MainWindow(settings)
    qtbot.addWidget(win)
    yield win
    win.close()


def test_close_after_completed_generation_does_not_raise(window, qtbot, tmp_path, monkeypatch):
    """A completed generation deleteLater's its QThread; closeEvent must not quit() it.
    closeEvent is called directly so a RuntimeError propagates instead of being
    swallowed at the C++ signal boundary."""
    monkeypatch.setattr("app.main_window.GenerateWorker", _FakeGenerateWorker)
    window._current_model = "llama3"
    window._on_generate_requested(WORD, str(tmp_path), "make a doc")
    qtbot.waitUntil(
        lambda: getattr(window, "_generate_thread", None) is None, timeout=5000
    )
    window.closeEvent(QCloseEvent())  # must not raise on the freed thread


def test_close_after_completed_manipulation_does_not_raise(window, qtbot, tmp_path, monkeypatch):
    """Same as above for the manipulate thread."""
    monkeypatch.setattr("app.main_window.ManipulateWorker", _FakeManipulateWorker)
    window._current_model = "llama3"
    window._on_save_requested(str(tmp_path / "f.docx"), "change it")
    qtbot.waitUntil(
        lambda: getattr(window, "_manipulate_thread", None) is None, timeout=5000
    )
    window.closeEvent(QCloseEvent())  # must not raise on the freed thread


def test_second_save_after_completed_manipulation_starts_again(window, qtbot, tmp_path, monkeypatch):
    """The in-flight guard must not probe the freed thread: before the fix,
    isRunning() on the deleteLater'd ref raised RuntimeError and every Save after
    the first was a silent no-op for the rest of the session."""
    constructed = []

    class CountingWorker(_FakeManipulateWorker):
        def __init__(self, *args, **kwargs):
            super().__init__()
            constructed.append(1)

    monkeypatch.setattr("app.main_window.ManipulateWorker", CountingWorker)
    window._current_model = "llama3"
    window._on_save_requested(str(tmp_path / "f.docx"), "change it")
    qtbot.waitUntil(
        lambda: getattr(window, "_manipulate_thread", None) is None, timeout=5000
    )
    window._on_save_requested(str(tmp_path / "f.docx"), "change it again")
    qtbot.waitUntil(
        lambda: getattr(window, "_manipulate_thread", None) is None, timeout=5000
    )
    assert len(constructed) == 2
