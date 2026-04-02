# simplicitor/app/workers/manipulate_worker.py
# Phase 4: File manipulation worker
from PySide6.QtCore import QObject, Signal


class ManipulateWorker(QObject):
    """Runs LLM manipulation and file write-back on a background QThread (Phase 4).

    Signals:
        completed: emitted with (saved_path, backup_path) on success.
        failed: emitted with user-friendly error message on failure.
    """

    completed = Signal(str, str)   # saved_path, backup_path
    failed = Signal(str)           # user_friendly_error_message

    def __init__(self, file_path: str, prompt: str, model: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.prompt = prompt
        self.model = model

    def run(self) -> None:
        """Execute manipulation pipeline. Called by QThread."""
        pass  # Phase 4
