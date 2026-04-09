# simplicitor/app/workers/manipulate_worker.py
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.config.defaults import MAX_MANIPULATION_CHARS
from app.services.backup_service import BackupService
from app.services.file_manipulator import FileManipulator, ManipulationError
from app.services.ollama_client import OllamaClient, OllamaConnectionError, OllamaGenerationError

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
_SYSTEM_PROMPT_FILE = "system_manipulate.txt"


class ManipulateWorker(QObject):
    """Runs the file manipulation pipeline on a background QThread (Phase 4).

    Workflow: read system prompt → extract text → backup → call Ollama → write back.

    Signals:
        started: emitted when run() begins.
        progress: emitted with a status string at each pipeline step.
        completed: emitted with (saved_path, backup_path) on success.
        failed: emitted with a user-friendly message on any failure.
    """

    started = Signal()
    progress = Signal(str)
    completed = Signal(str, str)  # saved_path, backup_path
    failed = Signal(str)

    def __init__(
        self,
        file_path: str,
        prompt: str,
        model: str,
        client: OllamaClient,
        backup_dir: str,
    ) -> None:
        """Initialise the worker.

        Args:
            file_path: Absolute path to the file to manipulate.
            prompt: The user's natural-language change instruction.
            model: Ollama model name.
            client: OllamaClient instance for API calls.
            backup_dir: Directory in which to store the file backup.
        """
        super().__init__()
        self.file_path = file_path
        self.prompt = prompt
        self.model = model
        self._client = client
        self.backup_dir = backup_dir

    def run(self) -> None:
        """Execute the manipulation pipeline. Called by QThread via started signal."""
        # Load system prompt
        prompt_path = PROMPTS_DIR / _SYSTEM_PROMPT_FILE
        try:
            system_prompt = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Could not read system prompt %s: %s", prompt_path, exc)
            self.failed.emit("System configuration error: missing manipulation prompt file.")
            return

        self.started.emit()

        # Extract text from file
        self.progress.emit("Reading file\u2026")
        try:
            original_text = FileManipulator().extract_text(Path(self.file_path))
        except ManipulationError as exc:
            logger.error("Text extraction failed for %s: %s", self.file_path, exc)
            self.failed.emit(f"Could not read file: {exc}")
            return

        if not original_text.strip():
            self.failed.emit("This file appears to be empty.")
            return

        # Warn if truncated
        if len(original_text) >= MAX_MANIPULATION_CHARS:
            self.progress.emit(
                "File is large \u2014 only the first portion will be processed\u2026"
            )
            logger.warning("File content truncated: %s", self.file_path)

        # Create backup
        self.progress.emit("Creating backup\u2026")
        try:
            backup_path = BackupService().backup_if_needed(
                Path(self.file_path), Path(self.backup_dir)
            )
        except OSError as exc:
            logger.error("Backup failed for %s: %s", self.file_path, exc)
            self.failed.emit(
                "Could not create a backup. Check that the backup folder exists "
                "and you have write permission."
            )
            return

        # Send to Ollama
        self.progress.emit("Sending to AI\u2026")
        user_prompt = f"File content:\n{original_text}\n\nInstruction:\n{self.prompt}"
        try:
            llm_response = self._client.generate(self.model, user_prompt, system_prompt)
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during manipulation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return

        # Write changes back
        self.progress.emit("Saving changes\u2026")
        try:
            result_path = FileManipulator().apply_changes(
                Path(self.file_path), original_text, llm_response
            )
        except ManipulationError as exc:
            logger.error("apply_changes failed for %s: %s", self.file_path, exc)
            self.failed.emit(f"Could not save changes: {exc}")
            return

        self.completed.emit(str(result_path), str(backup_path))
        logger.info("Manipulation complete: %s (backup: %s)", result_path, backup_path)
