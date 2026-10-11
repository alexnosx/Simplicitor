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
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.build_third_party_notices import build_notices, validate_notices

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
    f"--include-data-files={ROOT / 'LICENSE'}=LICENSE",
    f"--windows-icon-from-ico={ICON}",
    "--windows-product-name=Simplicitor",
    "--windows-product-version=2.0.0.0",
    "--windows-company-name=Simplicitor",
    "--windows-file-description=Private local document workspace",
    "--output-filename=Simplicitor",
]


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _wix_id(prefix: str, relative: str) -> str:
    return prefix + hashlib.sha256(relative.encode("utf-8")).hexdigest()[:40]


def payload_fragment(payload: Path) -> str:
    """WiX fragment: one per-user component per payload folder (HKCU key path,
    the folder's files, and its RemoveFolder) under INSTALLFOLDER."""
    folders = [payload] + sorted((p for p in payload.rglob("*") if p.is_dir()),
                                 key=lambda p: p.relative_to(payload).as_posix())
    rel = {f: (f.relative_to(payload).as_posix() or ".") for f in folders}
    dir_id = {f: ("INSTALLFOLDER" if f == payload else _wix_id("d", rel[f])) for f in folders}
    lines = ['<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">', "  <Fragment>",
             '    <DirectoryRef Id="INSTALLFOLDER">']

    def nest(folder: Path, depth: int) -> None:
        for child in sorted(p for p in folder.iterdir() if p.is_dir()):
            pad = "  " * depth
            lines.append(f'{pad}<Directory Id="{dir_id[child]}" Name={quoteattr(child.name)}>')
            nest(child, depth + 1)
            lines.append(f"{pad}</Directory>")

    nest(payload, 3)
    lines += ["    </DirectoryRef>", '    <ComponentGroup Id="Payload">']
    for folder in folders:
        lines.append(f'      <Component Id="{_wix_id("c", rel[folder])}" Directory="{dir_id[folder]}">')
        lines.append('        <RegistryValue Root="HKCU" Key="Software\\Simplicitor\\Installer\\Payload" '
                     f'Name={quoteattr(rel[folder])} Type="integer" Value="1" KeyPath="yes" />')
        lines.append(f'        <RemoveFolder Id="{_wix_id("r", rel[folder])}" On="uninstall" />')
        for file in sorted(p for p in folder.iterdir() if p.is_file()):
            relative = file.relative_to(payload).as_posix()
            source = "!(bindpath.payload)\\" + relative.replace("/", "\\")
            lines.append(f'        <File Id="{_wix_id("f", relative)}" Source={quoteattr(source)} />')
        lines.append("      </Component>")
    lines += ["    </ComponentGroup>", "  </Fragment>", "</Wix>"]
    return "\n".join(lines) + "\n"

def package_payload(payload: Path, installer: Path) -> None:
    """Validate resources and archive exactly the payload supplied to NSIS."""
    required = (
        "Simplicitor.exe", "LICENSE", "prompts/system_word.txt", "prompts/system_excel.txt",
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
    if _sha256(payload / "LICENSE") != _sha256(ROOT / "LICENSE"):
        raise ValueError("Packaged LICENSE does not match the project's current LICENSE.")
    validate_notices(payload / "third_party")
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
    notices = ROOT / ".nuitka" / "third_party_notices"
    try:
        build_notices(ROOT, notices)
    except (OSError, ValueError) as exc:
        print(f"\nNotice preparation FAILED: {exc}", file=sys.stderr)
        return 1
    installer = DIST_DIR / "Simplicitor-setup.exe"
    for path in (installer, DIST_DIR / "Simplicitor-portable.zip", DIST_DIR / "SHA256SUMS.json"):
        path.unlink(missing_ok=True)
    output = DIST_DIR / "standalone"
    cmd = [sys.executable, "-m", "nuitka", *NUITKA_FLAGS,
           f"--include-data-dir={notices}=third_party",
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
