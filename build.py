#!/usr/bin/env python3
"""
Simplicitor build script — produces dist/Simplicitor.exe via Nuitka.

Usage:
    pip install -r requirements-build.txt
    python build.py

The .exe is written to dist/Simplicitor.exe.
Run from the repository root (the directory containing this file).
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SIMPLICITOR_DIR = ROOT / "simplicitor"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"
ICON = ASSETS_DIR / "icons" / "simplicitor.ico"

# ---------------------------------------------------------------------------
# Nuitka flags
# ---------------------------------------------------------------------------
NUITKA_FLAGS = [
    "--onefile",
    "--windows-console-mode=disable",
    "--enable-plugin=pyside6",
    "--assume-yes-for-downloads",
    # Bundle the prompts/ directory so the app can read system prompts at runtime.
    # Source path is relative to the build working directory (simplicitor/).
    "--include-data-dir=prompts=prompts",
    # Bundle the pptx default template — python-pptx's internal copy is not
    # accessible inside a Nuitka onefile executable.
    "--include-data-dir=templates=templates",
    # Bundle the curated default templates (business_pitch, technical_overview) so
    # get_builtin_root() resolves at runtime and ensure_default_templates() can seed them.
    "--include-data-dir=templates_engine/builtin=templates_engine/builtin",
    # Bundle the assets directory so icons are available at runtime.
    f"--include-data-dir={ASSETS_DIR}=assets",
    f"--windows-icon-from-ico={ICON}",
    "--windows-product-name=Simplicitor",
    "--windows-product-version=1.2.0.0",
    "--windows-company-name=Simplicitor",
    "--windows-file-description=AI-powered Office document generator",
    f"--output-dir={DIST_DIR}",
    "--output-filename=Simplicitor",
]


def main() -> int:
    if not ICON.exists():
        print(
            f"ERROR: icon not found at {ICON}\n"
            "Place icon files in assets/icons/ (see docs for details).",
            file=sys.stderr,
        )
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "nuitka", *NUITKA_FLAGS, "main.py"]

    print("Building Simplicitor.exe ...")
    print("Command:", " ".join(str(c) for c in cmd))
    print(f"Working directory: {SIMPLICITOR_DIR}")
    print()

    result = subprocess.run(cmd, cwd=SIMPLICITOR_DIR)

    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})", file=sys.stderr)
        return result.returncode

    exe = DIST_DIR / "Simplicitor.exe"
    size_mb = exe.stat().st_size / (1024 * 1024) if exe.exists() else 0
    print(f"\nBuild complete: {exe}  ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
