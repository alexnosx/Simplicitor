#!/usr/bin/env python3
"""
Build a standalone Windows payload, built-in NSIS installer, and portable ZIP.

Usage:
    pip install -r requirements-build.txt
    python build.py

Outputs: dist/Simplicitor-setup.exe, Simplicitor-portable.zip, SHA256SUMS.json.
Run from the repository root (the directory containing this file).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).parent
SIMPLICITOR_DIR = ROOT / "simplicitor"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"
ICON = ASSETS_DIR / "icons" / "simplicitor.ico"

# ---------------------------------------------------------------------------
# Nuitka flags
# ---------------------------------------------------------------------------
NUITKA_FLAGS = [
    "--mode=standalone",
    "--windows-create-installer",
    "--windows-installer-mode=user",
    "--windows-installer-shortcuts=desktop,start-menu",
    "--windows-installer-no-user-change-install-dir",
    "--python-flag=isolated",
    "--windows-console-mode=disable",
    "--enable-plugin=pyside6",
    "--assume-yes-for-downloads",
    # Bundle the prompts/ directory so the app can read system prompts at runtime.
    # Source path is relative to the build working directory (simplicitor/).
    "--include-data-dir=prompts=prompts",
    # Bundle the pptx default template — python-pptx's internal copy is not
    # accessible unless explicitly bundled.
    "--include-data-dir=templates=templates",
    # Bundle the curated default templates (business_pitch, technical_overview) so
    # get_builtin_root() resolves at runtime and ensure_default_templates() can seed them.
    "--include-data-dir=templates_engine/builtin=templates_engine/builtin",
    # Bundle the assets directory so icons are available at runtime.
    f"--include-data-dir={ASSETS_DIR}=assets",
    f"--windows-icon-from-ico={ICON}",
    "--windows-product-name=Simplicitor",
    "--windows-product-version=1.2.1.0",
    "--windows-company-name=Simplicitor",
    "--windows-file-description=Private local document workspace",
    "--output-filename=Simplicitor",
]


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def correct_uninstall(script: str, payload: Path) -> str:
    """Replace the pinned backend's exact recursive removal with owned-file removal."""
    marker = '  RMDir /r "$INSTDIR"\n'
    section = 'Section "Uninstall"\n'
    if script.count(section) != 1 or script.count(marker) != 1:
        raise ValueError("Unexpected Nuitka uninstall script; review the pinned backend.")
    uninstall = script.split(section, 1)[1].split("SectionEnd", 1)[0]
    if marker not in uninstall:
        raise ValueError("Unexpected Nuitka uninstall section; refusing correction.")

    def relative(path: Path) -> str:
        return str(path.relative_to(payload)).replace("$", "$$")

    files = sorted((p for p in payload.rglob("*") if p.is_file()),
                   key=lambda p: p.relative_to(payload).as_posix())
    directories = sorted((p for p in payload.rglob("*") if p.is_dir()),
                         key=lambda p: (-len(p.parts), str(p)))
    commands = [f'  Delete "$INSTDIR\\{relative(p)}"' for p in files]
    commands += [f'  RMDir "$INSTDIR\\{relative(p)}"' for p in directories]
    commands.append('  RMDir "$INSTDIR"')  # Non-recursive: user files keep their directory.
    return script.replace(marker, "\n".join(commands) + "\n")


def rebuild_installer(payload: Path, installer: Path) -> None:
    """Correct Nuitka's generated script and compile it with the same NSIS tool."""
    scripts = list(payload.parent.glob("*.installer-build/installer.nsi"))
    if len(scripts) != 1 or not installer.is_file():
        raise ValueError("Missing or ambiguous Nuitka installer outputs.")
    script = scripts[0]
    corrected = correct_uninstall(script.read_text(encoding="utf-8"), payload)
    tool = shutil.which("makensis")
    if tool is None:
        cached = list(Path(os.environ["NUITKA_CACHE_DIR"]).glob(
            "downloads/makensis/*/nsis-*/makensis.exe"))
        if len(cached) != 1:
            raise ValueError("Missing or ambiguous cached NSIS compiler.")
        tool = str(cached[0])
    script.write_text(corrected, encoding="utf-8")
    installer.unlink()  # Never retain the original recursive uninstaller as a valid artifact.
    result = subprocess.run([tool, "/V2", str(script)], cwd=script.parent)
    if result.returncode:
        raise ValueError(f"Corrected installer compilation failed ({result.returncode}).")


def package_payload(payload: Path, installer: Path) -> None:
    """Validate resources and archive exactly the payload supplied to NSIS."""
    required = (
        "Simplicitor.exe", "prompts/system_word.txt", "prompts/system_excel.txt",
        "prompts/system_pptx.txt", "templates/pptx_default.pptx",
        "templates_engine/builtin/business_pitch/manifest.yaml",
        "templates_engine/builtin/business_pitch/template.pptx",
        "templates_engine/builtin/technical_overview/manifest.yaml",
        "templates_engine/builtin/technical_overview/template.pptx",
        "assets/icons/simplicitor.ico",
    )
    for path in (*(payload / name for name in required), installer):
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty build output: {path}")
    files = sorted(p for p in payload.rglob("*") if p.is_file())
    portable = DIST_DIR / "Simplicitor-portable.zip"
    with ZipFile(portable, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "Simplicitor/" + path.relative_to(payload).as_posix())
    manifest = {
        "payload": {p.relative_to(payload).as_posix(): _sha256(p) for p in files},
        "artifacts": {p.name: _sha256(p) for p in (installer, portable)},
    }
    (DIST_DIR / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                             encoding="utf-8")


def main() -> int:
    """Compile once with Nuitka's NSIS backend, then package the same payload."""
    if not ICON.exists():
        print(
            f"ERROR: icon not found at {ICON}\n"
            "Place icon files in assets/icons/ (see docs for details).",
            file=sys.stderr,
        )
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NUITKA_CACHE_DIR", str(ROOT / ".nuitka"))
    installer = DIST_DIR / "Simplicitor-setup.exe"
    for path in (installer, DIST_DIR / "Simplicitor-portable.zip", DIST_DIR / "SHA256SUMS.json"):
        path.unlink(missing_ok=True)
    output = DIST_DIR / "standalone"
    cmd = [sys.executable, "-m", "nuitka", *NUITKA_FLAGS,
           f"--output-dir={output}", f"--windows-installer-output={installer}", "main.py"]

    print("Building Simplicitor standalone and installer ...")
    print("Command:", " ".join(str(c) for c in cmd))
    print(f"Working directory: {SIMPLICITOR_DIR}")
    print()

    result = subprocess.run(cmd, cwd=SIMPLICITOR_DIR)

    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})", file=sys.stderr)
        return result.returncode

    try:
        rebuild_installer(output / "main.dist", installer)
        package_payload(output / "main.dist", installer)
    except (OSError, ValueError) as exc:
        for path in (installer, DIST_DIR / "Simplicitor-portable.zip", DIST_DIR / "SHA256SUMS.json"):
            path.unlink(missing_ok=True)
        print(f"\nPackaging FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"\nBuild complete: {installer}, Simplicitor-portable.zip, SHA256SUMS.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
