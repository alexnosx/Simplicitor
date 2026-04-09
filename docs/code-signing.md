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

EV certificates require identity verification (1–5 business days) and are delivered on a hardware USB token.

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

Nuitka onefile extracts to a temp directory on first run. Subsequent runs reuse the extraction if the exe has not changed. If startup is slow, consider adding this flag to `build.py`:

```python
"--onefile-tempdir-spec={CACHE_DIR}/{PRODUCT}/{VERSION}",
```

This persists the extraction across runs and eliminates the extraction overhead after first launch.
