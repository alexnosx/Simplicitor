# Phase 6: Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a single `Simplicitor.exe` that runs on a clean Windows 10/11 machine with no Python installed.

**Architecture:** Nuitka `--onefile` compiles the entire app into a self-extracting archive. At runtime it extracts to a temp dir, which mirrors the source layout so all `Path(__file__)` calculations still resolve correctly. The `prompts/` directory is bundled via `--include-data-dir`. Build tooling lives at the repo root; the distributable lands in `dist/`.

**Tech Stack:** Nuitka 2.x, Python 3.11+, PySide6, `ordered-set`, `zstandard`

---

## Path-resolution compatibility note

`generate_worker.py` and `manipulate_worker.py` resolve prompts using:
```python
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"
```
In Nuitka onefile the extraction root is `<tmp>/onefile_XXXXX/`. `__file__` for `app/workers/generate_worker.py` is `<tmp>/onefile_XXXXX/app/workers/generate_worker.py`, so `.parent.parent.parent` lands at `<tmp>/onefile_XXXXX/` — exactly where Nuitka extracts the bundled `prompts/` dir. **No code changes needed.**

## File Structure

**New:**
- `resources/` — new directory
- `resources/create_icon.py` — pure-Python ICO generator (no Pillow dep)
- `resources/icon.ico` — generated 32×32 app icon (Simplicitor blue)
- `requirements-build.txt` — Nuitka + compression deps
- `build.py` — Python build script (canonical, source of truth for flags)
- `build.bat` — Windows convenience wrapper that calls `build.py`
- `README.md` — user-facing documentation (repo root)
- `docs/code-signing.md` — code signing process documentation

**Not modified:** any source file under `simplicitor/` — zero runtime changes.

---

## Task 1: App icon

**Files:**
- Create: `resources/create_icon.py`
- Generate: `resources/icon.ico`

- [ ] **Step 1: Create the icon generator**

Create `resources/create_icon.py`:

```python
#!/usr/bin/env python3
"""
Generate resources/icon.ico — a 32×32 solid Simplicitor-blue (#2563EB) icon.

No third-party dependencies. Run:  python resources/create_icon.py
"""
import struct
from pathlib import Path

# Simplicitor primary accent: #2563EB  →  R=37, G=99, B=235
_R, _G, _B, _A = 37, 99, 235, 255


def _make_ico(size: int) -> bytes:
    """Return raw bytes for a single solid-colour ICO image at `size` × `size`."""
    # BGRA pixel data (ICO uses BGRA order)
    pixels = bytes([_B, _G, _R, _A]) * size * size

    # BITMAPINFOHEADER (40 bytes) — height doubled in ICO format
    bmi = struct.pack(
        "<IIIHHIIIIII",
        40,        # biSize
        size,      # biWidth
        size * 2,  # biHeight (×2 = XOR + AND bitmaps stacked)
        1,         # biPlanes
        32,        # biBitCount (32-bit BGRA)
        0,         # biCompression (BI_RGB)
        0,         # biSizeImage
        0,         # biXPelsPerMeter
        0,         # biYPelsPerMeter
        0,         # biClrUsed
        0,         # biClrImportant
    )

    # AND mask: 1 bit/pixel, rows padded to DWORD boundary
    # For 32-bit images Windows ignores the AND mask if alpha=0xFF, but we
    # must include it. Row width in bits = size, padded to 32 bits.
    row_bytes = ((size + 31) // 32) * 4
    and_mask = b"\x00" * (row_bytes * size)

    return bmi + pixels + and_mask


def create_icon(output_path: Path) -> None:
    """Write a multi-size ICO (16×16, 32×32) to *output_path*."""
    sizes = [16, 32]
    images = [_make_ico(s) for s in sizes]

    # ICONDIR header: reserved=0, type=1 (ICO), count
    icon_dir = struct.pack("<HHH", 0, 1, len(sizes))

    # ICONDIRENTRY for each image; offset starts after ICONDIR + all entries
    entry_size = 16
    data_offset = 6 + entry_size * len(sizes)
    entries = b""
    for i, (size, image) in enumerate(zip(sizes, images)):
        w = h = size if size < 256 else 0  # 256 encoded as 0 in ICO spec
        entries += struct.pack(
            "<BBBBHHII",
            w, h,           # width, height
            0,              # colorCount (0 = no palette)
            0,              # reserved
            1,              # planes
            32,             # bitCount
            len(image),     # bytesInRes
            data_offset,    # imageOffset
        )
        data_offset += len(image)

    output_path.write_bytes(icon_dir + entries + b"".join(images))
    print(f"Icon written: {output_path}  ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    out = Path(__file__).parent / "icon.ico"
    create_icon(out)
```

