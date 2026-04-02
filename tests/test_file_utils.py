# tests/test_file_utils.py
from pathlib import Path
import pytest
from app.utils.file_utils import sanitize_filename, ensure_dir


def test_sanitize_removes_special_chars() -> None:
    assert sanitize_filename("Hello, World!") == "Hello_World"


def test_sanitize_replaces_spaces_with_underscores() -> None:
    assert sanitize_filename("my document name") == "my_document_name"


def test_sanitize_truncates_to_max_length() -> None:
    result = sanitize_filename("a" * 100, max_length=40)
    assert len(result) <= 40


def test_sanitize_empty_string_returns_document() -> None:
    assert sanitize_filename("") == "document"


def test_sanitize_only_special_chars_returns_document() -> None:
    assert sanitize_filename("!@#$%^&*()") == "document"


def test_sanitize_preserves_alphanumeric() -> None:
    result = sanitize_filename("report2024")
    assert result == "report2024"


def test_ensure_dir_creates_nested_dirs(tmp_path: Path) -> None:
    target = tmp_path / "a" / "b" / "c"
    result = ensure_dir(target)
    assert result.is_dir()
    assert result == target


def test_ensure_dir_accepts_string(tmp_path: Path) -> None:
    target = str(tmp_path / "new_dir")
    result = ensure_dir(target)
    assert result.is_dir()


def test_ensure_dir_idempotent(tmp_path: Path) -> None:
    ensure_dir(tmp_path / "existing")
    ensure_dir(tmp_path / "existing")  # must not raise
