# simplicitor/app/workers/generate_worker.py
# Phase 3: File generation worker
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.services.file_generator import FileGenerator, FileGenerationError
from app.services.ollama_client import OllamaClient, OllamaConnectionError, OllamaGenerationError

logger = logging.getLogger(__name__)

# Prompts directory: two levels up from this file (app/workers → app → simplicitor), then prompts/
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

_PROMPT_FILES: dict[str, str] = {
    "Word (.docx)": "system_word.txt",
    "Excel (.xlsx)": "system_excel.txt",
    "PowerPoint (.pptx)": "system_pptx.txt",
}


class GenerateWorker(QObject):
    """Runs LLM generation and file writing on a background QThread (Phase 3).

    Signals:
        started: emitted when run() begins.
        progress: emitted with a status message string at key steps.
        completed: emitted with output file path on success.
        failed: emitted with user-friendly error message on failure.
    """

    started = Signal()
    progress = Signal(str)    # status message
    completed = Signal(str)   # output_file_path
    failed = Signal(str)      # user_friendly_error_message

    def __init__(
        self,
        file_type: str,
        save_path: str,
        prompt: str,
        model: str,
        client: OllamaClient,
    ) -> None:
        """Initialise the worker.

        Args:
            file_type: One of the GENERATE_FILE_TYPES values.
            save_path: Full path (including filename) for the output file.
            prompt: The user's natural-language prompt.
            model: Ollama model name to use for generation.
            client: An OllamaClient instance for making API calls.
        """
        super().__init__()
        self.file_type = file_type
        self.save_path = save_path
        self.prompt = prompt
        self.model = model
        self._client = client

    def run(self) -> None:
        """Execute the generation pipeline. Called by QThread via started signal.

        Emits started(), then progress() messages throughout, and finally either
        completed(path) or failed(message).
        """
        self.started.emit()
        self.progress.emit("Sending prompt to AI\u2026")

        # Load system prompt
        prompt_filename = _PROMPT_FILES.get(self.file_type)
        if prompt_filename is None:
            logger.error("No system prompt mapping for file type %r", self.file_type)
            self.failed.emit(f"System configuration error: unknown file type {self.file_type!r}")
            return

        prompt_path = PROMPTS_DIR / prompt_filename
        try:
            system_prompt = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.error("Could not read system prompt file %s: %s", prompt_path, exc)
            self.failed.emit(
                f"System configuration error: missing prompt file {prompt_filename}"
            )
            return

        # Call Ollama without a format constraint: Qwen3 and other thinking models return empty
        # responses when Ollama's json mode is active (the two features conflict). Instead we
        # rely on the system prompt's JSON-only instruction and _clean()'s extraction logic.
        try:
            llm_response = self._client.generate(self.model, self.prompt, system_prompt)
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during generation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return

        self.progress.emit("Generating file\u2026")

        output_path = Path(self.save_path)

        try:
            result_path = FileGenerator().generate(self.file_type, llm_response, output_path)
        except FileGenerationError as exc:
            # Retry once with a simplified prompt
            logger.warning(
                "First generation attempt failed (%s), retrying with simplified prompt", exc
            )
            self.progress.emit("Retrying with simplified prompt\u2026")
            simplified = f"Generate a simple {self.file_type} document about: {self.prompt[:200]}"
            try:
                llm_response2 = self._client.generate(self.model, simplified, system_prompt)
                result_path = FileGenerator().generate(self.file_type, llm_response2, output_path)
            except (OllamaConnectionError, OllamaGenerationError) as retry_exc:
                logger.error("Retry Ollama call failed: %s", retry_exc)
                self.failed.emit(
                    "The AI engine stopped responding. Please check Ollama is running."
                )
                return
            except FileGenerationError as retry_exc:
                logger.error("Retry also produced unparseable response: %s", retry_exc)
                self.failed.emit("Could not generate file. Please try a simpler or shorter prompt.")
                return
            except OSError as retry_exc:
                logger.error("Retry file write failed: %s", retry_exc)
                self.failed.emit(
                    f"Could not save file to {self.save_path}. "
                    "Check the folder exists and you have write permission."
                )
                return
            self.completed.emit(str(result_path))
            return
        except OSError as exc:
            logger.error("File write failed: %s", exc)
            self.failed.emit(
                f"Could not save file to {self.save_path}. "
                "Check the folder exists and you have write permission."
            )
            return

        self.completed.emit(str(result_path))