- [ ] **Step 2: Run the generator and verify the output**

```
cd C:\Repos\Simplicitor
python resources/create_icon.py
```

Expected output:
```
Icon written: C:\Repos\Simplicitor\resources\icon.ico  (XXXX bytes)
```

Then verify it is a valid ICO:
```
python -c "
from pathlib import Path
data = Path('resources/icon.ico').read_bytes()
assert data[2:4] == b'\x01\x00', 'not a valid ICO file'
assert data[4:6] == b'\x02\x00', 'expected 2 images (16, 32)'
print('ICO OK:', len(data), 'bytes')
"
```

Expected: `ICO OK: <number> bytes`

- [ ] **Step 3: Commit**

```bash
git add resources/create_icon.py resources/icon.ico
git commit -m "feat: add app icon (32x32 Simplicitor blue ICO)"
```

---

## Task 2: Build requirements file

**Files:**
- Create: `requirements-build.txt`

- [ ] **Step 1: Create the file**

Create `requirements-build.txt` at the repo root:

```
# Build-time dependencies — not needed to run Simplicitor
# Install with: pip install -r requirements-build.txt

nuitka>=2.0
ordered-set>=4.1.0
zstandard>=0.21.0
```

`ordered-set` and `zstandard` are required by Nuitka's onefile compression. `nuitka` itself is the compiler.

- [ ] **Step 2: Verify it is parseable by pip**

```
pip install --dry-run -r requirements-build.txt
```

Expected: no errors (packages may already be installed).

- [ ] **Step 3: Commit**

```bash
git add requirements-build.txt
git commit -m "chore: add requirements-build.txt for Nuitka packaging"
```

---

## Task 3: Build script

**Files:**
- Create: `build.py`
- Create: `build.bat`

The canonical list of Nuitka flags lives in `build.py`. `build.bat` is a one-liner that delegates to `build.py`.

- [ ] **Step 1: Write a test that verifies the required Nuitka flags are present**

Create `tests/test_build_script.py`:

```python
# tests/test_build_script.py
"""Smoke tests for the Nuitka build script — verify required flags are present."""
from pathlib import Path


BUILD_PY = Path(__file__).parent.parent / "build.py"


def _content() -> str:
    return BUILD_PY.read_text(encoding="utf-8")


def test_build_script_exists() -> None:
    assert BUILD_PY.exists(), "build.py not found at repo root"


def test_build_script_uses_onefile() -> None:
    assert "--onefile" in _content()


def test_build_script_disables_console() -> None:
    # Nuitka 2.x flag
    assert "--windows-console-mode=disable" in _content()


def test_build_script_enables_pyside6_plugin() -> None:
    assert "--enable-plugin=pyside6" in _content()


def test_build_script_includes_prompts_dir() -> None:
    assert "prompts=prompts" in _content()


def test_build_script_references_icon() -> None:
    assert "icon.ico" in _content()


def test_build_script_sets_product_name() -> None:
    assert "Simplicitor" in _content()


def test_build_bat_exists() -> None:
    bat = Path(__file__).parent.parent / "build.bat"
    assert bat.exists(), "build.bat not found at repo root"
```

- [ ] **Step 2: Run to verify they fail**

```
cd C:\Repos\Simplicitor\simplicitor
python -m pytest ../tests/test_build_script.py -v
```

