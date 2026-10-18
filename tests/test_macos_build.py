"""Mac command and bundle contracts. All external commands are mocked."""
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

from PIL import Image
import pytest


@pytest.fixture
def mac(tmp_path, monkeypatch):
    build = importlib.import_module("build_macos")
    monkeypatch.setattr(build, "DIST_DIR", tmp_path / "dist" / "macos-pilot")
    monkeypatch.setattr(build, "WORK_DIR", tmp_path / ".nuitka" / "macos-pilot")
    monkeypatch.setattr(build.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(build.platform, "machine", lambda: "arm64")
    return build


def test_nuitka_command_is_pure_and_uses_existing_data_and_free_signing(mac, tmp_path, monkeypatch):
    monkeypatch.setattr(mac.sys, "executable", "C:/hostedtoolcache/windows/Python/python.exe")
    def forbidden(*args, **kwargs):
        pytest.fail("command construction must not write files or run tools")
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(mac.subprocess, "run", forbidden)
    command = mac.nuitka_command(tmp_path / "compiler")
    assert command[:3] == [mac.sys.executable, "-m", "nuitka"]
    for flag in ("--mode=app", "--python-flag=isolated", "--enable-plugin=pyside6",
                 "--macos-app-name=Simplicitor", "--output-folder-name=Simplicitor",
                 "--output-filename=Simplicitor", "--macos-target-arch=arm64",
                 "--macos-signed-app-name=com.simplicitor.pilot",
                 "--macos-sign-identity=ad-hoc", "--macos-app-macos-min-version=14.0",
                 "--macos-app-console-mode=disable", "--macos-app-mode=gui", "--jobs=2",
                 f"--macos-app-version={mac.PRODUCT_VERSION}",
                 f"--output-dir={tmp_path / 'compiler'}",
                 "--include-data-dir=prompts=prompts", "--include-data-dir=templates=templates",
                 "--include-data-dir=templates_engine/builtin=templates_engine/builtin",
                 f"--include-data-dir={mac.ROOT / 'assets'}=assets",
                 f"--include-data-files={mac.ROOT / 'LICENSE'}=LICENSE",
                 f"--include-data-dir={mac.WORK_DIR / 'third_party'}=third_party",
                 f"--macos-app-icon={mac.WORK_DIR / 'simplicitor.png'}"):
        assert flag in command
    assert command[-1] == "main.py"
    assert not any(any(term in flag.partition("=")[0].lower() for term in (
        "windows", "wix", "notar", "entitlement", "protected-resource", "download", "ollama"
    )) for flag in command if flag.startswith("--"))
    assert mac.PRODUCT_VERSION == __import__("app.version", fromlist=["__version__"]).__version__


@pytest.mark.parametrize("system,arch", [("Windows", "arm64"), ("Linux", "arm64"),
                                         ("Darwin", "x86_64")])
def test_unsupported_host_refuses_before_creating_output_or_tools(mac, monkeypatch, system, arch):
    monkeypatch.setattr(mac.platform, "system", lambda: system)
    monkeypatch.setattr(mac.platform, "machine", lambda: arch)
    monkeypatch.setattr(mac.subprocess, "run", lambda *a, **k: pytest.fail("no external tools"))
    assert mac.main() == 1
    assert not mac.DIST_DIR.exists() and not mac.WORK_DIR.exists()


def test_icon_is_the_actual_largest_ico_image_without_changing_windows_artwork(mac):
    before = (mac.ROOT / "assets/icons/simplicitor.ico").read_bytes()
    mac.WORK_DIR.mkdir(parents=True)
    icon = mac.write_icon()
    with Image.open(mac.ROOT / "assets/icons/simplicitor.ico") as original, Image.open(icon) as png:
        size = max(original.ico.sizes(), key=lambda s: s[0] * s[1])
        expected = original.ico.getimage(size).convert("RGBA")
        assert png.size == size
        assert png.convert("RGBA").tobytes() == expected.tobytes()
    assert (mac.ROOT / "assets/icons/simplicitor.ico").read_bytes() == before


@pytest.fixture
def simulated_build(mac, monkeypatch):
    calls = []
    mode = {"failure": None, "missing": None}
    signed = {}

    def snapshot(app):
        return {p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in app.rglob("*") if p.is_file()}

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[:3] == [mac.sys.executable, "-m", "nuitka"]:
            assert (mac.WORK_DIR / "simplicitor.png").is_file()
            mac.validate_notices(mac.WORK_DIR / "third_party")
            if mode["failure"] == "compiler":
                raise subprocess.CalledProcessError(7, command)
            if mode["failure"] == "no_bundle":
                return SimpleNamespace(returncode=0)
            app = mac.WORK_DIR / "Simplicitor.app"
            payload = app / "Contents/MacOS"
            payload.mkdir(parents=True)
            (payload / "Simplicitor").write_bytes(b"synthetic executable, never run")
            for relative in ("prompts", "templates", "templates_engine/builtin"):
                shutil.copytree(mac.ROOT / "simplicitor" / relative, payload / relative)
            shutil.copytree(mac.ROOT / "assets", payload / "assets")
            shutil.copyfile(mac.ROOT / "LICENSE", payload / "LICENSE")
            shutil.copytree(mac.WORK_DIR / "third_party", payload / "third_party")
            if mode["missing"]:
                (payload / mode["missing"]).unlink()
            signed.update(snapshot(app))  # Simulates Nuitka's final signing boundary.
        elif command[0] == "ditto":
            app = Path(command[-2])
            assert snapshot(app) == signed, "signed app bytes changed after compilation"
            if mode["failure"] == "archive":
                raise subprocess.CalledProcessError(8, command)
            Path(command[-1]).write_bytes(b"mock ditto ZIP; never extracted or run")
        else:
            pytest.fail(f"unexpected external command: {command[0]}")
        return SimpleNamespace(returncode=0)

    def git(command, **kwargs):
        assert command == ["git", "rev-parse", "HEAD"]
        assert kwargs["cwd"] == mac.ROOT
        return "a" * 40 + "\n"

    monkeypatch.setattr(mac.subprocess, "run", run)
    monkeypatch.setattr(mac.subprocess, "check_output", git)
    return calls, mode


def test_build_stages_data_before_signing_then_archives_without_mutating_bundle(mac, simulated_build):
    calls, _ = simulated_build
    zip_path, manifest_path = mac.build()
    app = mac.DIST_DIR / "Simplicitor.app"
    assert zip_path.name == "Simplicitor-macos-arm64-pilot.zip"
    assert manifest_path.name == "SHA256SUMS-macos-pilot.json"
    assert len(calls) == 2  # Signing is Nuitka's final step, never a post-build tool call.
    assert calls[0][1]["cwd"] == mac.ROOT / "simplicitor"
    assert calls[0][1]["env"]["MACOSX_DEPLOYMENT_TARGET"] == "14.0"
    assert calls[1][0] == ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                            str(app), str(zip_path)]
    assert calls[0][1]["check"] and calls[1][1]["check"]
    manifest = json.loads(manifest_path.read_text())
    assert manifest["pilot"] is True and manifest["notarized"] is False
    assert manifest["version"] == mac.PRODUCT_VERSION
    assert manifest["source_commit"] == "a" * 40
    assert manifest["architecture"] == "arm64" and manifest["minimum_macos"] == "14.0"
    assert manifest["signing"] == "ad-hoc"
    assert set(manifest["runtime_versions"]) == {"python", "qt", "nuitka"}
    assert manifest["artifacts"] == {zip_path.name: hashlib.sha256(zip_path.read_bytes()).hexdigest()}
    assert manifest["bundle_layout"]["executable"] == "Contents/MacOS/Simplicitor"
    assert manifest["bundle_layout"]["data"] == "Contents/MacOS"
    assert manifest["bundle"]["symlinks"] == {}
    for name, digest in manifest["bundle"]["files"].items():
        assert hashlib.sha256((app / name).read_bytes()).hexdigest() == digest
    assert "SHA256SUMS-macos-pilot.json" not in manifest["bundle"]["files"]


