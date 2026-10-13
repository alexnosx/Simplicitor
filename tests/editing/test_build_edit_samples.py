"""The Word-check sample builder uses the production route and refuses unsafe folders."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_edit_samples.py"
spec = importlib.util.spec_from_file_location("build_edit_samples", SCRIPT)
build_edit_samples = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_edit_samples)


def test_builds_every_sample_into_an_empty_folder(tmp_path, monkeypatch):
    # The local test policy keeps pytest's temporary folders inside the repository's .venv,
    # which the builder rightly refuses; treat a sibling folder as the repository here.
    monkeypatch.setattr(build_edit_samples, "ROOT", tmp_path / "repository")
    out = tmp_path / "samples"
    assert build_edit_samples.main(out) == 0
    assert sorted(p.stem for p in out.iterdir()) == sorted(s[0] for s in build_edit_samples.SAMPLES)


def test_refuses_the_repository_and_a_non_empty_folder(tmp_path):
    assert build_edit_samples.main(build_edit_samples.ROOT / "docs") == 2
    (tmp_path / "keep.txt").write_text("x")
    assert build_edit_samples.main(tmp_path) == 2
