# tests/test_cli.py
"""CLI tests: argument guards and unified template-root resolution.

Migrated from simplicitor/tests/test_cli.py (stale tree, never collected by
pytest) and extended for the Settings.templates_dir unification.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from cli import _cmd_generate, _cmd_list_templates, _templates_root, _warn_if_legacy_root


def test_generate_requires_out_when_not_dry_run(capsys):
    """--out is required when not in dry-run mode; omitting it prints an error and returns 1."""
    result = _cmd_generate(argparse.Namespace(dry_run=False, out=None))
    assert result == 1
    assert "--out is required" in capsys.readouterr().err


# ── Unified template-root resolution ──────────────────────────────────────────

def test_templates_root_falls_back_to_documents_default(tmp_path, monkeypatch):
    """No settings.json: the documented default Documents\\Simplicitor\\Templates."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))  # empty config dir
    assert _templates_root() == Path.home() / "Documents" / "Simplicitor" / "Templates"


def test_templates_root_reads_persisted_settings(tmp_path, monkeypatch):
    """The CLI resolves the same settings.json the app writes."""
    cfg = tmp_path / "Roaming" / "Simplicitor"
    cfg.mkdir(parents=True)
    (cfg / "settings.json").write_text(
        json.dumps({"templates_dir": str(tmp_path / "MyTemplates")}), encoding="utf-8"
    )
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert _templates_root() == tmp_path / "MyTemplates"


def test_list_templates_uses_unified_root(tmp_path, monkeypatch, capsys):
    """list-templates scans the unified root: a user template there is listed."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))  # no legacy root
    root = tmp_path / "Templates"
    tdir = root / "my_upload"
    tdir.mkdir(parents=True)
    (tdir / "template.pptx").write_bytes(b"stub")  # listing checks existence only
    (tdir / "manifest.yaml").write_text("name: my_upload\n", encoding="utf-8")

    with patch("cli._templates_root", return_value=root):
        result = _cmd_list_templates(argparse.Namespace())

    assert result == 0
    out = capsys.readouterr().out
    assert "my_upload" in out
    # Seeded defaults appear alongside the upload, tagged as defaults.
    assert "business_pitch" in out


# ── Legacy-root migration notice ───────────────────────────────────────────────

def _make_stub_template(folder: Path) -> None:
    folder.mkdir(parents=True)
    (folder / "template.pptx").write_bytes(b"stub")
    (folder / "manifest.yaml").write_text("name: stub\n", encoding="utf-8")


def test_legacy_root_notice_names_both_paths(tmp_path, monkeypatch, capsys):
    """Templates left in the retired APPDATA root produce a notice naming both paths."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    legacy = tmp_path / "Roaming" / "Simplicitor" / "templates"
    _make_stub_template(legacy / "old_template")
    active = tmp_path / "Active"

    _warn_if_legacy_root(active)

    err = capsys.readouterr().err
    assert str(legacy) in err
    assert str(active) in err
    assert "retired" in err


def test_no_legacy_notice_when_root_absent(tmp_path, monkeypatch, capsys):
    """No legacy folder: no notice."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    _warn_if_legacy_root(tmp_path / "Active")
    assert capsys.readouterr().err == ""
