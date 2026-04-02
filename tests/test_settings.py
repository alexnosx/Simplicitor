# tests/test_settings.py
from pathlib import Path
import pytest
from app.config.settings import Settings


def test_default_paths_contain_simplicitor(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert "Simplicitor" in s.generated_dir
    assert "Simplicitor" in s.uploads_dir
    assert "Simplicitor" in s.backups_dir
    assert "Simplicitor" in s.logs_dir


def test_paths_are_strings(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert isinstance(s.generated_dir, str)
    assert isinstance(s.uploads_dir, str)
    assert isinstance(s.backups_dir, str)
    assert isinstance(s.logs_dir, str)


def test_save_and_reload_persists_value(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s2 = Settings(tmp_path)
    assert s2.generated_dir == "/custom/generated"


def test_reload_preserves_other_keys(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    original_uploads = s.uploads_dir
    s.set("generated_dir", "/custom/generated")
    s.save()
    s2 = Settings(tmp_path)
    assert s2.uploads_dir == original_uploads


def test_reset_to_defaults_restores_paths(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s.reset_to_defaults()
    assert "Simplicitor" in s.generated_dir
    assert s.generated_dir != "/custom/generated"


def test_reset_persists_to_disk(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    s.set("generated_dir", "/custom/generated")
    s.save()
    s.reset_to_defaults()
    s2 = Settings(tmp_path)
    assert s2.generated_dir != "/custom/generated"


def test_handles_corrupt_json_gracefully(tmp_path: Path) -> None:
    (tmp_path / "settings.json").write_text("{invalid json}", encoding="utf-8")
    s = Settings(tmp_path)  # must not raise
    assert "Simplicitor" in s.generated_dir


def test_get_unknown_key_returns_default(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert s.get("nonexistent_key", "fallback") == "fallback"


def test_get_returns_none_when_no_default_given(tmp_path: Path) -> None:
    s = Settings(tmp_path)
    assert s.get("nonexistent_key") is None
