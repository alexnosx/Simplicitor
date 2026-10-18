"""Qualification contracts on synthetic bundles. No Mac tools or app are run."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
from types import SimpleNamespace

import pytest


@pytest.fixture
def pilot(tmp_path, monkeypatch):
    q = importlib.import_module("scripts.qualify_macos_pilot")
    root = tmp_path / "checkout"
    root.mkdir()
    app = root / "dist/Simplicitor.app"
    payload = app / "Contents/MacOS"
    payload.mkdir(parents=True)
    for name in ("LICENSE", "assets/icons/simplicitor.ico", "templates/pptx_default.pptx",
                 *(f"prompts/system_{kind}.txt" for kind in ("word", "excel", "pptx", "manipulate")),
                 *(f"templates_engine/builtin/{kind}/{file}" for kind in
                   ("business_pitch", "technical_overview") for file in
                   ("manifest.yaml", "template.pptx"))):
        source = root / name if name.startswith(("LICENSE", "assets/")) else root / "simplicitor" / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"synthetic tracked resource " + name.encode())
        target = payload / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    exe = payload / "Simplicitor"
    exe.write_bytes(b"\xcf\xfa\xed\xfe synthetic Mach-O, never executed")
    exe.chmod(0o755)
    dependency = payload / "dependency.so"
    dependency.write_bytes(exe.read_bytes())
    dependency.chmod(0o755)
    resources = app / "Contents/Resources"
    resources.mkdir()
    (resources / "app.icns").write_bytes(b"icns synthetic icon")
    info = {"CFBundleName": "Simplicitor", "CFBundleDisplayName": "Simplicitor",
            "CFBundleIdentifier": "com.simplicitor.pilot", "CFBundleVersion": "2.5.1",
            "CFBundleShortVersionString": "2.5.1", "CFBundleExecutable": "Simplicitor",
            "CFBundlePackageType": "APPL", "LSMinimumSystemVersion": "14.0",
            "CFBundleIconFile": "app.icns"}
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    notice = payload / "third_party"
    notice.mkdir()
    (notice / "notice.txt").write_text("synthetic notices")
    archive = app.parent / "Simplicitor-macos-arm64-pilot.zip"
    archive.write_bytes(b"mock native ZIP, never extracted by real tools")
    manifest = app.parent / "SHA256SUMS-macos-pilot.json"
    record = {"pilot": True, "source_commit": "a" * 40, "version": "2.5.1",
              "architecture": "arm64", "minimum_macos": "14.0", "signing": "ad-hoc",
              "notarized": False, "runtime_versions": {"python": "3.11.9", "qt": "6.11.2",
                                                       "nuitka": "4.2.2"},
              "artifacts": {archive.name: hashlib.sha256(archive.read_bytes()).hexdigest()},
              "bundle": q.bundle_inventory(app)}
    manifest.write_text(json.dumps(record))
    runner = tmp_path / "runner"
    runner.mkdir()
    monkeypatch.setattr(q, "ROOT", root)
    monkeypatch.setattr(q.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(q.platform, "machine", lambda: "arm64")
    for key, value in {"GITHUB_ACTIONS": "true", "RUNNER_TEMP": str(runner),
                       "PILOT_HEAD_SHA": "a" * 40, "GITHUB_RUN_ID": "123",
                       "GITHUB_REPOSITORY": "alexnosx/Simplicitor", "ImageVersion": "test-image",
                       "USERPROFILE": "forbidden", "APPDATA": "forbidden",
                       "LOCALAPPDATA": "forbidden", "PYTHONPATH": "forbidden"}.items():
        monkeypatch.setenv(key, value)
    calls, launches, mode = [], [], {}

    def command(args, **kwargs):
        calls.append(args)
        output, error = "", ""
        if args[0] == "git":
            output = "a" * 40
        elif args[0] == "ditto":
            destination = Path(args[-1])
            assert not destination.is_relative_to(root)
            assert " " in str(destination) and "Ω" in str(destination)
            shutil.copytree(app, destination / app.name)
        elif args[0] == "lipo":
            output = mode.get("architectures", "x86_64 arm64")
        elif args[0] == "otool":
            output = mode.get("load_commands", "Load command 1\n cmd LC_BUILD_VERSION\n"
                              " cmdsize 32\n platform 1\n minos 11.0\n sdk 15.0\n")
        elif args[:2] == ["codesign", "--verify"]:
            if mode.get("bad_signature"):
                raise subprocess.CalledProcessError(1, args)
        elif args[:2] == ["codesign", "-d"]:
            error = mode.get("signature", "Signature=adhoc\nTeamIdentifier=not set\n")
        else:
            pytest.fail(f"unexpected tool {args[0]}")
        return SimpleNamespace(stdout=output, stderr=error, returncode=0)

    class Process:
        def __init__(self, args, **kwargs):
            launches.append((args, kwargs))
            self.stopped = False
            assert not Path(kwargs["cwd"]).is_relative_to(root)
            assert Path(args[0]).is_relative_to(runner)
            env = kwargs["env"]
            assert env["QT_QPA_PLATFORM"] == "offscreen" and env["PATH"] == "/usr/bin:/bin"
            assert not set(("USERPROFILE", "APPDATA", "LOCALAPPDATA", "PYTHONPATH")) & set(env)
            settings = Path(env["HOME"]) / "Library/Application Support/Simplicitor/settings.json"
            assert Path(json.loads(settings.read_text())["generated_dir"]) == (
                Path(env["HOME"]) / "Simplicitor/Generated")
            if mode.get("settings_mutation"):
                settings.write_text("changed")
            if mode.get("bundle_mutation"):
                Path(args[0]).write_bytes(b"changed")

        def wait(self, timeout):
            if self.stopped or mode.get("early_exit"):
                return 0
            assert timeout == 20
            raise subprocess.TimeoutExpired("synthetic app", timeout)

        def terminate(self):
            self.stopped = True

        def kill(self):
            self.stopped = True

    monkeypatch.setattr(q.subprocess, "run", command)
    monkeypatch.setattr(q.subprocess, "Popen", Process)
    monkeypatch.setattr(q.socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(
        ConnectionRefusedError()))
    notices = []
    monkeypatch.setattr(q, "validate_notices", lambda path: notices.append(path))
    return SimpleNamespace(q=q, app=app, manifest=manifest, report=app.parent / "report.json",
                           record=record, calls=calls, launches=launches, mode=mode,
                           info=info, notices=notices)


def run(pilot):
    pilot.q.qualify(pilot.app, pilot.manifest, pilot.report)
    return json.loads(pilot.report.read_text())


@pytest.mark.parametrize("system,arch,github", [("Windows", "arm64", "true"),
                                             ("Darwin", "x86_64", "true"),
                                             ("Darwin", "arm64", "false")])
def test_host_guard_precedes_any_staging_or_process(pilot, monkeypatch, system, arch, github):
    monkeypatch.setattr(pilot.q.platform, "system", lambda: system)
    monkeypatch.setattr(pilot.q.platform, "machine", lambda: arch)
    monkeypatch.setenv("GITHUB_ACTIONS", github)
    with pytest.raises(ValueError, match="GitHub Darwin arm64"):
        run(pilot)
    assert not pilot.report.exists() and not pilot.calls and not pilot.launches


def test_success_qualifies_extracted_copy_twice_without_ollama_and_records_limits(pilot):
    report = run(pilot)
    assert report["result"] == "passed"
    assert all(check["result"] == "passed" for check in report["checks"].values())
    assert report["source_commit"] == "a" * 40 and report["notarized"] is False
    assert report["run_url"] == "https://github.com/alexnosx/Simplicitor/actions/runs/123"
    assert report["runner_image"] == "test-image"
    assert report["runtime_versions"] == pilot.record["runtime_versions"]
    assert report["sha256"][pilot.manifest.name] == hashlib.sha256(pilot.manifest.read_bytes()).hexdigest()
    assert set(report["limits"]) == {"native_cocoa", "gatekeeper", "real_model", "office"}
    assert len(pilot.launches) == 2 and len(pilot.notices) == 1
    assert pilot.q.bundle_inventory(pilot.app) == pilot.record["bundle"]
    assert any(call[:5] == ["codesign", "--verify", "--deep", "--strict", "--verbose=2"]
               for call in pilot.calls)
    assert len(report["mach_o"]) == 2
    assert all(set(item["deployment_minima"]) == {"arm64", "x86_64"}
               for item in report["mach_o"])


@pytest.mark.parametrize("mutation,check", [("archive", "archive_and_manifest"),
                                           ("source", "archive_and_manifest"),
                                           ("inventory", "inventory_and_links")])
def test_manifest_archive_and_bundle_mismatches_fail_closed(pilot, mutation, check):
    if mutation == "archive":
        pilot.record["artifacts"]["Simplicitor-macos-arm64-pilot.zip"] = "0" * 64
    elif mutation == "source":
        pilot.record["source_commit"] = "b" * 40
    else:
        pilot.record["bundle"]["files"]["Contents/MacOS/Simplicitor"] = "0" * 64
    pilot.manifest.write_text(json.dumps(pilot.record))
    with pytest.raises(ValueError):
        run(pilot)
    report = json.loads(pilot.report.read_text())
    assert report["checks"][check]["result"] == "failed"
    assert report["checks"]["launch_1"]["result"] == "not checked"
    assert not pilot.launches


@pytest.mark.parametrize("missing", ["assets/icons/simplicitor.ico", "LICENSE",
                                    "templates/pptx_default.pptx",
                                    "templates_engine/builtin/technical_overview/template.pptx",
                                    "prompts/system_word.txt"])
def test_missing_required_payload_is_rejected_even_if_inventory_matches(pilot, missing):
    (pilot.app / "Contents/MacOS" / missing).unlink()
    pilot.record["bundle"] = pilot.q.bundle_inventory(pilot.app)
    pilot.manifest.write_text(json.dumps(pilot.record))
    with pytest.raises(ValueError):
        run(pilot)
    assert json.loads(pilot.report.read_text())["checks"]["resources_and_notices"]["result"] == "failed"


@pytest.mark.parametrize("key,value", [("CFBundleIdentifier", "wrong"),
                                      ("CFBundleVersion", "0.0.0"),
                                      ("LSMinimumSystemVersion", "15.0"),
                                      ("CFBundleIconFile", "missing.icns")])
def test_invalid_plist_or_missing_finder_icon_is_rejected(pilot, key, value):
    pilot.info[key] = value
    (pilot.app / "Contents/Info.plist").write_bytes(plistlib.dumps(pilot.info))
    pilot.record["bundle"] = pilot.q.bundle_inventory(pilot.app)
    pilot.manifest.write_text(json.dumps(pilot.record))
    with pytest.raises(ValueError):
        run(pilot)
    assert json.loads(pilot.report.read_text())["checks"]["plist_and_modes"]["result"] == "failed"


@pytest.mark.parametrize("setting,value", [("architectures", "x86_64"),
    ("load_commands", "cmd LC_BUILD_VERSION\n platform 1\n minos 15.0\n"),
    ("load_commands", "cmd LC_BUILD_VERSION\n platform 2\n minos 11.0\n"),
    ("load_commands", "cmd LC_UUID\n uuid synthetic\n")])
def test_every_macho_requires_arm64_and_known_macos_14_compatible_minimum(pilot, setting, value):
    pilot.mode[setting] = value
    with pytest.raises(ValueError):
        run(pilot)
    assert json.loads(pilot.report.read_text())["checks"]["mach_o"]["result"] == "failed"


def test_legacy_macos_deployment_command_is_accepted(pilot):
    pilot.mode["load_commands"] = "cmd LC_VERSION_MIN_MACOSX\n cmdsize 16\n version 10.15\n sdk 14.0\n"
    assert run(pilot)["result"] == "passed"


@pytest.mark.parametrize("setting,value", [("bad_signature", True),
    ("signature", "Signature=Developer ID\nTeamIdentifier=ABCD\n"),
    ("signature", "Signature=adhoc\nTeamIdentifier=ABCD\n")])
def test_invalid_or_non_adhoc_signature_blocks_launch(pilot, setting, value):
    pilot.mode[setting] = value
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        run(pilot)
    assert not pilot.launches
    assert json.loads(pilot.report.read_text())["checks"]["signature"]["result"] == "failed"


@pytest.mark.parametrize("setting,check", [("early_exit", "launch_1"),
                                         ("settings_mutation", "settings_and_sentinel"),
                                         ("bundle_mutation", "bundle_unchanged")])
def test_early_exit_and_changes_to_preserved_bytes_fail(pilot, setting, check):
    pilot.mode[setting] = True
    with pytest.raises(ValueError):
        run(pilot)
    assert json.loads(pilot.report.read_text())["checks"][check]["result"] == "failed"


def test_existing_ollama_endpoint_blocks_qualification(pilot, monkeypatch):
    class Connection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
    monkeypatch.setattr(pilot.q.socket, "create_connection", lambda *a, **k: Connection())
    with pytest.raises(ValueError):
        run(pilot)
    assert not pilot.launches
    assert json.loads(pilot.report.read_text())["checks"]["no_ollama"]["result"] == "failed"


def test_notice_validation_remains_strict(pilot, monkeypatch):
    def invalid(path):
        raise ValueError("missing license text")
    monkeypatch.setattr(pilot.q, "validate_notices", invalid)
    with pytest.raises(ValueError):
        run(pilot)
    assert not pilot.launches


def test_runner_temp_must_be_outside_checkout(pilot, monkeypatch):
    monkeypatch.setenv("RUNNER_TEMP", str(pilot.q.ROOT))
    with pytest.raises(ValueError, match="outside"):
        run(pilot)
    assert not pilot.calls
