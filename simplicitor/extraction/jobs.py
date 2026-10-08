"""Owned temporary jobs and ordinary Save As copying, independent of widgets."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from uuid import uuid4

from app.config.defaults import EXTRACTION_JOB_RETENTION_HOURS
from extraction.models import Candidate

_ROOT = "extraction-jobs"
_MARKER = ".simplicitor-job.json"
_JOB_NAME = re.compile(r"job-[0-9a-f]{32}\Z")


def same_path(first: Path, second: Path) -> bool:
    """Recognize normalized paths and existing aliases without opening content."""
    first, second = Path(first), Path(second)
    if os.path.normcase(str(first.resolve())) == os.path.normcase(str(second.resolve())):
        return True
    return first.exists() and second.exists() and first.samefile(second)


def create_job(app_data: Path) -> Path:
    """Create an owned job; each new run starts with no candidate or review."""
    root = Path(app_data) / _ROOT
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("Job storage must be an owned directory.")
    job = root / ("job-" + uuid4().hex)
    job.mkdir()
    try:
        (job / _MARKER).write_text(json.dumps({
            "job_id": job.name, "created_at": datetime.now(timezone.utc).isoformat(),
        }), encoding="utf-8")
    except OSError:
        (job / _MARKER).unlink(missing_ok=True)
        job.rmdir()
        raise
    return job


def save_candidate(candidate: Candidate, destination: Path, acknowledge_issues: bool) -> Path:
    """Copy after native Save As acceptance, including its overwrite confirmation.

    A cancelled dialog must not call this function. Failure preserves the saved
    review and the existing destination. No source file is ever a valid target.
    """
    destination = Path(destination)
    if any(same_path(destination, source) for source in candidate.source_paths):
        raise ValueError("Save As cannot replace a source file. Choose another destination.")
    if same_path(destination, candidate.path):
        raise ValueError("Choose a destination outside the temporary candidate file.")
    if candidate.issues and not acknowledge_issues:
        raise ValueError("Review acknowledgement is required for flagged or incomplete output.")
    temporary = None
    try:
        # mkstemp is closed before copy/replace, including on Windows.
        descriptor, name = tempfile.mkstemp(prefix=".simplicitor-", suffix=".tmp",
                                            dir=destination.parent)
        os.close(descriptor)
        temporary = Path(name)
        shutil.copyfile(candidate.path, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def _created_at(job_dir: Path) -> datetime:
    if (job_dir.parent.name != _ROOT or not _JOB_NAME.fullmatch(job_dir.name)
            or job_dir.is_symlink() or job_dir.parent.is_symlink()
            or not job_dir.is_dir() or (job_dir / _MARKER).is_symlink()):
        raise ValueError("Not an owned extraction job.")
    try:
        marker = json.loads((job_dir / _MARKER).read_text(encoding="utf-8"))
        created = datetime.fromisoformat(marker["created_at"])
        if marker["job_id"] != job_dir.name or created.tzinfo is None:
            raise ValueError
        return created.astimezone(timezone.utc)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Not an owned extraction job.") from exc


def discard_job(job_dir: Path) -> None:
    """Remove only an owned job, after its workers and workbook handles finish."""
    job_dir = Path(job_dir)
    if not job_dir.exists() and not job_dir.is_symlink():
        return
    _created_at(job_dir)
    shutil.rmtree(job_dir)


def cleanup_old_jobs(app_data: Path, now: datetime) -> int:
    """Remove owned jobs strictly older than retention; naive now means UTC."""
    root = Path(app_data) / _ROOT
    if not root.is_dir() or root.is_symlink():
        return 0
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(hours=EXTRACTION_JOB_RETENTION_HOURS)
    removed = 0
    for job in root.iterdir():
        try:
            created = _created_at(job)
        except ValueError:
            continue
        if created < cutoff:
            discard_job(job)
            removed += 1
    return removed
