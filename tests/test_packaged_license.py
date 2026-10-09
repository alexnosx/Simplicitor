"""Application license packaging contracts; no installer or deletion execution."""
import pytest

from tests.test_build_script import build, make_payload


def test_license_is_included_in_the_nuitka_payload():
    assert f"--include-data-files={build.ROOT / 'LICENSE'}=LICENSE" in build.NUITKA_FLAGS


def test_missing_application_license_fails_before_archiving(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "DIST_DIR", tmp_path)
    payload = tmp_path / "payload"
    make_payload(payload, include_license=False)
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"synthetic artifact, never executed")
    with pytest.raises(ValueError, match="LICENSE"):
        build.package_payload(payload, installer)
    assert not (tmp_path / "Simplicitor-portable.zip").exists()


@pytest.mark.parametrize("wrong", [b"", b"stale noncommercial license"])
def test_empty_or_stale_application_license_fails_before_archiving(tmp_path, monkeypatch, wrong):
    monkeypatch.setattr(build, "DIST_DIR", tmp_path)
    payload = tmp_path / "payload"
    make_payload(payload)
    (payload / "LICENSE").write_bytes(wrong)
    installer = tmp_path / "setup.exe"
    installer.write_bytes(b"synthetic artifact, never executed")
    with pytest.raises(ValueError, match="LICENSE"):
        build.package_payload(payload, installer)
    assert not (tmp_path / "Simplicitor-portable.zip").exists()
