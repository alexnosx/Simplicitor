"""Notice assembly and read-only payload validation; no installer or deletion tests."""
from pathlib import Path
import importlib.util
import json

import pytest


def test_build_qt_version_matches_vendored_notice_snapshot():
    root = Path(__file__).parents[1]
    version = json.loads((root / "resources/third_party/qt/sources.json").read_text())["qt_version"]
    assert f"PySide6=={version}" in (root / "requirements-build.txt").read_text().splitlines()


def test_notice_bundle_contains_runtime_versions_and_full_qt_terms(tmp_path):
    from scripts.build_third_party_notices import build_notices, validate_notices
    root = Path(__file__).parents[1]
    bundle = tmp_path / "third_party"
    build_notices(root, bundle)
    validate_notices(bundle)
    inventory = json.loads((bundle / "inventory.json").read_text())
    names = {p["name"].lower().replace('_', '-') for p in inventory["packages"]}
    assert {"pyside6", "shiboken6", "python-docx", "openpyxl", "pdfplumber",
            "pypdf", "requests", "pydantic", "lxml", "cryptography"} <= names
    assert (bundle / "qt/qtbase/LICENSES/LGPL-3.0-only.txt").read_text().lstrip().startswith(
        "GNU LESSER GENERAL PUBLIC LICENSE")
    assert "GNU GENERAL PUBLIC LICENSE" in (bundle / "qt/qtbase/LICENSES/GPL-3.0-only.txt").read_text()
    assert (bundle / "python-runtime/LICENSE.txt").stat().st_size > 1000
    assert (bundle / "nuitka-runtime/LICENSE-RUNTIME.txt").stat().st_size > 100
    assert all(p["version"] and p["license_files"] for p in inventory["packages"])


def test_missing_notice_payload_is_rejected_without_writing(tmp_path):
    from scripts.build_third_party_notices import validate_notices
    with pytest.raises(ValueError, match="notice"):
        validate_notices(tmp_path)
    assert not tuple(tmp_path.iterdir())


def test_build_packaging_checks_notice_payload_before_archiving(tmp_path, monkeypatch):
    # The archive writer must reject absent notices even if core resources exist.
    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location("task6_build", root / "build.py")
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    monkeypatch.setattr(build, "DIST_DIR", tmp_path)
    from tests.test_build_script import make_payload
    payload = tmp_path / "payload"
    make_payload(payload, notices=False)
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"test installer")
    with pytest.raises(ValueError, match="notice"):
        build.package_payload(payload, installer)
    assert not (tmp_path / "Simplicitor-portable.zip").exists()


def test_notice_payload_is_preserved_in_portable_archive(tmp_path, monkeypatch):
    from tests.test_build_script import build, make_payload
    from zipfile import ZipFile
    monkeypatch.setattr(build, "DIST_DIR", tmp_path)
    payload = tmp_path / "payload"
    make_payload(payload)
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"synthetic installer, never executed")
    build.package_payload(payload, installer)
    with ZipFile(tmp_path / "Simplicitor-portable.zip") as archive:
        for path in (payload / "third_party").rglob("*"):
            if path.is_file():
                assert archive.read("Simplicitor/" + path.relative_to(payload).as_posix()) == path.read_bytes()


def test_changed_notice_payload_is_rejected(tmp_path):
    from scripts.build_third_party_notices import build_notices, validate_notices
    build_notices(Path(__file__).parents[1], tmp_path / "third_party")
    (tmp_path / "third_party/python-runtime/LICENSE.txt").write_text("changed")
    with pytest.raises(ValueError, match="notice.*checksum"):
        validate_notices(tmp_path / "third_party")
