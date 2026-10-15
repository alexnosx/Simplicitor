"""Qt signals around Edit for Word; no widgets, no document text in diagnostics."""
from dataclasses import dataclass, field
import logging
from pathlib import Path
from threading import Event

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, Slot

from app.config.defaults import EDIT_MAX_INSTRUCTION_CHARS, EDIT_MAX_SELECTION_CHARS
from app.services.ollama_client import OllamaClient
from editing import reading_view
from editing.body_map import selection_problem
from editing.models import EditCandidate, EditError, OpenedDocument
from editing.package import open_document
from editing.patch import build_candidate
from editing.proposal import EditCancelled, request_change
from editing.save import save_candidate

logger = logging.getLogger(__name__)
SELECTION_TOO_LONG = "Select a shorter part (up to about 6,000 characters)."
NO_MODEL = "Open Settings and select an installed local model."
FAILED = "Could not complete the change. Your document was not changed. Try again."


@dataclass(frozen=True)
class EditSetup:
    """Frozen inputs for one action: open (path), propose (opened, range, instruction,
    styles, model, attempt) or save (candidate, destination). The save records the
    destination's state itself, off the GUI thread."""
    path: Path | None = None
    opened: OpenedDocument | None = None
    first: int = 0
    last: int = 0
    instruction: str = ""
    styles: dict[int, str] = field(default_factory=dict)
    model: str = ""
    attempt: int = 0
    candidate: EditCandidate | None = None
    destination: Path | None = None


class EditWorker(QObject):
    """Run one open, propose or accepted save off the GUI thread."""
    opened = Signal(object, object)
    proposed = Signal(object, object, object)
    saved = Signal(str)
    failed = Signal(str, str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, action: str, setup: EditSetup, client: OllamaClient | None = None) -> None:
        super().__init__()
        self.action, self.setup, self._client = action, setup, client
        self._cancel = Event()

    def cancel(self) -> None:
        """Thread-safe cooperative cancellation; an accepted save finishes."""
        if self.action != "save":
            self._cancel.set()

    @Slot()
    def run(self) -> None:
        """Emit one terminal signal, then finished."""
        try:
            if self._cancel.is_set():
                raise EditCancelled()
            if self.action == "open":
                document = open_document(self.setup.path)
                view = reading_view.build(document)
                if self._cancel.is_set():
                    raise EditCancelled()
                self.opened.emit(document, view)
            elif self.action == "propose":
                self._propose()
            elif self.action == "save":
                path = save_candidate(self.setup.candidate, self.setup.destination)
                self.saved.emit(str(path))
            else:
                raise ValueError("Unknown edit action.")
        except EditCancelled:
            self.cancelled.emit()
        except EditError as exc:
            logger.info("Edit %s refused: %s", self.action, type(exc).__name__)
            if self._cancel.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc), exc.outcome)
        except Exception as exc:
            logger.warning("Edit %s failed: %s", self.action, type(exc).__name__)
            if self._cancel.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(FAILED, "failed")
        finally:
            # Avoid concurrent worker destruction and GUI-side Qt/GIL locking.
            current_thread = QThread.currentThread()
            gui_thread = QCoreApplication.instance().thread()
            if self.thread() == current_thread and current_thread != gui_thread:
                self.moveToThread(gui_thread)
            self.finished.emit()

    def _propose(self) -> None:
        setup = self.setup
        opened, first, last = setup.opened, setup.first, setup.last
        problem = selection_problem(opened.blocks, first, last)
        if problem:
            raise EditError(problem)
        if sum(len(b.text) for b in opened.paragraphs[first:last + 1]) > EDIT_MAX_SELECTION_CHARS:
            raise EditError(SELECTION_TOO_LONG)
        if not setup.instruction.strip() or len(setup.instruction) > EDIT_MAX_INSTRUCTION_CHARS:
            raise EditError("Describe the change in up to 2,000 characters.")
        if not setup.model:
            raise EditError(NO_MODEL)
        proposal = request_change(opened, first, last, setup.instruction, setup.styles, setup.model,
                                  setup.attempt, self._client, self._cancel)
        candidate = build_candidate(opened, first, last, proposal)
        before = reading_view.paragraphs(opened.data, first, last - first + 1)
        after = reading_view.paragraphs(candidate.data, first, candidate.after_count)
        if self._cancel.is_set():
            raise EditCancelled()
        self.proposed.emit(candidate, before, after)
