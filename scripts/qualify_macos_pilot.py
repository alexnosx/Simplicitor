#!/usr/bin/env python3
"""Hosted-only, offline qualification of an extracted Apple silicon pilot ZIP.

This does not establish Gatekeeper trust, native GUI quality or model correctness.
External tools and child processes are mocked in the local source tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_macos import PRODUCT_VERSION, bundle_inventory
from scripts.build_third_party_notices import validate_notices

CHECKS = ("archive_and_manifest", "inventory_and_links", "plist_and_modes",
          "resources_and_notices", "mach_o", "signature", "no_ollama", "launch_1", "launch_2",
          "settings_and_sentinel", "bundle_unchanged")
MACH_MAGICS = {bytes.fromhex(value) for value in (
    "feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _require_host() -> Path:
    if (os.environ.get("GITHUB_ACTIONS") != "true" or platform.system() != "Darwin"
            or platform.machine() != "arm64"):
        raise ValueError("Qualification requires a GitHub Darwin arm64 runner")
    runner = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    if runner.is_relative_to(ROOT.resolve()):
        raise ValueError("Runner temporary folder must be outside the checkout")
    return runner


def assert_no_ollama() -> None:
    """Refuse an available loopback endpoint; never install or contact a model."""
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, 11434), timeout=2):
                pass
        except ConnectionRefusedError:
            continue
        except OSError as exc:
            # An unavailable IPv6 protocol/address is acceptable; a timeout is not proof.
            if exc.errno in (47, 49, 97, 99, 10047, 10049):
                continue
            raise ValueError("Cannot establish that Ollama is unavailable") from exc
        raise ValueError("An Ollama endpoint is available on the qualification runner")


def _command(args: list[str]) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True, timeout=60)
    return result.stdout + result.stderr


def _minimum(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        raise ValueError("Unknown deployment minimum")
    return tuple((list(map(int, value.split("."))) + [0])[:3])


def _plist_and_modes(app: Path, version: str) -> None:
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    expected = {"CFBundleName": "Simplicitor", "CFBundleDisplayName": "Simplicitor",
                "CFBundleIdentifier": "com.simplicitor.pilot", "CFBundleVersion": version,
                "CFBundleShortVersionString": version, "CFBundleExecutable": "Simplicitor",
                "CFBundlePackageType": "APPL", "LSMinimumSystemVersion": "15.0"}
    if any(info.get(key) != value for key, value in expected.items()):
        raise ValueError("Unexpected app plist identity, version or minimum OS")
    icon = info.get("CFBundleIconFile", "")
    if not icon or Path(icon).name != icon:
        raise ValueError("Invalid app icon name")
    if not icon.endswith(".icns"):
        icon += ".icns"
    icon_path = app / "Contents/Resources" / icon
    if not icon_path.is_file() or icon_path.read_bytes()[:4] != b"icns":
        raise ValueError("Missing ICNS app icon")
    if not os.access(app / "Contents/MacOS/Simplicitor", os.X_OK):
        raise ValueError("App executable mode was not preserved")


def _resources(app: Path) -> None:
    payload = app / "Contents/MacOS"
    names = ["LICENSE", "assets/icons/simplicitor.ico", "templates/pptx_default.pptx"]
    names += [f"prompts/system_{name}.txt" for name in ("word", "excel", "pptx", "manipulate")]
    names += [f"templates_engine/builtin/{name}/{file}" for name in
              ("business_pitch", "technical_overview") for file in ("manifest.yaml", "template.pptx")]
    for name in names:
        source = ROOT / name if name.startswith(("LICENSE", "assets/")) else ROOT / "simplicitor" / name
        target = payload / name
        if not target.is_file() or not target.stat().st_size or _sha256(source) != _sha256(target):
            raise ValueError("Required resource missing or different from tracked source")
    validate_notices(payload / "third_party")


def _mach_o(app: Path, records: list[dict], offenders: list[dict]) -> None:
    # Populate the report as we scan, including minima from rejected and passing slices.
    declared = plistlib.loads((app / "Contents/Info.plist").read_bytes())["LSMinimumSystemVersion"]
    app_minimum = _minimum(declared)
    for path in sorted(app.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            magic = stream.read(4)
        if magic not in MACH_MAGICS:
            continue
        relative = path.relative_to(app).as_posix()
        architectures = _command(["lipo", "-archs", str(path)]).split()
        minima = {}
        records.append({"path": relative, "architectures": architectures,
                        "deployment_minima": minima})

        def offend(arch, reason, field=None, value=None):
            offenders.append({"path": relative, "architecture": arch,
                              "minimum_field": field, "minimum": value, "reason": reason})

        if "arm64" not in architectures:
            offend(" ".join(architectures) or "unknown", "Missing arm64")
        for arch in architectures:
            output = _command(["otool", "-arch", arch, "-l", str(path)])
            versions = []
            for block in re.split(r"(?m)^\s*cmd ", output)[1:]:
                if block.startswith("LC_BUILD_VERSION\n"):
                    field = "minos"
                    platform_match = re.search(r"(?m)^\s*platform (\S+)\s*$", block)
                    match = re.search(r"(?m)^\s*minos (\S+)\s*$", block)
                    if not platform_match or platform_match[1] not in ("1", "MACOS"):
                        offend(arch, "Targets another or unknown platform", field,
                               match[1] if match else None)
                elif block.startswith("LC_VERSION_MIN_MACOSX\n"):
                    field = "version"
                    match = re.search(r"(?m)^\s*version (\S+)\s*$", block)
                else:
                    continue
                if not match:
                    offend(arch, "Unknown deployment minimum", field)
                    continue
                versions.append(match[1])
                try:
                    minimum = _minimum(match[1])
                except ValueError:
                    offend(arch, "Unknown deployment minimum", field, match[1])
                    continue
                if minimum > app_minimum:
                    offend(arch, f"Requires later than macOS {declared}", field, match[1])
            if len(versions) != 1:
                offend(arch, "Deployment minimum is unknown or ambiguous")
            minima[arch] = versions[0] if len(versions) == 1 else versions
    if not any(item["path"] == "Contents/MacOS/Simplicitor" for item in records):
        offenders.append({"path": "Contents/MacOS/Simplicitor", "architecture": "unknown",
                          "minimum_field": None, "minimum": None,
                          "reason": "Main executable is not a Mach-O"})
    if offenders:
        details = "; ".join(
            f"{item['path']} [{item['architecture']}] "
            f"{item['minimum_field'] or 'minimum'}={item['minimum'] or 'unknown'}: "
            f"{item['reason']}" for item in offenders)
        raise ValueError(f"Bundled Mach-O checks failed: {details}")


def _signature(app: Path) -> str:
    _command(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)])
    identity = _command(["codesign", "-d", "--verbose=4", str(app)])
    if ("Signature=adhoc" not in identity.splitlines()
            or "TeamIdentifier=not set" not in identity.splitlines()):
        raise ValueError("Expected ad-hoc signature without Team ID")
    return "ad-hoc; no Team ID; deep strict verification passed"


def _launch(executable: Path, home: Path, cwd: Path) -> None:
    environment = {"HOME": str(home), "PATH": "/usr/bin:/bin", "QT_QPA_PLATFORM": "offscreen",
                   "TMPDIR": str(cwd), "LANG": "en_US.UTF-8"}
    process = subprocess.Popen([str(executable)], cwd=cwd, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            return
        raise ValueError("Extracted app exited before 20 seconds")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def qualify(bundle: Path, manifest: Path, report: Path) -> None:
    """Check the shipped archive on a guarded runner; write a named-check report on failure."""
    runner = _require_host()  # Must precede output/staging and all external commands.
    record = {
        "pilot": True, "result": "failed", "notarized": False,
        "source_commit": os.environ.get("PILOT_HEAD_SHA"),
        "run_url": f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
                   f"{os.environ['GITHUB_RUN_ID']}",
        "runner_image": os.environ.get("ImageVersion"), "macos": platform.mac_ver()[0],
        "architecture": platform.machine(), "python": platform.python_version(),
        "limits": {name: "not checked" for name in ("native_cocoa", "gatekeeper", "real_model", "office")},
        "checks": {name: {"result": "not checked", "reason": "Earlier check has not passed"}
                   for name in CHECKS},
    }
    active = "archive_and_manifest"

    def check(name, operation):
        nonlocal active
        active = name
        result = operation()
        record["checks"][name] = {"result": "passed", "reason": "Check completed"}
        return result

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        source = _command(["git", "rev-parse", "HEAD"]).strip()
        archive = manifest.parent / "Simplicitor-macos-arm64-pilot.zip"
        if (not re.fullmatch(r"[0-9a-f]{40}", source)
                or source != record["source_commit"] or source != data.get("source_commit")
                or data.get("pilot") is not True or data.get("architecture") != "arm64"
                or data.get("version") != PRODUCT_VERSION or data.get("minimum_macos") != "15.0"
                or data.get("signing") != "ad-hoc" or data.get("notarized") is not False
                or data.get("artifacts") != {archive.name: _sha256(archive)}):
            raise ValueError("Archive or manifest does not match this pilot source")
        record["sha256"] = {archive.name: _sha256(archive), manifest.name: _sha256(manifest)}
        record["version"] = data["version"]
        record["minimum_macos"] = data["minimum_macos"]
        record["archive_size_bytes"] = archive.stat().st_size
        record["runtime_versions"] = data["runtime_versions"]
        check("archive_and_manifest", lambda: None)
        with tempfile.TemporaryDirectory(prefix="Simplicitor pilot Ω ", dir=runner) as folder:
            stage = Path(folder)
            extracted = stage / "extracted"
            active = "inventory_and_links"
            _command(["ditto", "-x", "-k", str(archive.resolve()), str(extracted)])
            app = extracted / "Simplicitor.app"
            if bundle.name != app.name or set(extracted.iterdir()) != {app}:
                raise ValueError("Unexpected extracted bundle layout")
            inventory = bundle_inventory(app)
            if inventory != data["bundle"]:
                raise ValueError("Extracted inventory or symlinks differ from manifest")
            check("inventory_and_links", lambda: None)
            check("plist_and_modes", lambda: _plist_and_modes(app, data["version"]))
            check("resources_and_notices", lambda: _resources(app))
            record["mach_o"], record["mach_o_offenders"] = [], []
            check("mach_o", lambda: _mach_o(app, record["mach_o"], record["mach_o_offenders"]))
            record["signature"] = check("signature", lambda: _signature(app))
            check("no_ollama", assert_no_ollama)
            home, cwd = stage / "home", stage / "unrelated working folder"
            cwd.mkdir()
            settings = home / "Library/Application Support/Simplicitor/settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text(json.dumps({f"{kind.lower()}_dir": str(home / "Simplicitor" / kind)
                                            for kind in ("Generated", "Uploads", "Backups", "Logs", "Templates")}),
                                encoding="utf-8")
            sentinel = home / "Simplicitor/synthetic-sentinel.txt"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("Synthetic local document. Must survive both launches.", encoding="utf-8")
            originals = {path: path.read_bytes() for path in (settings, sentinel)}
            for number in (1, 2):
                check(f"launch_{number}", lambda: _launch(app / "Contents/MacOS/Simplicitor", home, cwd))
                active = "settings_and_sentinel"
                if any(path.read_bytes() != value for path, value in originals.items()):
                    raise ValueError("Synthetic settings or sentinel document changed")
                check("settings_and_sentinel", lambda: None)
                active = "bundle_unchanged"
                if bundle_inventory(app) != inventory:
                    raise ValueError("Bundled files changed during smoke launches")
                check("bundle_unchanged", lambda: None)
        record["result"] = "passed"
    except Exception as exc:
        record["checks"][active] = {"result": "failed", "reason": (
            str(exc) if isinstance(exc, ValueError) else type(exc).__name__)}
        print(json.dumps(record, indent=2), file=sys.stderr)
        raise
    finally:
        report.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    """Parse the three artifact paths; return nonzero without exposing tool output."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "manifest", "report"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        qualify(args.bundle, args.manifest, args.report)
    except Exception as exc:
        print(f"Mac qualification failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
