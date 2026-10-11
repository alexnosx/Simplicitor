"""Build command and real archive/inventory contracts, without recompiling in pytest."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

SPEC = importlib.util.spec_from_file_location("simplicitor_build", Path(__file__).parents[1] / "build.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


@pytest.fixture
def payload(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "DIST_DIR", tmp_path / "dist")
    monkeypatch.setattr(build, "FRAGMENT", tmp_path / "msi" / "payload.wxs")
    monkeypatch.setattr(build, "ICON", tmp_path / "icon.ico")
    build.ICON.write_bytes(b"test icon")
    monkeypatch.setenv("NUITKA_CACHE_DIR", str(tmp_path / "cache"))
    return tmp_path / "dist" / "standalone" / "main.dist"


def make_payload(payload, *, notices=True, include_license=True):
    files = {
        "Simplicitor.exe": b"compiled application",
        "prompts/system_word.txt": b"word prompt",
        "prompts/system_excel.txt": b"excel prompt",
        "prompts/system_pptx.txt": b"pptx prompt",
        "templates/pptx_default.pptx": b"default template",
        "templates_engine/builtin/business_pitch/manifest.yaml": b"pitch",
        "templates_engine/builtin/business_pitch/template.pptx": b"pitch pptx",
        "templates_engine/builtin/technical_overview/manifest.yaml": b"technical",
        "templates_engine/builtin/technical_overview/template.pptx": b"technical pptx",
        "assets/icons/simplicitor.ico": b"icon",
        "PySide6/Qt6Core.dll": b"runtime",
    }
    for name, data in files.items():
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if notices:
        build.build_notices(build.ROOT, payload / "third_party")
    if include_license:
        (payload / "LICENSE").write_bytes((build.ROOT / "LICENSE").read_bytes())
    return files


def test_build_flags_have_no_nsis_installer():
    assert not any(flag.startswith("--windows-installer") or flag == "--windows-create-installer"
                   for flag in build.NUITKA_FLAGS)



def test_product_version_is_210():
    assert build.PRODUCT_VERSION == "2.1.0"
    assert "--windows-product-version=2.1.0.0" in build.NUITKA_FLAGS


def test_build_produces_matching_portable_payload_and_msi(payload, monkeypatch):
    captured = []
    msi = build.DIST_DIR / "Simplicitor-2.1.0.msi"

    def run(command, *, cwd):
        captured.append((command, cwd))
        if command[:3] == ["dotnet", "wix", "build"]:
            msi.write_bytes(b"MSI package")
        elif command[0] != "dotnet":
            make_payload(payload)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build.shutil, "which", lambda name: "dotnet.exe")
    monkeypatch.setattr(build.subprocess, "run", run)
    assert build.main() == 0
    nuitka, cwd = captured[0]
    assert "--mode=standalone" in nuitka and cwd == build.SIMPLICITOR_DIR
    assert captured[1][0] == ["dotnet", "tool", "restore"]
    wix = captured[2][0]
    assert wix[:3] == ["dotnet", "wix", "build"]
    assert str(build.WIX_SOURCE) in wix and str(build.FRAGMENT) in wix
    assert "ProductVersion=2.1.0" in wix and f"payload={payload}" in wix
    assert build.FRAGMENT.read_text(encoding="utf-8") == build.payload_fragment(payload)
    manifest = json.loads((build.DIST_DIR / "SHA256SUMS.json").read_text())
    assert set(manifest["artifacts"]) == {"Simplicitor-2.1.0.msi", "Simplicitor-portable.zip"}
    for name in manifest["artifacts"]:
        assert manifest["artifacts"][name] == hashlib.sha256((build.DIST_DIR / name).read_bytes()).hexdigest()
    assert not (build.DIST_DIR / "Simplicitor-setup.exe").exists()


def _payload_only(payload):
    def run(command, *, cwd):
        if command[0] != "dotnet":
            make_payload(payload)
        return SimpleNamespace(returncode=0)
    return run


def test_ci_build_fails_without_dotnet(payload, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(build.shutil, "which", lambda name: None)
    monkeypatch.setattr(build.subprocess, "run", _payload_only(payload))
    assert build.main() != 0
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_local_build_without_dotnet_skips_msi_only(payload, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(build.shutil, "which", lambda name: None)
    monkeypatch.setattr(build.subprocess, "run", _payload_only(payload))
    assert build.main() == 0
    manifest = json.loads((build.DIST_DIR / "SHA256SUMS.json").read_text())
    assert set(manifest["artifacts"]) == {"Simplicitor-portable.zip"}


@pytest.mark.parametrize("missing", ["Simplicitor.exe", "prompts/system_word.txt",
                                    "templates/pptx_default.pptx",
                                    "templates_engine/builtin/business_pitch/template.pptx",
                                    "assets/icons/simplicitor.ico", "msi"])
def test_incomplete_build_fails_without_a_portable_archive(payload, monkeypatch, missing):
    monkeypatch.setattr(build.shutil, "which", lambda name: "dotnet.exe")
    def incomplete(command, *, cwd):
        if command[:3] == ["dotnet", "wix", "build"]:
            if missing != "msi":
                (build.DIST_DIR / "Simplicitor-2.1.0.msi").write_bytes(b"msi")
        elif command[0] != "dotnet":
            make_payload(payload)
            if missing != "msi":
                (payload / missing).unlink()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(build.subprocess, "run", incomplete)
    assert build.main() != 0
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_compiler_failure_is_propagated(payload, monkeypatch):
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=7))
    assert build.main() == 7
    assert not (build.DIST_DIR / "Simplicitor-portable.zip").exists()


def test_missing_icon_fails_before_compilation(payload, monkeypatch):
    build.ICON.unlink()
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: pytest.fail("must not compile"))
    assert build.main() != 0
