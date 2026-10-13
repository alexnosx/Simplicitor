"""Save As for an edit candidate: record the destination, stage, read back, recheck, replace.

Runs in the edit worker, never on the GUI thread: recording the destination's fingerprint
reads the whole existing file.
"""
import os
from pathlib import Path
import tempfile

from editing.models import EditCandidate, EditError
from editing.package import sha256
from extraction.jobs import same_path

ORIGINAL_TARGET = "Your original cannot be overwritten. Choose a different name or folder."
WRONG_SUFFIX = "Save the edited document as a .docx file."
ORIGINAL_CHANGED = "The original changed after you opened it. Open it again before editing."
ORIGINAL_MISSING = "The original was moved, deleted or cannot be read. Open it again before editing."
DESTINATION_UNREADABLE = "The file you chose cannot be read. Choose where to save again."
DESTINATION_CHANGED = "The file you chose changed while saving. Choose where to save again."
WRITE_FAILED = "Could not save the document. Check that the folder is writable, then try again."


def suggested_name(original: Path) -> str:
    return f"{Path(original).stem} (edited).docx"


def destination_state(destination: Path) -> str | None:
    """None when absent, else the SHA-256 of the existing file. Raises OSError if unreadable."""
    try:
        return sha256(Path(destination).read_bytes())
    except FileNotFoundError:
        return None


def _stage(candidate: EditCandidate, folder: Path) -> Path:
    """Write the candidate to a temporary file in folder and read it back."""
    descriptor, name = tempfile.mkstemp(prefix=".simplicitor-", suffix=".tmp", dir=folder)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(candidate.data)
        if sha256(temporary.read_bytes()) != candidate.sha256:
            raise OSError("read-back mismatch")
    except OSError:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _commit_checks(candidate: EditCandidate, destination: Path, recorded: str | None) -> None:
    try:
        original = candidate.original_path.read_bytes()
    except OSError:
        raise EditError(ORIGINAL_MISSING, "original") from None
    if sha256(original) != candidate.original_sha256:
        raise EditError(ORIGINAL_CHANGED, "original")
    if same_path(destination, candidate.original_path):
        raise EditError(ORIGINAL_TARGET, "retry")
    try:
        current = destination_state(destination)
    except OSError:
        current = "unreadable"
    if current != recorded:
        raise EditError(DESTINATION_CHANGED, "destination")


def save_candidate(candidate: EditCandidate, destination: Path) -> Path:
    """Write the verified bytes to destination; on any failure leave an existing file unchanged.

    The destination's state is recorded first, as the save starts after Save As was accepted.
    outcome on EditError: "retry" (choose another destination), "destination" (Save As again,
    candidate kept), "original" (candidate discarded, open again) or "failed" (write error).
    """
    destination = Path(destination)
    if destination.suffix.lower() != ".docx":
        raise EditError(WRONG_SUFFIX, "retry")
    if same_path(destination, candidate.original_path):
        raise EditError(ORIGINAL_TARGET, "retry")
    try:
        recorded = destination_state(destination)
    except OSError:
        raise EditError(DESTINATION_UNREADABLE, "destination") from None
    try:
        temporary = _stage(candidate, destination.parent)
    except OSError:
        raise EditError(WRITE_FAILED) from None
    try:
        _commit_checks(candidate, destination, recorded)
        try:
            os.replace(temporary, destination)
        except OSError:
            raise EditError(WRITE_FAILED) from None
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