Expected: most tests FAIL (files don't exist yet).

- [ ] **Step 3: Create `build.py`**

Create `build.py` at the repo root:

```python
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
RESOURCES_DIR = ROOT / "resources"
DIST_DIR = ROOT / "dist"
ICON = RESOURCES_DIR / "icon.ico"

# ---------------------------------------------------------------------------
# Nuitka flags
# ---------------------------------------------------------------------------
NUITKA_FLAGS = [
    "--onefile",
    "--windows-console-mode=disable",
    "--enable-plugin=pyside6",
    # Bundle the prompts/ directory so the app can read system prompts at runtime.
    # Source path is relative to the build working directory (simplicitor/).
    "--include-data-dir=prompts=prompts",
    f"--windows-icon-from-ico={ICON}",
    "--windows-product-name=Simplicitor",
    "--windows-product-version=1.0.0.0",
    "--windows-company-name=Simplicitor",
    "--windows-file-description=AI-powered Office document generator",
    f"--output-dir={DIST_DIR}",
    "--output-filename=Simplicitor",
]


def main() -> int:
    if not ICON.exists():
        print(
            f"ERROR: icon not found at {ICON}\n"
            "Run:  python resources/create_icon.py",
            file=sys.stderr,
        )
        return 1

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "nuitka", *NUITKA_FLAGS, "main.py"]

    print("Building Simplicitor.exe …")
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
```

- [ ] **Step 4: Create `build.bat`**

Create `build.bat` at the repo root:

```bat
@echo off
REM Simplicitor build script (Windows convenience wrapper).
REM Run from the repository root.  Requires Python and Nuitka:
REM     pip install -r requirements-build.txt

python "%~dp0build.py" %*
```

- [ ] **Step 5: Run the tests**

```
cd C:\Repos\Simplicitor\simplicitor
python -m pytest ../tests/test_build_script.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Verify build.py is syntactically valid Python**

```
python -m py_compile build.py && echo "OK"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add build.py build.bat tests/test_build_script.py
git commit -m "feat: add Nuitka build script for onefile Windows exe"
```

---

## Task 4: README.md

**Files:**
- Create: `README.md` (repo root)

No unit tests — manual review against the implementation guide checklist.

- [ ] **Step 1: Create `README.md`**

Create `README.md` at the repo root:

```markdown
# Simplicitor

Generate and edit Word, Excel, and PowerPoint files using plain English — powered by a locally running AI.

No cloud. No subscription. No data leaves your machine.

## Requirements

- **Windows 10 or 11** (64-bit)
- **[Ollama](https://ollama.com)** installed and running on your machine
- At least one language model loaded in Ollama (see recommendations below)

## Installation

1. Download `Simplicitor.exe` from the [Releases](../../releases) page
2. Double-click `Simplicitor.exe` — no installation or Python required

## Recommended Models

For best results use a model with **7 billion parameters or more**:

| Model | Download size | Ollama command |
|---|---|---|
| Qwen3 8B | ~5 GB | `ollama pull qwen3:8b` |
| Llama 3.1 8B | ~4.7 GB | `ollama pull llama3.1:8b` |
| Mistral 7B | ~4 GB | `ollama pull mistral:7b` |

Smaller models work for simple requests but may struggle with complex documents.

## Quick Start

### 1. Start Ollama

Open a terminal (Win+R → `cmd`) and run:

```
ollama serve
```

Then in another terminal, load your model:

```
ollama run qwen3:8b
```

### 2. Launch Simplicitor

Double-click `Simplicitor.exe`. The status dot in the top bar turns **green** when the AI is ready.

### Create a new document

1. Select a file type: **Word**, **Excel**, or **PowerPoint**
2. Choose where to save it (defaults to `Documents\Simplicitor\Generated`)
3. Describe what you need in the text box
4. Click **Generate** — the file is saved automatically and an **Open file** button appears

### Edit an existing document

1. Drag a `.docx`, `.xlsx`, `.pptx`, `.txt`, or `.pdf` file into the Edit panel (or click to browse)
2. Describe the change you want
3. Click **Save** — a backup of the original is created automatically in `Documents\Simplicitor\Backups`

## Troubleshooting

**"AI engine not connected" (red indicator)**
- Make sure Ollama is running: open a terminal and run `ollama serve`
- Click the **Retry** button in the app

**Generation produces empty or garbled output**
- Try a shorter, simpler prompt
- Use a larger model (7B+ recommended)
- Check the logs: Settings → View Logs Folder

**"Cannot create the output folder" error**
- Open Settings (⚙ gear icon) and verify the "Generated files" path is valid
- Make sure you have write permission to that folder

**The generated file looks wrong (missing formatting, wrong structure)**
- The AI controls content; Simplicitor handles formatting
- Try adding more detail to your prompt
- Upgrade to a larger model

## Settings

Click the **⚙** gear icon (top right) to configure:

| Setting | Default location |
|---|---|
| Generated files | `Documents\Simplicitor\Generated` |
| Uploaded files | `Documents\Simplicitor\Uploads` |
| Backups | `Documents\Simplicitor\Backups` |
| Logs | `Documents\Simplicitor\Logs` |

Click **View Logs Folder** to open the log directory in Explorer.  
Click **Reset to Defaults** to restore all paths to their defaults.

## Building from Source

Requirements: Python 3.11+, Git

```bat
git clone <repo-url>
cd Simplicitor
pip install -r requirements.txt
pip install -r requirements-build.txt
python resources/create_icon.py
python build.py
```

The compiled executable will be at `dist\Simplicitor.exe`.

## Privacy

Simplicitor sends your prompts only to the Ollama instance running on your own machine. No data is sent to any external server. Log files contain operation metadata (timestamps, file types, success/error status) but never file content or prompt text.
```

- [ ] **Step 2: Verify the required sections are present**

```
python -c "
content = open('README.md').read()
required = [
    'Requirements', 'Installation', 'Recommended Models',
    'Troubleshooting', 'ollama', 'Qwen', 'Building from Source', 'Privacy'
]
missing = [s for s in required if s not in content]
if missing:
    print('MISSING sections:', missing)
else:
    print('README OK — all required sections present')
"
```

Expected: `README OK — all required sections present`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation, usage, and troubleshooting"
```

---

## Task 5: Code signing documentation

**Files:**
- Create: `docs/code-signing.md`

- [ ] **Step 1: Create `docs/code-signing.md`**

Create `docs/code-signing.md`:

```markdown
# Code Signing Simplicitor.exe

Unsigned executables trigger Windows SmartScreen ("Windows protected your PC") and may be quarantined by antivirus software. Code signing eliminates these warnings for end users.

## Certificate Type

Purchase an **EV (Extended Validation) code signing certificate**. Standard OV (Organization Validation) certificates no longer suppress SmartScreen automatically as of Windows 11 23H2.

Recommended certificate authorities (prices approximate):

| CA | URL | Price/year |
|---|---|---|
| DigiCert | https://www.digicert.com | ~$500 |
| Sectigo | https://www.sectigo.com | ~$400 |
| GlobalSign | https://www.globalsign.com | ~$450 |

EV certificates require identity verification (1-5 business days) and are delivered on a hardware USB token.

## Prerequisites

- Windows SDK installed (includes `signtool.exe`)
- EV certificate installed from the USB token

## Sign the Executable

After building `dist\Simplicitor.exe`:

```bat
signtool sign ^
  /tr http://timestamp.digicert.com ^
  /td sha256 ^
  /fd sha256 ^
  /a ^
  dist\Simplicitor.exe
```

| Flag | Meaning |
|---|---|
| `/tr` | RFC 3161 timestamp server URL (keeps signature valid after cert expiry) |
| `/td sha256` | Timestamp digest algorithm |
| `/fd sha256` | File digest algorithm |
| `/a` | Auto-select best certificate from the store |

## Verify the Signature

```bat
signtool verify /pa dist\Simplicitor.exe
```

Expected output: `Successfully verified: dist\Simplicitor.exe`

## Full Build + Sign Workflow

```bat
REM 1. Build
python build.py

REM 2. Sign
signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist\Simplicitor.exe

REM 3. Verify
signtool verify /pa dist\Simplicitor.exe

REM 4. Distribute dist\Simplicitor.exe
```

## AV Vendor Submission

Even signed executables may trigger false positives on first release. Submit `dist\Simplicitor.exe` to major vendors:

| Vendor | Submission URL |
|---|---|
| Microsoft Defender | https://www.microsoft.com/en-us/wdsi/filesubmission |
| Kaspersky | https://opentip.kaspersky.com |
| ESET | https://www.eset.com/int/about/virus-lab/ |
| Bitdefender | https://www.bitdefender.com/submit |
| Avast | https://www.avast.com/false-positive-file-form.php |

Allow 1–5 business days per vendor. Repeat with each new release.

## Startup Time

Target: under 3 seconds on a modern machine.

Nuitka onefile extracts to a temp directory on first run. Subsequent runs reuse the extraction if the exe has not changed. If startup is slow, consider `--onefile-tempdir-spec="{CACHE_DIR}/{PRODUCT}/{VERSION}"` in the build script to persist the extraction across runs.
```

- [ ] **Step 2: Commit**

```bash
git add docs/code-signing.md
git commit -m "docs: add code signing process documentation"
```

---

## Task 6: Full test suite + build smoke test

- [ ] **Step 1: Run the complete test suite**

```
cd C:\Repos\Simplicitor\simplicitor
python -m pytest ../tests/ -v --tb=short 2>&1 | tail -10
```

Expected: all tests pass (≥323 + 8 new = 331+).

- [ ] **Step 2: Verify the build script can be invoked (pre-flight check)**

This checks that all flags are well-formed, the icon exists, and the output dir can be created — without actually running Nuitka:

```
cd C:\Repos\Simplicitor
python -c "
import build
from pathlib import Path

# icon must exist
assert build.ICON.exists(), f'icon missing: {build.ICON}'

# SIMPLICITOR_DIR must contain main.py
assert (build.SIMPLICITOR_DIR / 'main.py').exists(), 'main.py not found'

# prompts dir must exist
assert (build.SIMPLICITOR_DIR / 'prompts').is_dir(), 'prompts/ not found'

print('Pre-flight OK')
print('  Icon:', build.ICON)
print('  Entry point:', build.SIMPLICITOR_DIR / 'main.py')
print('  Prompts:', build.SIMPLICITOR_DIR / 'prompts')
print()
print('To build the exe, run:')
print('  pip install -r requirements-build.txt')
print('  python build.py')
"
```

Expected:
```
Pre-flight OK
  Icon: C:\Repos\Simplicitor\resources\icon.ico
  Entry point: C:\Repos\Simplicitor\simplicitor\main.py
  Prompts: C:\Repos\Simplicitor\simplicitor\prompts
```

- [ ] **Step 3: Commit anything remaining**

```bash
git status
# commit any untracked files if needed
```

---

## Manual verification checklist (after running `python build.py`)

These steps require Nuitka installed and are run manually — they cannot be automated in CI without a real build environment:

- [ ] `dist\Simplicitor.exe` exists and is under 150 MB
- [ ] Double-click `dist\Simplicitor.exe` on the build machine — app launches within 5 seconds
- [ ] With Ollama running: green dot, model name shown, Generate and Save buttons work end-to-end
- [ ] Without Ollama: red dot, friendly "not connected" message, Retry button works
- [ ] Copy `dist\Simplicitor.exe` to a machine with no Python or PySide6 — still works
- [ ] Windows Defender does not quarantine the file (expected with EV cert; may warn without one)

---

## Self-Review

**Spec coverage:**

| Implementation guide task | Covered by |
|---|---|
| Nuitka build script (standalone, onefile, disable console, pyside6 plugin) | Task 3 (build.py) |
| Include prompts/ as data | Task 3 (`--include-data-dir=prompts=prompts`) |
| Set application icon | Tasks 1 + 3 |
| Set version metadata (product name, version, company) | Task 3 |
| Measure executable size (target 50–80 MB) | Manual checklist |
| Test on clean Windows VM | Manual checklist |
| Test with Windows Defender | Manual checklist |
| Code signing documentation | Task 5 |
| README.md | Task 4 |

**Placeholder scan:** No TBD or "implement later" found.

**Type consistency:** `build.ICON`, `build.SIMPLICITOR_DIR`, `build.DIST_DIR`, `build.NUITKA_FLAGS` — used consistently in Task 3 and the pre-flight check in Task 6.
