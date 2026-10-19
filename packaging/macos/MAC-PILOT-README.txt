SIMPLICITOR: APPLE SILICON MAC PILOT

Private pilot, not a public Mac release. Needs Apple silicon, macOS 15 or later,
existing local Ollama running and your own existing installed model. No Python,
Xcode, package manager, Office or new model is required.

DOWNLOAD AND HASH CHECK

The workflow artifact is available for 14 days. Direct download requires GitHub
sign-in and repository read access. Use your browser and the exact successful run
Alex supplies. Extract its outer ZIP container to find four files:
  Simplicitor-macos-arm64-pilot.zip
  SHA256SUMS-macos-pilot.json
  macos-pilot-qualification.json
  MAC-PILOT-README.txt
There are two ZIP layers. Hash the inner pilot ZIP, not the outer artifact ZIP.

Alternative: Alex downloads the artifact and sends the unchanged pilot ZIP,
its expected hash and these instructions. Download that ZIP through your browser
to retain normal quarantine and first-launch behavior. Do not send an extracted
app, strip quarantine or use a scripted bypass. Record the route you used.

In Terminal, in the folder holding the pilot ZIP:
  shasum -a 256 Simplicitor-macos-arm64-pilot.zip
Compare all 64 characters with the artifacts entry in SHA256SUMS-macos-pilot.json
or Alex's expected hash. If different, stop. A hash match identifies bytes, not
publisher trust. Extract the inner ZIP with Finder; put Simplicitor.app in your
own ~/Applications folder.

FIRST LAUNCH

This app is ad-hoc signed and not notarized. Apple has not verified its publisher.
Double-click it in Finder and record the actual message. Unnotarized-app messages
vary; the older wording is included for reference, not support for macOS 14:
  macOS 14: "'Simplicitor' cannot be opened because Apple cannot check it for malicious software."
  macOS 15: "Apple could not verify 'Simplicitor' is free of malware that may harm your Mac or compromise your privacy."
If blocked as unnotarized
or unidentified and you choose to trust these bytes: after the attempt, go to
System Settings > Privacy & Security, scroll to Open Anyway, then confirm Open.
This is a one-time exception for this app. Apple instructions:
https://support.apple.com/en-us/102445
Stop and report only if macOS says the app "is damaged and can't be opened",
"will damage your computer" or "contains malware". Never disable Gatekeeper
globally or remove quarantine. Managed Macs may prevent the exception. Declining
it means the launch check has not passed. CI cannot prove this first-launch path.

LOCAL FOLDERS AND MODEL CHOICE

Working folders: ~/Simplicitor/Generated, ~/Simplicitor/Uploads,
~/Simplicitor/Backups, ~/Simplicitor/Logs and ~/Simplicitor/Templates.
Settings and jobs: ~/Library/Application Support/Simplicitor
Keep synthetic sources and results in a local folder outside cloud sync.
Documents and AI processing stay on your computer. This is not a network-security
audit or control over iCloud, OS backups or other sync settings.

Open Settings and select your own installed local Ollama model. Other models can
be used but are unchecked. Results depend on the model. Prior Windows Q4_K_M
results, not Mac qualification:
  Edit for Word: qwen3:8b-q4_K_M and llama3.1:8b-instruct-q4_K_M both passed,
  11/12 each (docs/evaluation/2.3.0-edit-model-check.json).
  Pull information into Excel: qwen3:8b-q4_K_M passed 272/280 (97.14%),
  zero unflagged wrong. llama3.1:8b-instruct-q4_K_M scored 262/280 (93.57%),
  failing the 95% accuracy bar (docs/evaluation/2026-10-08-task1-rerun.md).
  Whole-file extraction was then qualified on qwen3:8b only.
Do not install a model for the trial or silently substitute one after failure.
Record the actual model tag selected for each model-assisted check.

MUST-PASS NATIVE CHECKS

Alex supplies synthetic fixtures from the manifest's exact source_commit,
including tests/editing/fixtures/word-basic.docx and a synthetic extraction DOCX
or text-layer PDF. No customer documents for acceptance. Record each must-pass
case as passed, failed or not checked, with an observation and actual model tag
(null if no model was used). Record chip, RAM, macOS and actual delivery route.

1. Browser-downloaded app launches after any one-time per-app allow. Record the
   actual quarantine and Gatekeeper outcome.
2. S logo is visible in the app header.
3. Pull one synthetic DOCX or text-layer PDF into Excel: confirm columns, extract,
   review saved values/evidence, acknowledge issues when required and Save As a
   new XLSX. Check correctness in the app's saved-grid review and an existing
   viewer if available. Record the model tag.
4. Edit word-basic.docx: payment period 30 to 45 days, review before and after
   with red deletions/green additions, Use this change and Save As a new DOCX.
   Confirm the saved candidate reflects the review. Record the model tag.
5. For BOTH original sources, compare shasum -a 256 before and after. They must
   be byte-identical. Record synthetic fixture IDs and hashes, no private paths.

Every must-pass check must pass. Failed or not checked means the pilot has not
passed. Do not change the checks after failure. Hosted offscreen qualification
is a prerequisite, not a substitute for these native checks.

OPTIONAL CHECKS

Record EACH optional case as passed, failed or not checked, with an observation
and model tag when used. No time/viewer means not checked, never assumed passed.
  - Generate Word, PDF, Excel and PowerPoint; use both built-in templates.
    Try the other source format and Open file using already-installed viewers.
  - At 1280x800 and 1024x640, reach Write/Pull, acknowledgement, Save to Excel,
    Edit Review. Check header, Finder/Dock icons, fonts/focus and native scaling.
    Hosted scale emulation does not prove Retina/native behavior.
  - Finder drag/drop; Unicode paths; denied access; overwrite/original refusal;
    discard/Keep editing; cancel/close during work, each separately.
  - Open logs; disconnected startup; normal close/reopen; settings/files surviving;
    working folders staying outside sync.

FEEDBACK FROM YOUR OWN USE

After must-pass checks, try your own real work and models, locally. Send feedback
in plain words: what you tried; what worked; what failed or annoyed you; what you
wished it did. Do not send documents, contents, quotes, filenames, private paths,
real-work screenshots, logs or remote access. Record the actual model tag for a
reported check; if unknown say not recorded and do not treat it as verified.
No feedback means not provided, not an assumed positive result.

Alex records the exact source/run/artifact/ZIP hash and separate must-pass,
optional and feedback results, then decides acceptance, merge or wider testing.
This does not publish a Mac release or change the Windows release.