@pytest.mark.parametrize("failure", ["compiler", "no_bundle", "archive"])
def test_failed_external_step_or_absent_bundle_never_produces_manifest(mac, simulated_build, failure):
    calls, mode = simulated_build
    mode["failure"] = failure
    assert mac.main() == 1
    assert not (mac.DIST_DIR / "SHA256SUMS-macos-pilot.json").exists()
    if failure != "archive":
        assert not any(command[0] == "ditto" for command, _ in calls)


@pytest.mark.parametrize("missing", ["LICENSE", "assets/icons/simplicitor.ico",
    "prompts/system_word.txt", "templates/pptx_default.pptx",
    "templates_engine/builtin/business_pitch/template.pptx",
    "templates_engine/builtin/technical_overview/manifest.yaml", "third_party/inventory.json"])
def test_missing_payload_input_fails_before_archiving(mac, simulated_build, missing):
    calls, mode = simulated_build
    mode["missing"] = missing
    assert mac.main() == 1
    assert not any(command[0] == "ditto" for command, _ in calls)


def test_existing_output_is_not_deleted_or_overwritten(mac, simulated_build):
    calls, _ = simulated_build
    app = mac.DIST_DIR / "Simplicitor.app"
    app.mkdir(parents=True)
    (app / "keep.txt").write_text("keep")
    assert mac.main() == 1
    assert (app / "keep.txt").read_text() == "keep"
    assert calls == []


@pytest.mark.parametrize("outside", [False, True])
def test_inventory_keeps_internal_symlink_targets_and_rejects_escaping_links(mac, tmp_path, outside):
    app = tmp_path / "Simplicitor.app"
    app.mkdir()
    target = (tmp_path if outside else app) / "target"
    target.write_bytes(b"synthetic framework bytes")
    link = app / "current"
    try:
        link.symlink_to(Path("..") / "target" if outside else Path("target"))
    except OSError:
        pytest.skip("host cannot create a symlink; Mac source CI must exercise this check")
    if outside:
        with pytest.raises(ValueError, match="outside"):
            mac.bundle_inventory(app)
    else:
        inventory = mac.bundle_inventory(app)
        assert inventory["symlinks"] == {"current": "target"}
        assert inventory["files"] == {"target": hashlib.sha256(target.read_bytes()).hexdigest()}


def test_inventory_rejects_absolute_symlink_even_if_it_points_inside_the_build(mac, tmp_path, monkeypatch):
    app = tmp_path / "Simplicitor.app"
    app.mkdir()
    target = app / "target"
    target.write_bytes(b"synthetic framework bytes")
    link = app / "current"
    link.write_bytes(b"stand-in for a symlink on hosts without symlink privileges")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == link or original(p))
    monkeypatch.setattr(mac.os, "readlink", lambda p: str(target))
    # The target is inside the current app but its absolute path breaks on moving
    # or extracting the app elsewhere. Mock only link primitives, not the inventory.
    with pytest.raises(ValueError, match="symlink"):
        mac.bundle_inventory(app)
