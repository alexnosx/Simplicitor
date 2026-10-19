#!/usr/bin/env python3
"""Build the Apple silicon pilot on a Mac runner. Never invokes the Windows builder.

Nuitka assembles and ad-hoc signs Simplicitor.app. Data is accessible beside the executable
in Contents/MacOS: prompts/, templates/, templates_engine/builtin/, assets/, LICENSE
and third_party/, using internal symlinks where Nuitka relocates data for signing.
Contents/Resources holds the native application icon prepared with Apple's iconutil.
The signed app is moved intact to dist/macos-pilot and archived with native ditto.
Nothing inside the app is written after Nuitka returns.
"""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import runpy
import shutil
import subprocess
import sys

from PIL import Image
from PySide6.QtCore import qVersion

from scripts.build_third_party_notices import build_notices, validate_notices

ROOT = Path(__file__).resolve().parent
WORK_DIR = ROOT / ".nuitka" / "macos-pilot"
DIST_DIR = ROOT / "dist" / "macos-pilot"
PRODUCT_VERSION = runpy.run_path(str(ROOT / "simplicitor/app/version.py"))["__version__"]


def nuitka_command(output_dir: Path) -> list[str]:
    """Describe the pinned-tool app build without writing files or running tools."""
    return [
        sys.executable, "-m", "nuitka", "--mode=app", "--python-flag=isolated",
        "--enable-plugin=pyside6", "--macos-target-arch=arm64", "--jobs=2",
        "--macos-app-name=Simplicitor", "--output-folder-name=Simplicitor",
        "--output-filename=Simplicitor", "--macos-signed-app-name=com.simplicitor.pilot",
        "--macos-sign-identity=ad-hoc", f"--macos-app-version={PRODUCT_VERSION}",
        "--macos-app-macos-min-version=14.0", "--macos-app-mode=gui",
        "--macos-app-console-mode=disable", f"--macos-app-icon={WORK_DIR / 'simplicitor.icns'}",
        "--include-data-dir=prompts=prompts", "--include-data-dir=templates=templates",
        "--include-data-dir=templates_engine/builtin=templates_engine/builtin",
        f"--include-data-dir={ROOT / 'assets'}=assets",
        f"--include-data-files={ROOT / 'LICENSE'}=LICENSE",
        f"--include-data-dir={WORK_DIR / 'third_party'}=third_party",
        f"--output-dir={output_dir}", "main.py",
    ]


def write_icon() -> Path:
    """Resize the largest original S into an iconset; use native iconutil for ICNS."""
    iconset = WORK_DIR / "simplicitor.iconset"
    iconset.mkdir()
    target = WORK_DIR / "simplicitor.icns"
    with Image.open(ROOT / "assets/icons/simplicitor.ico") as image:
        size = max(image.ico.sizes(), key=lambda s: s[0] * s[1])
        largest = image.ico.getimage(size).convert("RGBA")
        for logical_size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = logical_size * scale
                suffix = "@2x" if scale == 2 else ""
                name = f"icon_{logical_size}x{logical_size}{suffix}.png"
                largest.resize((pixels, pixels), Image.Resampling.LANCZOS).save(
                    iconset / name, format="PNG")
    subprocess.run(["iconutil", "-c", "icns", "-o", str(target), str(iconset)], check=True)
    if not target.is_file() or target.read_bytes()[:4] != b"icns":
        raise ValueError("Native icon conversion did not produce an ICNS file")
    return target


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def bundle_inventory(app: Path) -> dict:
    """Hash files and record relative symlinks that stay inside the portable app."""
    root = app.resolve(strict=True)
    files, symlinks = {}, {}
    for path in sorted(app.rglob("*")):
        relative = path.relative_to(app).as_posix()
        if path.is_symlink():
            target = os.readlink(path)
            if Path(target).is_absolute() or not path.resolve(strict=True).is_relative_to(root):
                raise ValueError("Bundle symlink points outside the app")
            symlinks[relative] = target
        elif path.is_file():
            files[relative] = _sha256(path)
    return {"files": files, "symlinks": symlinks}


def _validate_bundle(app: Path) -> None:
    payload = app / "Contents/MacOS"
    required = ["Simplicitor", "LICENSE", "assets/icons/simplicitor.ico",
                "templates/pptx_default.pptx"]
    required += [f"prompts/system_{name}.txt" for name in ("word", "excel", "pptx", "manipulate")]
    required += [f"templates_engine/builtin/{name}/{file}"
                 for name in ("business_pitch", "technical_overview")
                 for file in ("manifest.yaml", "template.pptx")]
    if any(not (payload / name).is_file() or not (payload / name).stat().st_size
           for name in required):
        raise ValueError("Missing or empty Mac bundle input")
    for relative in ("LICENSE", "assets/icons/simplicitor.ico"):
        if _sha256(payload / relative) != _sha256(ROOT / relative):
            raise ValueError("Mac bundle input differs from source")
    validate_notices(payload / "third_party")


def _require_host() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("Mac pilot build requires Darwin arm64")


def build() -> tuple[Path, Path]:
    """Assemble, sign through Nuitka, and archive a pilot; return ZIP and manifest."""
    _require_host()
    app = DIST_DIR / "Simplicitor.app"
    archive = DIST_DIR / "Simplicitor-macos-arm64-pilot.zip"
    manifest = DIST_DIR / "SHA256SUMS-macos-pilot.json"
    if any(path.exists() or path.is_symlink() for path in (
        app, archive, manifest, WORK_DIR / "Simplicitor.app", WORK_DIR / "third_party"
    )):
        raise FileExistsError("Use a fresh Mac pilot build workspace")
    source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Expected an exact source commit")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    write_icon()
    build_notices(ROOT, WORK_DIR / "third_party")
    validate_notices(WORK_DIR / "third_party")
    environment = dict(os.environ, MACOSX_DEPLOYMENT_TARGET="14.0")
    subprocess.run(nuitka_command(WORK_DIR), cwd=ROOT / "simplicitor", env=environment, check=True)
    built_app = WORK_DIR / "Simplicitor.app"
    _validate_bundle(built_app)
    inventory = bundle_inventory(built_app)
    shutil.move(str(built_app), str(app))
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                    str(app), str(archive)], check=True)
    if not archive.is_file() or not archive.stat().st_size:
        raise ValueError("Mac archive was not created")
    record = {
        "pilot": True, "version": PRODUCT_VERSION, "source_commit": source,
        "architecture": "arm64", "minimum_macos": "14.0",
        "runtime_versions": {"python": platform.python_version(), "qt": qVersion(),
                             "nuitka": metadata.version("Nuitka")},
        "signing": "ad-hoc", "notarized": False,
        "artifacts": {archive.name: _sha256(archive)},
        "bundle_layout": {"root": app.name, "executable": "Contents/MacOS/Simplicitor",
                          "data": "Contents/MacOS", "icon": "Contents/Resources"},
        "bundle": inventory,
    }
    manifest.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return archive, manifest


def main() -> int:
    """Refuse other hosts before any build side effect; report tool failures safely."""
    try:
        build()
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Mac pilot build failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
