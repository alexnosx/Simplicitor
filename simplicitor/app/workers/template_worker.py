# simplicitor/app/workers/template_worker.py
# Template-based PPTX generation worker: runs the full generate + render pipeline
# on a background QThread.
import logging

from PySide6.QtCore import QObject, Signal

from app.parsers.llm_response_parser import ParseError
from app.services.file_manipulator import ManipulationError
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
    """Runs the template generate-validate-repair-render pipeline on a background QThread.

    Reuses the moveToThread pattern (started/completed/failed). Builds the prompt from
    the manifest and the user's request, then runs pipeline.run, which generates content,
    validates and repairs it, and renders the deck to out_path. Touches no widgets: run()
    only emits signals, preserving the no-QWidget-off-thread rule. File I/O (the render)
    stays off the UI thread.

    Signals:
        started: emitted when run() begins.
        completed: emitted with (out_path: str, issues: list[str]) on success. issues are
            non-fatal degrade warnings collected during rendering.
        failed: emitted with a user-facing error message. Never contains raw exception
            text or model content.
    """

    started = Signal()
    completed = Signal(str, object)   # (out_path, issues)
    failed = Signal(str)

    def __init__(
        self,
        manifest: Manifest,
        template_dir: str,
        user_request: str,
        out_path: str,
        model: str,
        client: OllamaClient,
    ) -> None:
        super().__init__()
        self._manifest = manifest
        self._template_dir = template_dir
        self._user_request = user_request
        self._out_path = out_path
        self._model = model
        self._client = client

    def run(self) -> None:
        """Execute generate-validate-repair-render. Called via QThread.started.

        Emits started(), then either completed(out_path, issues) or failed(message).
        """
        self.started.emit()
        messages = build_prompt(self._manifest, self._user_request)
        try:
            result = pipeline.run(
                self._manifest,
                self._template_dir,
                messages,
                self._model,
                self._out_path,
                client=self._client,
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
        except ManipulationError as exc:
            # Render I/O failure or manifest/template index mismatch.
            logger.error("Template render failed (manipulation): %s", exc)
            self.failed.emit(
                "Could not save the presentation, or the template and its manifest "
                "are out of sync."
            )
            return
        except ValueError as exc:
            # Template file could not be opened as a PowerPoint file (corrupt/invalid).
            logger.error("Template render failed (template open): %s", exc)
            self.failed.emit("The template file could not be opened as a PowerPoint file.")
            return
        except Exception as exc:  # defensive net; matches OllamaWorker/GenerateWorker
            logger.error("Unexpected error during template generation: %s", exc)
            self.failed.emit(
                "Something went wrong while generating the slides. Please try again."
            )
            return

        self.completed.emit(str(result["path"]), result["issues"])
