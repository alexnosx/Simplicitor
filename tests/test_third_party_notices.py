"""Notice assembly and read-only payload validation; no installer or deletion tests."""
from pathlib import Path
import importlib.util
import json

import pytest


@pytest.fixture
def missing_installed_license(tmp_path, monkeypatch):
    """Model the Mac wheels: package metadata exists but no installed license file."""
    from types import SimpleNamespace
    from scripts import build_third_party_notices as notices

    def use(name, version="6.11.2", entries=("package.dist-info/METADATA",)):
        for entry in entries:
            path = tmp_path / "installed" / entry
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic installed metadata")
        dist = SimpleNamespace(metadata={"Name": name}, version=version,
                               files=[Path(entry) for entry in entries],
                               locate_file=lambda entry: tmp_path / "installed" / entry)
        monkeypatch.setattr(notices, "_runtime_distributions", lambda root: [dist])
        return notices
    return use


@pytest.mark.parametrize("name", ["PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6"])
def test_mac_qt_without_installed_license_references_verified_vendored_texts(
    tmp_path, missing_installed_license, name
):
    notices = missing_installed_license(name)
    root = Path(__file__).parents[1]
    bundle = tmp_path / "third_party"
    notices.build_notices(root, bundle)
    inventory = json.loads((bundle / "inventory.json").read_text())
    expected = sorted("qt/" + entry["file"] for entry in json.loads(
        (root / "resources/third_party/qt/sources.json").read_text())["files"]
        if entry["file"].startswith("pyside-setup/LICENSES/"))
    assert expected
    assert inventory["packages"][0]["license_files"] == expected
    for path in expected:
        assert (bundle / path).read_bytes() == (root / "resources/third_party" / path).read_bytes()
    notices.validate_notices(bundle)
    (bundle / expected[0]).write_text("changed")
    with pytest.raises(ValueError, match="checksum"):
        notices.validate_notices(bundle)


def test_non_qt_without_installed_license_still_fails(tmp_path, missing_installed_license):
    notices = missing_installed_license("unrelated-package")
    with pytest.raises(ValueError, match="Missing license texts.*unrelated-package"):
        notices.build_notices(Path(__file__).parents[1], tmp_path / "third_party")


def test_qt_fallback_cannot_hide_invalid_installed_notice_path(tmp_path, missing_installed_license):
    notices = missing_installed_license("PySide6", entries=("../LICENSE.txt",))
    with pytest.raises(ValueError, match="Unexpected runtime notice path"):
        notices.build_notices(Path(__file__).parents[1], tmp_path / "third_party")


def test_qt_fallback_requires_matching_package_version(tmp_path, missing_installed_license):
    notices = missing_installed_license("shiboken6", version="6.10.0")
    with pytest.raises(ValueError, match="snapshot version"):
        notices.build_notices(Path(__file__).parents[1], tmp_path / "third_party")


@pytest.mark.parametrize("location", ["base", "stdlib"])
def test_python_license_resolver_uses_nonempty_installed_file(tmp_path, monkeypatch, location):
    from scripts import build_third_party_notices as notices
    base, stdlib = tmp_path / "base", tmp_path / "stdlib"
    base.mkdir(); stdlib.mkdir()
    (base / "LICENSE.txt").write_bytes(b"base terms" if location == "base" else b"")
    (stdlib / "LICENSE.txt").write_bytes(b"stdlib terms")
    monkeypatch.setattr(notices.sys, "base_prefix", str(base))
    monkeypatch.setattr(notices.sysconfig, "get_path", lambda key: str(stdlib))
    assert notices.python_license_path() == (base if location == "base" else stdlib) / "LICENSE.txt"


def test_python_license_resolver_rejects_missing_or_empty_files(tmp_path, monkeypatch):
    from scripts import build_third_party_notices as notices
    (tmp_path / "LICENSE.txt").write_bytes(b"")
    monkeypatch.setattr(notices.sys, "base_prefix", str(tmp_path))
    monkeypatch.setattr(notices.sysconfig, "get_path", lambda key: str(tmp_path / "missing"))
    with pytest.raises(ValueError, match="Python license"):
        notices.python_license_path()


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
        build.package_payload(payload, (installer,))
    assert not (tmp_path / "Simplicitor-portable.zip").exists()


def test_notice_payload_is_preserved_in_portable_archive(tmp_path, monkeypatch):
    from tests.test_build_script import build, make_payload
    from zipfile import ZipFile
    monkeypatch.setattr(build, "DIST_DIR", tmp_path)
    payload = tmp_path / "payload"
    make_payload(payload)
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"synthetic installer, never executed")
    build.package_payload(payload, (installer,))
    with ZipFile(tmp_path / "Simplicitor-portable.zip") as archive:
        assert archive.read("Simplicitor/LICENSE") == (build.ROOT / "LICENSE").read_bytes()
        for path in (payload / "third_party").rglob("*"):
            if path.is_file():
                assert archive.read("Simplicitor/" + path.relative_to(payload).as_posix()) == path.read_bytes()


def test_changed_notice_payload_is_rejected(tmp_path):
    from scripts.build_third_party_notices import build_notices, validate_notices
    build_notices(Path(__file__).parents[1], tmp_path / "third_party")
    (tmp_path / "third_party/python-runtime/LICENSE.txt").write_text("changed")
    with pytest.raises(ValueError, match="notice.*checksum"):
        validate_notices(tmp_path / "third_party")
