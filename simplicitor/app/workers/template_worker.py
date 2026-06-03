# simplicitor/app/workers/template_worker.py
# Phase K: Template-based PPTX content generation worker.
import logging

from PySide6.QtCore import QObject, Signal

from app.parsers.llm_response_parser import ParseError
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaTimeoutError,
)
from templates_engine import pipeline
from templates_engine.manifest import Manifest
from templates_engine.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


class TemplateGenerateWorker(QObject):
    """Runs the template generate-validate-repair loop on a background QThread.

    Reuses the moveToThread pattern (started/progress/completed/failed). Renders
    nothing - the dialog renders synchronously after the editable preview. Touches
    no widgets: run() only emits signals, and the progress callback passed into
    pipeline.generate_content only emits a signal (queued to the main thread when
    moved to a worker thread), preserving the no-QWidget-off-thread rule.

    Signals:
        started: emitted when run() begins.
        progress: emitted with the raw phase label produced by
            pipeline.generate_content ("generating" / "validating" / "repairing").
            The dialog maps these labels to display text.
        completed: emitted with the validated content dict {"slides": [...]}.
        failed: emitted with a user-facing error message. Never contains raw
            exception text or model content.
    """

    started = Signal()
    progress = Signal(str)
    completed = Signal(object)   # validated content dict
    failed = Signal(str)

    def __init__(
        self, manifest: Manifest, user_request: str, model: str, client: OllamaClient
    ) -> None:
        super().__init__()
        self._manifest = manifest
        self._user_request = user_request
        self._model = model
        self._client = client

    def run(self) -> None:
        """Execute the generate-validate-repair loop. Called via QThread.started.

        Emits started(), then progress() phase labels, and finally either
        completed(content_dict) or failed(message).
        """
        self.started.emit()
        messages = build_prompt(self._manifest, self._user_request)
        try:
            content = pipeline.generate_content(
                self._manifest,
                messages,
                self._model,
                client=self._client,
                progress=self.progress.emit,
            )
        except OllamaTimeoutError as exc:  # subclass of OllamaConnectionError: catch FIRST
            logger.error("Ollama timed out during template generation: %s", exc)
            self.failed.emit("The AI engine timed out. It may be busy; please try again.")
            return
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during template generation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error during template generation: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return
        except ParseError as exc:
            # Per NOTES.md follow-up #4, schema-invalid-after-repair also arrives here as
            # ParseError. Surface a generation failure, never a "parse error", to the user.
            logger.error("Template content invalid after repair: %s", exc)
            self.failed.emit(
                "The AI could not produce a valid slide structure after retrying. "
                "Try a simpler request or a different model."
            )
            return
        except Exception as exc:  # defensive net; matches OllamaWorker/GenerateWorker
            logger.error("Unexpected error during template generation: %s", exc)
            self.failed.emit(
                "Something went wrong while generating the slides. Please try again."
            )
            return

        self.completed.emit(content)
