# tests/test_gen_repo_map.py
"""Tests for scripts/gen_repo_map.py against a fixture mini-repo.

The fixture repo is materialized into tmp_path with git init so that
.gitignore handling is exercised through git itself, exactly as the
script uses it. A committed fixture directory cannot hold its own
.gitignore inside this repo (the outer git would apply it), so the
fixture is built at test time instead.
"""
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "gen_repo_map.py"

KNOWN_FUNCTION_SOURCE = '''\
"""Fixture module."""


def known_function(a: int, b: str = "x") -> bool:
    """Return True when the fixture works."""
    return True


class KnownClass:
    """A fixture class."""

    def method(self) -> None:
        pass
'''


def _make_repo(root: Path) -> None:
    """Build the fixture mini-repo: one package, one ignored file, one doc."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "module.py").write_text(KNOWN_FUNCTION_SOURCE, encoding="utf-8")
    (root / "ignored.txt").write_text("must not appear\n", encoding="utf-8")
    (root / "notes.md").write_text("# Notes\n\nOne line.\n", encoding="utf-8")


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
    )


def test_known_function_signature_appears(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "REPO_MAP.md").read_text(encoding="utf-8")
    assert "def known_function(a: int, b: str" in content
    assert "-> bool" in content
    assert "Return True when the fixture works." in content
    assert "class KnownClass" in content


def test_gitignored_file_excluded(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    content = (tmp_path / "REPO_MAP.md").read_text(encoding="utf-8")
    assert "ignored.txt" not in content
    assert "notes.md" in content


def test_manual_region_preserved_across_runs(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    assert _run(tmp_path).returncode == 0
    map_path = tmp_path / "REPO_MAP.md"
    first = map_path.read_text(encoding="utf-8")
    assert "TODO" in first, "fresh map must carry the TODO placeholder"

    custom = "Author note: the pkg package is the core.\nSecond line kept verbatim."
    edited = first.replace(
        first.split("<!-- MANUAL:BEGIN -->\n")[1].split("\n<!-- MANUAL:END -->")[0],
        custom,
    )
    map_path.write_text(edited, encoding="utf-8", newline="\n")

    assert _run(tmp_path).returncode == 0
    second = map_path.read_text(encoding="utf-8")
    assert custom in second


def test_consecutive_runs_byte_identical(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    assert _run(tmp_path).returncode == 0
    first_bytes = (tmp_path / "REPO_MAP.md").read_bytes()
    assert _run(tmp_path).returncode == 0
    second_bytes = (tmp_path / "REPO_MAP.md").read_bytes()
    assert first_bytes == second_bytes


def test_unparseable_python_fails_loudly(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    (tmp_path / "pkg" / "broken.py").write_text(
        "def broken(:\n", encoding="utf-8"
    )
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "broken.py" in result.stderr
    assert not (tmp_path / "REPO_MAP.md").exists(), "no partial output on failure"
