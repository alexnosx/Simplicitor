#!/usr/bin/env python3
"""
Build a standalone Windows payload, per-user MSI, and portable ZIP.

Usage:
    pip install -r requirements-build.txt
    python build.py

Outputs: dist/Simplicitor-<version>.msi, Simplicitor-portable.zip, SHA256SUMS.json.
Run from the repository root (the directory containing this file).
"""
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from xml.sax.saxutils import quoteattr
from zipfile import ZIP_DEFLATED, ZipFile

from scripts.build_third_party_notices import build_notices, validate_notices

ROOT = Path(__file__).parent
SIMPLICITOR_DIR = ROOT / "simplicitor"
ASSETS_DIR = ROOT / "assets"
DIST_DIR = ROOT / "dist"
ICON = ASSETS_DIR / "icons" / "simplicitor.ico"

PRODUCT_VERSION = runpy.run_path(str(SIMPLICITOR_DIR / "app" / "version.py"))["__version__"]
WIX_SOURCE = ROOT / "packaging" / "simplicitor.wxs"
FRAGMENT = ROOT / ".nuitka" / "msi" / "payload.wxs"


def upgrade_probe_version(version: str = PRODUCT_VERSION) -> str:
    """A throwaway version just above *version*, for the hosted major-upgrade check."""
    major, minor, patch = (int(part) for part in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


# ---------------------------------------------------------------------------
# Nuitka flags
# ---------------------------------------------------------------------------
NUITKA_FLAGS = [
    "--mode=standalone",
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
    f"--windows-product-version={PRODUCT_VERSION}.0",
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
        # WiX cannot auto-generate GUIDs for components with files and a registry key path.
        guid = uuid5(NAMESPACE_URL, "https://simplicitor.com/msi/payload/" + rel[folder])
        lines.append(f'      <Component Id="{_wix_id("c", rel[folder])}" '
                     f'Guid="{guid}" Directory="{dir_id[folder]}">')
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

def build_msi(payload: Path, version: str, output: Path) -> None:
    """Compile the per-user MSI from the standalone payload with the pinned WiX tool."""
    FRAGMENT.parent.mkdir(parents=True, exist_ok=True)
    FRAGMENT.write_text(payload_fragment(payload), encoding="utf-8")
    restore = subprocess.run(["dotnet", "tool", "restore"], cwd=ROOT)
    if restore.returncode:
        raise ValueError(f"WiX tool restore failed ({restore.returncode}).")
    result = subprocess.run(
        ["dotnet", "wix", "build", str(WIX_SOURCE), str(FRAGMENT), "-arch", "x64",
         "-d", f"ProductVersion={version}", "-bindpath", f"payload={payload}",
         "-o", str(output)], cwd=ROOT)
    if result.returncode or not output.is_file() or not output.stat().st_size:
        raise ValueError(f"MSI build failed ({result.returncode}).")
    # CLI builds do not run ICE validation. ICE91 flags intentional per-user locations.
    validation = subprocess.run(
        ["dotnet", "wix", "msi", "validate", str(output), "-sice", "ICE91"], cwd=ROOT)
    if validation.returncode:
        raise ValueError(f"MSI validation failed ({validation.returncode}).")

def package_payload(payload: Path, artifacts: tuple[Path, ...]) -> None:
    """Validate resources and archive exactly the payload supplied to the MSI."""
    required = (
        "Simplicitor.exe", "LICENSE", "prompts/system_word.txt", "prompts/system_excel.txt",
        "prompts/system_pptx.txt", "templates/pptx_default.pptx",
        "templates_engine/builtin/business_pitch/manifest.yaml",
        "templates_engine/builtin/business_pitch/template.pptx",
        "templates_engine/builtin/technical_overview/manifest.yaml",
        "templates_engine/builtin/technical_overview/template.pptx",
        "assets/icons/simplicitor.ico",
    )
    for path in (*(payload / name for name in required), *artifacts):
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
        "artifacts": {p.name: _sha256(p) for p in (*artifacts, portable)},
    }
    (DIST_DIR / "SHA256SUMS.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                             encoding="utf-8")


def main() -> int:
    """Compile the standalone payload, build its MSI, then package the same payload."""
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
    msi = DIST_DIR / f"Simplicitor-{PRODUCT_VERSION}.msi"
    outputs = (msi, DIST_DIR / "Simplicitor-portable.zip", DIST_DIR / "SHA256SUMS.json",
               DIST_DIR / "Simplicitor-setup.exe")
    for path in outputs:
        path.unlink(missing_ok=True)
    output = DIST_DIR / "standalone"
    cmd = [sys.executable, "-m", "nuitka", *NUITKA_FLAGS,
           f"--include-data-dir={notices}=third_party",
           f"--output-dir={output}", "main.py"]

    print("Building Simplicitor standalone payload ...")
    print("Command:", " ".join(str(c) for c in cmd))
    print(f"Working directory: {SIMPLICITOR_DIR}")
    print()

    result = subprocess.run(cmd, cwd=SIMPLICITOR_DIR)

    if result.returncode != 0:
        print(f"\nBuild FAILED (exit code {result.returncode})", file=sys.stderr)
        return result.returncode

    payload = output / "main.dist"
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    try:
        artifacts: tuple[Path, ...] = ()
        if shutil.which("dotnet") is not None:
            build_msi(payload, PRODUCT_VERSION, msi)
            artifacts = (msi,)
        elif in_ci:
            raise ValueError("The .NET SDK is required to build the MSI in CI.")
        else:
            print("MSI skipped: the .NET SDK is not installed. CI builds the MSI.")
        package_payload(payload, artifacts)
    except (OSError, ValueError) as exc:
        for path in outputs:
            path.unlink(missing_ok=True)
        print(f"\nPackaging FAILED: {exc}", file=sys.stderr)
        return 1
    names = [p.name for p in artifacts] + ["Simplicitor-portable.zip", "SHA256SUMS.json"]
    print(f"\nBuild complete: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
