"""Save As: refusals, the recorded destination, commit-point checks and clean failures."""
import os

import pytest

from editing import save
from editing.models import EditError, Proposal, ProposedParagraph
from editing.package import open_document
from editing.patch import build_candidate
from tests.editing.docx_builder import build_docx, p


@pytest.fixture
def candidate(tmp_path):
    original = tmp_path / "terms.docx"
    original.write_bytes(build_docx(p("Pay in 30 days.")))
    opened = open_document(original)
    return build_candidate(opened, 0, 0, Proposal((ProposedParagraph(0, "Pay in 45 days."),)))


def _leftovers(folder):
    return [name for name in os.listdir(folder) if name.startswith(".simplicitor-")]


def _interleave(monkeypatch, change):
    """Run `change` after the destination was recorded and staged, before the commit checks."""
    real = save._commit_checks

    def interleaved(candidate, destination, recorded):
        change(candidate, destination)
        return real(candidate, destination, recorded)

    monkeypatch.setattr(save, "_commit_checks", interleaved)


def test_suggested_name():
    assert save.suggested_name("C:/docs/terms.docx") == "terms (edited).docx"


def test_saves_new_file_and_leaves_original(tmp_path, candidate):
    before = candidate.original_path.read_bytes()
    target = tmp_path / save.suggested_name(candidate.original_path)
    assert save.save_candidate(candidate, target) == target
    assert target.read_bytes() == candidate.data
    assert candidate.original_path.read_bytes() == before
    assert _leftovers(tmp_path) == []


def test_refuses_original_and_wrong_suffix(tmp_path, candidate):
    with pytest.raises(EditError, match="original cannot be overwritten") as caught:
        save.save_candidate(candidate, candidate.original_path)
    assert caught.value.outcome == "retry"
    with pytest.raises(EditError, match=r"\.docx file"):
        save.save_candidate(candidate, tmp_path / "terms.txt")


def test_replaces_an_existing_destination_that_stayed_unchanged(tmp_path, candidate):
    target = tmp_path / "copy.docx"
    target.write_bytes(b"older")
    save.save_candidate(candidate, target)
    assert target.read_bytes() == candidate.data


@pytest.mark.parametrize("change, outcome", [
    (lambda c, t: c.original_path.write_bytes(b"edited elsewhere"), "original"),
    (lambda c, t: c.original_path.unlink(), "original"),
    (lambda c, t: t.write_bytes(b"appeared"), "destination"),
])
def test_commit_point_changes_save_nothing(tmp_path, candidate, monkeypatch, change, outcome):
    target = tmp_path / "out.docx"
    _interleave(monkeypatch, change)
    with pytest.raises(EditError) as caught:
        save.save_candidate(candidate, target)
    assert caught.value.outcome == outcome
    assert (target.read_bytes() if target.exists() else None) in (None, b"appeared")
    assert _leftovers(tmp_path) == []


def test_same_size_same_time_content_change_is_detected(tmp_path, candidate, monkeypatch):
    target = tmp_path / "copy.docx"
    target.write_bytes(b"Value 30")
    stat = target.stat()

    def swap(c, t):
        t.write_bytes(b"Value 45")
        os.utime(t, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    _interleave(monkeypatch, swap)
    with pytest.raises(EditError, match="changed while saving") as caught:
        save.save_candidate(candidate, target)
    assert caught.value.outcome == "destination" and target.read_bytes() == b"Value 45"
    assert _leftovers(tmp_path) == []


def test_unreadable_destination_is_reported_before_writing(tmp_path, candidate, monkeypatch):
    target = tmp_path / "copy.docx"
    target.write_bytes(b"keep me")
    monkeypatch.setattr(save, "destination_state", lambda d: (_ for _ in ()).throw(PermissionError()))
    with pytest.raises(EditError, match="cannot be read") as caught:
        save.save_candidate(candidate, target)
    assert caught.value.outcome == "destination"
    assert target.read_bytes() == b"keep me" and _leftovers(tmp_path) == []


def test_write_failure_and_read_back_mismatch_leave_destination(tmp_path, candidate, monkeypatch):
    target = tmp_path / "copy.docx"
    target.write_bytes(b"keep me")
    real = save.sha256
    monkeypatch.setattr(save, "sha256", lambda data: "mismatch" if data == candidate.data else real(data))
    with pytest.raises(EditError, match="Could not save"):
        save.save_candidate(candidate, target)
    assert target.read_bytes() == b"keep me" and _leftovers(tmp_path) == []
    monkeypatch.undo()
    monkeypatch.setattr(save.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("locked")))
    with pytest.raises(EditError, match="Could not save"):
        save.save_candidate(candidate, target)
    assert target.read_bytes() == b"keep me" and _leftovers(tmp_path) == []
