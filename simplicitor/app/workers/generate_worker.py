# simplicitor/app/workers/generate_worker.py
# Phase 3: File generation worker
from PySide6.QtCore import QObject, Signal


class GenerateWorker(QObject):
    """Runs LLM generation and file writing on a background QThread (Phase 3).

    Signals:
        completed: emitted with output file path on success.
        failed: emitted with user-friendly error message on failure.
    """

    completed = Signal(str)   # output_file_path
    failed = Signal(str)      # user_friendly_error_message

    def __init__(self, file_type: str, save_path: str, prompt: str, model: str) -> None:
        super().__init__()
        self.file_type = file_type
        self.save_path = save_path
        self.prompt = prompt
        self.model = model

    def run(self) -> None:
        """Execute generation pipeline. Called by QThread."""
        pass  # Phase 3
