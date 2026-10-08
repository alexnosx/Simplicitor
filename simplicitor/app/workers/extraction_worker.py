"""Qt signals around local extraction; no widgets or content-bearing diagnostics."""
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from app.services.ollama_client import OllamaClient
from extraction.jobs import discard_job, save_candidate
from extraction.models import Candidate, ColumnSpec, ExtractionProfile
from extraction.pipeline import ExtractionCancelled, ExtractionError, extract, propose_columns
from extraction.source_readers import SourceReadError, read_sources
from extraction.xlsx_writer import read_candidate, write_candidate


@dataclass(frozen=True)
class ExtractionSetup:
    """Snapshot of the selected sources, request, confirmed columns, and model."""
    paths: tuple[Path, ...]
    request: str
    columns: tuple[ColumnSpec, ...]
    profile: ExtractionProfile


class ExtractionWorker(QObject):
    """Run one inspection, proposal, extraction, or accepted Save As off-thread."""
    progress = Signal(str)
    inspection_ready = Signal(object)
    columns_ready = Signal(object)
    candidate_ready = Signal(object, object)
    saved = Signal(str)
    failed = Signal(str, object)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, action: str, setup: ExtractionSetup, client: OllamaClient, *,
                 job_dir: Path | None = None, candidate: Candidate | None = None,
                 destination: Path | None = None, acknowledge_issues: bool = False) -> None:
        super().__init__()
        self.action, self.setup, self._client = action, setup, client
        self._job_dir, self._candidate, self._destination = job_dir, candidate, destination
        self._acknowledge = acknowledge_issues
        self._cancel = Event()

    def cancel(self) -> None:
        """Thread-safe cooperative cancellation; accepted file copying finishes."""
        if self.action != "save":
            self._cancel.set()

    def _check_cancel(self) -> None:
        if self._cancel.is_set():
            raise ExtractionCancelled("Cancelled.")

    @Slot()
    def run(self) -> None:
        """Emit one terminal result, then finished, with all file handles closed."""
        try:
            self._check_cancel()
            if self.action == "save":
                self.progress.emit("Saving workbook...")
                path = save_candidate(self._candidate, self._destination, self._acknowledge)
                self.saved.emit(str(path))
                return
            self.progress.emit("Reading sources...")
            documents = read_sources(self.setup.paths)
            self._check_cancel()
            if not documents:
                raise SourceReadError("Choose DOCX or text-layer PDF sources first.")
            self.inspection_ready.emit(documents)
            if self.action == "inspect":
                return
            if not self.setup.profile.model:
                raise ExtractionError("Select an installed local model in the top bar.")
            if self.action == "propose":
                self.progress.emit("Suggesting columns from the first source...")
                columns = propose_columns(self.setup.request, documents[0], self.setup.profile,
                                          self._client, self._cancel)
                self._check_cancel()
                self.columns_ready.emit(columns)
            elif self.action == "extract":
                if self._job_dir is None:
                    raise ValueError("Missing job directory.")
                result = extract(documents, self.setup.columns, self.setup.request,
                                 self.setup.profile, self._client, self._cancel,
                                 lambda _source, _section, done, total:
                                 self.progress.emit(f"Extracting source units: {done} / {total}"))
                self._check_cancel()
                self.progress.emit("Writing and checking the workbook...")
                candidate = write_candidate(result, self.setup.columns,
                                            self._job_dir / "candidate.xlsx")
                cells = read_candidate(candidate)
                self._check_cancel()
                self.candidate_ready.emit(candidate, cells)
            else:
                raise ValueError("Unknown extraction action.")
        except ExtractionCancelled:
            self._discard_failed_job()
            self.cancelled.emit()
        except (SourceReadError, ExtractionError) as exc:
            self._discard_failed_job()
            if self._cancel.is_set():
                self.cancelled.emit()
            else:
                self.failed.emit(str(exc), exc.issues)
        except Exception:
            self._discard_failed_job()
            if self._cancel.is_set():
                self.cancelled.emit()
            else:
                message = ("Could not save the workbook. Choose an .xlsx destination outside the "
                           "sources, acknowledge flagged output, and check write access."
                           if self.action == "save" else
                           "Could not complete the request. Check Ollama, readable sources, "
                           "and Excel text limits, then retry. Your setup is retained.")
                self.failed.emit(message, ())
        finally:
            self.finished.emit()

    def _discard_failed_job(self) -> None:
        if self.action == "extract" and self._job_dir is not None:
            try:
                discard_job(self._job_dir)
            except OSError:
                # The startup retention sweep can retry after handles are released.
                pass
