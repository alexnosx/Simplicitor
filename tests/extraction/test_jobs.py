"""Real filesystem Save As, failures, ownership, and retention boundaries."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from extraction.jobs import cleanup_old_jobs, create_job, discard_job, save_candidate
from extraction.models import Candidate, Issue


def candidate_in(tmp_path, *, issues=()):
    job = create_job(tmp_path / "app")
    path = job / "candidate.xlsx"
    path.write_bytes(b"candidate bytes")
    sources = (tmp_path / "one.docx", tmp_path / "two.pdf")
    for source in sources:
        source.write_bytes(b"source bytes")
    return Candidate(job.name, path, sources, issues)


def test_owned_unique_jobs_and_normal_close_cleanup(tmp_path):
    first, second = create_job(tmp_path), create_job(tmp_path)
    assert first != second and first.parent == second.parent
    (first / "candidate.xlsx").write_bytes(b"closed workbook")
    discard_job(first)
    assert not first.exists() and second.exists()
    discard_job(first)  # close can be repeated after cleanup


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("variant", ["direct", "dots", "case"])
def test_save_as_refuses_source_path(tmp_path, index, variant):
    candidate = candidate_in(tmp_path)
    source = candidate.source_paths[index]
    destination = {"direct": source, "dots": source.parent / "sub" / ".." / source.name,
                   "case": Path(str(source).upper())}[variant]
    with pytest.raises(ValueError, match="source"):
        save_candidate(candidate, destination, False)
    assert source.read_bytes() == b"source bytes"
    assert candidate.path.read_bytes() == b"candidate bytes"


def test_save_as_new_and_confirmed_overwrite(tmp_path):
    candidate = candidate_in(tmp_path)
    destination = tmp_path / "chosen.xlsx"
    assert save_candidate(candidate, destination, False) == destination
    assert destination.read_bytes() == b"candidate bytes"
    destination.write_bytes(b"previous user output")
    assert save_candidate(candidate, destination, False) == destination
    assert destination.read_bytes() == b"candidate bytes"
    assert candidate.path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_flagged_output_requires_acknowledgement(tmp_path):
    candidate = candidate_in(tmp_path, issues=(Issue("missing_value", "one", "", "Review."),))
    destination = tmp_path / "chosen.xlsx"
    with pytest.raises(ValueError, match="acknowledg"):
        save_candidate(candidate, destination, False)
    assert not destination.exists()
    save_candidate(candidate, destination, True)
    assert destination.exists()


@pytest.mark.parametrize("filename", ["output", "output.csv", "output.xls", "output.xlsx.txt"])
@pytest.mark.parametrize("existing", [False, True])
def test_save_as_refuses_non_xlsx_suffix_without_writing(tmp_path, filename, existing):
    candidate = candidate_in(tmp_path)
    destination = tmp_path / filename
    if existing:
        destination.write_bytes(b"previous bytes")
    with pytest.raises(ValueError, match=".xlsx"):
        save_candidate(candidate, destination, False)
    if existing:
        assert destination.read_bytes() == b"previous bytes"
    else:
        assert not destination.exists()
    assert candidate.path.read_bytes() == b"candidate bytes"
    assert not list(tmp_path.glob("*.tmp"))


def test_save_as_accepts_case_insensitive_xlsx_suffix(tmp_path):
    candidate = candidate_in(tmp_path)
    destination = tmp_path / "output.XlSx"
    save_candidate(candidate, destination, False)
    assert destination.read_bytes() == b"candidate bytes"


@pytest.mark.parametrize("operation", ["copy", "replace"])
@pytest.mark.parametrize("existing", [False, True])
def test_failed_copy_or_rename_keeps_destination_and_review(tmp_path, monkeypatch, operation, existing):
    from extraction import jobs
    candidate = candidate_in(tmp_path)
    destination = tmp_path / "chosen.xlsx"
    if existing:
        destination.write_bytes(b"previous output")
    def fail_copy(source, target):
        Path(target).write_bytes(b"partial")
        raise OSError("disk full")
    def fail_replace(source, target):
        assert Path(source).parent == destination.parent
        assert Path(source).read_bytes() == b"candidate bytes"
        raise PermissionError("destination open")
    if operation == "copy":
        monkeypatch.setattr(jobs.shutil, "copyfile", fail_copy)
    else:
        monkeypatch.setattr(jobs.os, "replace", fail_replace)
    with pytest.raises(OSError):
        save_candidate(candidate, destination, False)
    assert destination.read_bytes() == b"previous output" if existing else not destination.exists()
    assert candidate.path.read_bytes() == b"candidate bytes"
    assert all(p.read_bytes() == b"source bytes" for p in candidate.source_paths)
    assert not list(destination.parent.glob("*.tmp"))


def test_cleanup_only_owned_jobs_strictly_older_than_24_hours(tmp_path):
    now = datetime.now(timezone.utc)
    old, boundary, fresh = (create_job(tmp_path) for _ in range(3))
    for job, age in ((old, timedelta(hours=24, seconds=1)),
                     (boundary, timedelta(hours=24)), (fresh, timedelta(hours=23))):
        marker = job / ".simplicitor-job.json"
        data = json.loads(marker.read_text())
        data["created_at"] = (now - age).isoformat()
        marker.write_text(json.dumps(data))
    unrelated = old.parent / ("job-" + "0" * 32)
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("unrelated")
    assert cleanup_old_jobs(tmp_path, now) == 1
    assert not old.exists() and boundary.exists() and fresh.exists() and unrelated.exists()


def test_unowned_folder_refused_and_unrelated_files_untouched(tmp_path):
    unrelated = tmp_path / "extraction-jobs" / "job-other"
    unrelated.mkdir(parents=True)
    keep = unrelated / "keep.txt"
    keep.write_text("keep")
    with pytest.raises(ValueError, match="owned"):
        discard_job(unrelated)
    assert cleanup_old_jobs(tmp_path, datetime.now(timezone.utc)) == 0
    assert keep.read_text() == "keep"


def test_failed_rerun_cannot_save_stale_candidate(tmp_path):
    candidate = candidate_in(tmp_path)
    discard_job(candidate.path.parent)
    with pytest.raises(OSError):
        save_candidate(candidate, tmp_path / "output.xlsx", False)
    assert not (tmp_path / "output.xlsx").exists()


def test_save_as_refuses_existing_source_alias(tmp_path):
    import os
    candidate = candidate_in(tmp_path)
    alias = tmp_path / "alias.xlsx"
    os.link(candidate.source_paths[0], alias)
    with pytest.raises(ValueError, match="source"):
        save_candidate(candidate, alias, False)
    assert alias.read_bytes() == b"source bytes"


@pytest.mark.parametrize("marker", ["not json", "[]", '{"job_id": "wrong"}'])
def test_cleanup_preserves_invalid_ownership_markers(tmp_path, marker):
    job = create_job(tmp_path)
    (job / ".simplicitor-job.json").write_text(marker)
    with pytest.raises(ValueError, match="owned"):
        discard_job(job)
    assert cleanup_old_jobs(tmp_path, datetime.now(timezone.utc) + timedelta(days=3)) == 0
    assert job.exists()


def test_failed_job_creation_removes_its_partial_marker(tmp_path, monkeypatch):
    original = Path.write_text
    def fail_marker(path, content, **kwargs):
        original(path, "partial", **kwargs)
        raise OSError("disk full")
    monkeypatch.setattr(Path, "write_text", fail_marker)
    with pytest.raises(OSError, match="disk full"):
        create_job(tmp_path)
    assert not list((tmp_path / "extraction-jobs").iterdir())
