# tests/test_backup_service.py
import pytest
from pathlib import Path
from app.services.backup_service import BackupService


def test_backup_creates_file_in_backup_dir(tmp_path):
    src = tmp_path / "report.docx"
    src.write_bytes(b"fake docx content")
    backup_dir = tmp_path / "backups"
    result = BackupService().backup_if_needed(src, backup_dir)
    assert result.exists()
    assert result.name == "report_backup.docx"
    assert result.parent == backup_dir


def test_backup_creates_backup_dir_if_missing(tmp_path):
    src = tmp_path / "data.xlsx"
    src.write_bytes(b"fake xlsx")
    backup_dir = tmp_path / "nested" / "backups"
    BackupService().backup_if_needed(src, backup_dir)
    assert backup_dir.exists()


def test_backup_content_matches_source(tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("important content", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    result = BackupService().backup_if_needed(src, backup_dir)
    assert result.read_text(encoding="utf-8") == "important content"


def test_backup_not_overwritten_on_second_call(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("original", encoding="utf-8")
    backup_dir = tmp_path / "backups"
    # First backup
    result1 = BackupService().backup_if_needed(src, backup_dir)
    # Modify source and backup again — backup must NOT be overwritten
    src.write_text("modified", encoding="utf-8")
    result2 = BackupService().backup_if_needed(src, backup_dir)
    assert result1 == result2
    assert result2.read_text(encoding="utf-8") == "original"  # unchanged


def test_backup_returns_existing_backup_path(tmp_path):
    src = tmp_path / "doc.txt"
    src.write_text("hello")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    existing = backup_dir / "doc_backup.txt"
    existing.write_text("old backup")
    result = BackupService().backup_if_needed(src, backup_dir)
    assert result == existing
