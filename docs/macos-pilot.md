# Apple silicon Mac pilot

This is a private pilot, not a public Mac release. It needs an Apple silicon Mac
with macOS 14 or later, existing local Ollama running, and an existing installed
model. No Python, Xcode, Office, package manager or new model is required.
The Windows release is unchanged. Hosted checks do not prove native Mac acceptance.

## Before Alex authorizes a package

Claude reviews the qualification and packaging code first. Alex then checks the
current public-repository standard `macos-14` arm64 runner is still free and checks
the account's Actions artifact storage/billing page for free capacity for the
14-day pilot artifact. If capacity is unavailable or unclear, stop, with no paid
fallback. This check has not been performed for a package yet. See
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Verify the intended head SHA and passing Mac/Windows source jobs in draft PR #1.
Only Alex (`alexnosx`) adding `mac-package` starts a package, after that run's Mac
source tests pass. Keeping the label on a later push does not rebuild it. After a
failed package, stop and report; removing/re-adding the label needs fresh approval.
No label, packaging run or native trial is authorized by these instructions alone.

## Download and check the exact bytes

The workflow artifact is available for **14 days**. GitHub sign-in and repository
read access are required for the direct download. Download the artifact through
your browser from the exact successful run Alex supplies. Extract the outer ZIP
container. Inside are four files: `Simplicitor-macos-arm64-pilot.zip`,
`SHA256SUMS-macos-pilot.json`, `macos-pilot-qualification.json` and
`MAC-PILOT-README.txt`. There are two ZIP layers: do not mistake the outer workflow
container for the inner pilot ZIP whose hash is recorded.

Alternative: Alex downloads the artifact and sends the **unchanged pilot ZIP**,
its expected SHA-256 and these instructions. Download that ZIP through your browser
so normal quarantine and first-launch behavior apply. Do not send an extracted
app or strip quarantine. Record which delivery route you actually used.

Before extracting the inner ZIP, run this in Terminal in its download folder:

```sh
shasum -a 256 Simplicitor-macos-arm64-pilot.zip
```

Compare all 64 characters with `artifacts` in `SHA256SUMS-macos-pilot.json`, or the
expected hash Alex supplied. A mismatch means stop. A matching hash identifies
the delivered bytes; it does not establish publisher trust. Extract the inner ZIP
with Finder and move `Simplicitor.app` to your own `~/Applications` folder.

## First launch

The app is **ad-hoc signed and not notarized**. It has no Apple-verified publisher
identity. Double-click it in Finder and record the actual message. If it is blocked
as unnotarized or unidentified and you choose to trust these bytes, use the
one-time per-app exception: after trying to open it, open System Settings,
Privacy & Security, scroll to **Open Anyway**, then confirm **Open** when asked.
See [Apple's instructions](https://support.apple.com/en-us/102445). Do not override
a malware/damaged-app warning; stop and report it. Never disable Gatekeeper
globally, remove quarantine or run a scripted bypass. A managed Mac may disallow
the exception. Declining it is fine, but the launch check has not passed.

## Local folders and models

Working folders are `~/Simplicitor/Generated`, `~/Simplicitor/Uploads`,
`~/Simplicitor/Backups`, `~/Simplicitor/Logs` and `~/Simplicitor/Templates`.
Settings and jobs use `~/Library/Application Support/Simplicitor`.
Use a local, non-synced folder for synthetic source copies and saved results.
Documents and AI processing stay on the computer; this is not a network-security
audit or a guarantee about your OS backups, iCloud or other sync settings.

Open Settings and choose your own installed local Ollama model. Other models can
be used but are **unchecked**. Results depend on the model. These Q4_K_M results
are prior **Windows** results, **not Mac qualification**:

- Edit for Word: `qwen3:8b-q4_K_M` and `llama3.1:8b-instruct-q4_K_M` both passed,
  **11/12 each**. [Recorded edit check](evaluation/2.3.0-edit-model-check.json).
- Pull information into Excel: `qwen3:8b-q4_K_M` passed **272/280 (97.14%)** with
  **zero unflagged wrong**; `llama3.1:8b-instruct-q4_K_M` scored **262/280 (93.57%)**
  and failed the **95%** accuracy bar. Whole-file extraction was then qualified on
  `qwen3:8b` only. [Recorded extraction check](evaluation/2026-10-08-task1-rerun.md).

Do not install a model for this trial or silently substitute another model if
yours fails. Record the exact model tag actually selected for each model-assisted
check, not a recommended tag copied from this page.

## Must-pass native checks

Alex supplies synthetic fixtures from the exact `source_commit` in the manifest,
including `tests/editing/fixtures/word-basic.docx` and a synthetic extraction DOCX
or text-layer PDF. Do not use customer documents for acceptance.
Record each must-pass result as `passed`, `failed` or `not checked`, with a short
observation and actual model tag (null if no model was used).

1. First launch after browser download and any one-time allow succeeds. Record
   the download route, quarantine/first-launch outcome, chip, RAM and macOS version.
2. The S logo is visible in the app header.
3. Pull information into Excel from one synthetic DOCX or text-layer PDF: confirm
   columns, extract, review saved values/evidence, acknowledge issues if required,
   Save As a new XLSX. Confirm the saved result is correct using the app review and
   an existing viewer if available. Record the model tag.
4. Edit the synthetic Word fixture's payment period from 30 to 45 days. Review
   before/after, red deletions and green additions, Use this change, Save As a new
   DOCX. Confirm it reflects the reviewed change. Record the model tag.
5. Hash both original inputs before and after with `shasum -a 256`. Both must be
   byte-identical. Report synthetic fixture IDs and hashes, not private filenames.

All must-pass checks must be `passed`. A failed or not checked item means the
pilot has not passed. Hosted offscreen qualification is a prerequisite, not a
substitute. Do not change the checks after a failure.

## Optional checks and feedback

Record each optional case separately as `passed`, `failed` or `not checked` with
an observation and actual model tag when used. No time or suitable viewer means
not checked, never an assumed pass:

- Create Word, PDF, Excel and PowerPoint; use both built-in PowerPoint templates.
  Try the other source format and Open file in an already-installed viewer.
- At 1280x800 and 1024x640, reach Write, Pull, acknowledgement, Save to Excel and
  Edit Review. Check Finder/Dock icons, header, fonts, focus and native scaling.
- Finder drag/drop; Unicode paths; denied access; overwrite and original-file
  refusal; discard/Keep editing; cancel and close during work, each separately.
- Open logs; disconnected startup; normal close/reopen; settings/files surviving;
  working folders outside sync. Hosted scale emulation does not prove Retina use.

After must-pass checks, try your own real work and models locally. Send feedback
in plain words: what you tried, what worked, what failed or annoyed you, and what
you wished it did. Do not send documents, contents, quotes, filenames, private
paths, real-work screenshots, logs or remote access. Record the actual model tag
for any reported check; if unknown say not recorded and do not call it verified.
No feedback is `not provided`, not an assumed positive result.

The later native record belongs in `docs/builds/macos-arm64-pilot-native.json`,
with exact source/run/artifact/ZIP identity, separate must-pass and optional
results and feedback. Alex decides acceptance, merge or wider testing. Nothing
here publishes a Mac release or changes the Windows release.
