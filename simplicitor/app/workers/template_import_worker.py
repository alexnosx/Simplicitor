# simplicitor/app/workers/template_import_worker.py
# Template import worker: runs config.import_template (inspect, strip, manifest
# write) on a background QThread so a large uploaded deck does not freeze the UI.
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.services.file_manipulator import ManipulationError
from templates_engine import config

logger = logging.getLogger(__name__)


class TemplateImportWorker(QObject):
    """Runs config.import_template on a background QThread.

    Reuses the moveToThread pattern (started/completed/failed). import_template is
    file I/O plus python-pptx parsing, no widgets, so it is safe off-thread; the
    dialog dispatches the returned status dict on the GUI thread.

    Signals:
        started: emitted when run() begins.
        completed: emitted with the import_template result dict
            (status "ok" / "hard_stop" / "exists").
        failed: emitted with a user-facing error message. Never contains raw
            exception text or file content.
    """

    started = Signal()
    completed = Signal(object)   # import_template result dict
    failed = Signal(str)

    def __init__(self, pptx_path: str, user_root: str) -> None:
        super().__init__()
        self._pptx_path = pptx_path
        self._user_root = user_root

    def run(self) -> None:
        """Execute the import. Called via QThread.started.

        Emits started(), then either completed(result_dict) or failed(message).
        """
        self.started.emit()
        try:
            result = config.import_template(
                self._pptx_path, user_root=Path(self._user_root)
            )
        except ValueError as exc:
            logger.error("Template import rejected (bad file): %s", exc)
            self.failed.emit("That file is not a usable PowerPoint deck.")
            return
        except ManipulationError as exc:
            logger.error("Template import write failure: %s", exc)
            self.failed.emit(
                "Could not save the imported template. Check disk space and permissions."
            )
            return
        except Exception as exc:  # defensive net; matches the other workers
            logger.error("Unexpected error during template import: %s", exc)
            self.failed.emit("Something went wrong while importing. Please try again.")
            return

        self.completed.emit(result)
