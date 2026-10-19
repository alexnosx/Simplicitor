# Apple Silicon Mac Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. No execution method is selected or authorized by this draft.

**Status:** Draft 2, revised on 2026-10-18 after Claude's review of `0f2fce2`. Alex authorized this plan revision, commit and push to main. Implementation, branch/PR creation, workflow execution, merging and distribution await his approval.

**Goal:** Give one Apple silicon Mac user a self-contained Simplicitor pilot, retaining the current document workflows and spending nothing on certificates, services or build infrastructure.

**Architecture:** Keep the Python/PySide6 app, Ollama client, workers and document engines. Make small desktop/path/font adaptations, and add a separate Nuitka Mac build and draft-PR source-check workflow on the feature branch. Alex's PR label gates packaging. Deliver an ad-hoc-signed `Simplicitor.app` in a ZIP; qualify it on the runner and then on the colleague's actual Mac. No workflow bootstrap or implementation lands on main before review.

**Tech Stack:** Existing Python 3.11, PySide6 6.11.2, Nuitka 4.2.2 and document libraries; Qt desktop services; macOS `codesign`, `ditto`, `lipo` and `otool`; standard GitHub-hosted arm64 runner.

**Spec:** Alex's request for a free Apple silicon pilot, the existing [PRD](../../../PRD.md), [architecture](../specs/2026-10-08-document-architecture-design.md), [UI design](../specs/2026-10-08-document-workspace-ui-design.md), [Word preservation design](../specs/2026-10-13-edit-for-word-design.md), and [packaging policy](../../code-signing.md). This proposal adds a pilot platform, not a new document workflow. The Windows-only product scope stays in force until execution is approved and the pilot passes.

**Inspected baseline:** Main at `f565f573e5886f7af76891b17a22b6589f040cf5`, with product version 2.5.1. The recorded Windows suite has 1,395 tests. No Mac run has been performed; this is not a claim that 1,395 tests pass on macOS.

## Changes from draft 1

1. Keep the artifact for 14 days. Explain GitHub sign-in and Alex's alternative of sending the pilot ZIP for a browser download.
2. Open the feature branch's draft PR during Task 0. Use `pull_request` source checks and an Alex-added `mac-package` label for packaging, without a default-branch bootstrap or dispatch input.
3. Separate Task 5's must-pass native checks from optional checks. Record every optional result as passed, failed or not checked.
4. Put Darwin settings/jobs in `~/Library/Application Support/Simplicitor` through `get_app_data_dir()`, retaining `~/Simplicitor` working folders and Windows behavior.
5. Document the recorded Q4_K_M model results by workflow, record the actual model tag per native check, and collect plain-language feedback from the pilot user's own use without document contents or filenames.

## Global constraints

- Apple silicon only. Target macOS 15 or later; qualify only the OS versions actually tested. Alex approved the 15.0 minimum on 2026-10-19 after the bundled PySide6/shiboken6 arm64 binaries were measured at minos 15.0 and he confirmed the colleague uses macOS 15 or newer. No Intel build, Rosetta dependency, universal-app project or App Store work.
- No paid certificate, Apple Developer subscription, notarization, paid runner or new dependency. Ad-hoc signing is free and required by this build route; it establishes bundle integrity, not a verified publisher or Gatekeeper trust.
- No cloud model, remote Ollama endpoint, telemetry, cloud fallback or bundled/downloaded model. Keep existing prompts, options, profiles, grounding, evidence and model-size warning.
- Preserve document patch/verification/save rules, source protection, cancellations, stale-result handling, worker retirement and legacy Edit disabling. A defect requiring an engine change stops the pilot for a separate decision.
- No version bump. Read `version.py`; distinguish the pilot by its artifact name, source commit and evidence. Do not tag, create a GitHub Release, add Mac assets to v2.5.1 or change its release records.
- Leave `build.py`, `.github/workflows/build.yml`, the MSI route, current Windows defaults, LICENSE and existing release artifacts unchanged. Reuse their data/notice conventions without redesigning the Windows builder.
- Future app branch: `codex/macos-apple-silicon-pilot`. No branch is created by writing this plan. No app merge into main before the native pilot result and Alex's approval.
- On Alex's PC: existing source tests and synthetic captures only. No build script, installer, uninstaller, msiexec, Sandbox, WiX, qualification script or tool/dependency installation. Download/hash a Mac artifact only; do not unpack or run it here.
- Mac builds, dependency installation and automated qualification run only on GitHub's disposable Mac runner. The colleague performs native checks on their own Mac, with their consent. No remote access is assumed.
- Use synthetic fixtures for automated and formal native checks. After the must-pass checks, the colleague may use their own documents privately on their own Mac and describe their experience. Collect no documents, contents, prompts, responses, filenames or private paths in reports/logs; the feedback is a manual account, not telemetry.

## Pilot decisions

| Decision | Proposed implementation |
|---|---|
| Build host | Standard `macos-15` packaging runner, Python 3.11 arm64, with runtime assertions for Darwin, arm64 and macOS 15. Source tests stay on `macos-14`. Recheck availability before execution; never substitute a paid `-large`/`-xlarge` runner. |
| Cost | The repository was confirmed PUBLIC on 2026-10-18. Standard public-repository runners are free. Check available free artifact storage before Alex adds the packaging label; retain only final outputs for 14 days. If zero-cost execution cannot be confirmed, stop. Do not enable billing or change account settings. |
| Distribution | One workflow artifact containing `Simplicitor-macos-arm64-pilot.zip`, `SHA256SUMS-macos-pilot.json`, `macos-pilot-qualification.json` and `MAC-PILOT-README.txt`. The inner ZIP contains `Simplicitor.app` at its root. Downloading a workflow artifact requires GitHub sign-in and repository read access. Alternatively, Alex downloads the artifact and sends the unchanged pilot ZIP, its expected hash and instructions to the colleague, who downloads the ZIP through their browser. |
| Signing | Explicit Nuitka `--macos-sign-identity=ad-hoc`. No signing secret, identity auto-detection, Apple account credential or notarization call. Verify the final signature after ZIP round-trip. |
| First launch | State plainly that macOS may block this unidentified, unnotarized app. The user may choose Apple's per-app Open Anyway procedure. Never remove quarantine, disable Gatekeeper, request blanket Full Disk Access or work around managed-device policy. A blocked/declined first launch is a failed native gate, not a passing pilot. |
| Settings/jobs | On Darwin only, `get_app_data_dir()` returns `~/Library/Application Support/Simplicitor`, even if APPDATA is set. Settings and jobs share this root. There are no existing Mac users, so do not migrate or use `~/.simplicitor` on Darwin. Windows APPDATA resolution and other platforms' fallback stay unchanged; no settings schema change. |
| New Mac working folders | Default to `~/Simplicitor/{Generated,Uploads,Backups,Logs,Templates}`, outside the usual Desktop/Documents iCloud sync locations. Preserve saved custom paths. Explicitly tell the pilot user to use folders not managed by any sync provider; no automatic cloud-folder detector or guarantee about OS backup/sync. |
| Appearance | Keep the Azure layout, actual S and wording. Use `Helvetica Neue` on Darwin, Segoe UI elsewhere, retaining 11 pt minimum body text. No Mac redesign. |
| Compatibility claim | No Office installation required. Existing OOXML/PDF behavior is retained; no new Pages, Numbers, Keynote or PDF-editing claim. |
| Models | The pilot user is a real target user and local-LLM enthusiast, using their own installed models. The instructions give the recorded Q4_K_M results by workflow from Task 4: both models passed Edit for Word; only Qwen passed Pull's accuracy bar, and whole-file extraction was then qualified on Qwen only. These are prior Windows results, not Mac qualification. Other models can be used but are unchecked. Record the actual tag used per native check. |

## Review focus

1. A browser-downloaded, quarantined app must be judged separately from an unquarantined CI launch. Task 5 owns the native first-launch gate.
2. Spaces, Unicode, a changed working directory and `.app` resource locations must not break the S, prompts or either built-in template. Tasks 2, 3 and 4 own these checks.
3. Mac fonts and Qt metrics must keep PDF text readable and the header, review acknowledgement and Save actions reachable. Tasks 2 and 5 own the source/native checks.
4. Settings must survive subsequent launches at the new Darwin data root; Mac working defaults must not silently use iCloud Documents or modify Windows defaults. Tasks 1 and 4 own the tests. There is no existing Mac settings migration.
5. Mac filesystem aliases and denied access must not bypass original-file protection or turn failed saving into success. Tasks 2 and 5 exercise existing guards; they do not rewrite them.

## Files and responsibilities

| Files | Responsibility |
|---|---|
| New `.github/workflows/macos-pilot.yml` | Source checks from the pilot branch's draft PR and, later, Alex-label-gated packaging. No default-branch bootstrap, dispatch input, release permissions or tag/push trigger. |
| New `simplicitor/app/utils/desktop.py` | One Qt-based file/folder opening helper. |
| `simplicitor/app/widgets/create_screen.py`, `settings_dialog.py` | Use that helper for the existing active desktop actions. |
| `simplicitor/app/config/settings.py`, `defaults.py` | Darwin-only default working root and font selection. |
| `simplicitor/templates_engine/config.py`, `tests/templates_engine/test_config.py` | Darwin Application Support settings/jobs root through `get_app_data_dir()`, with Windows APPDATA and other-platform fallback regressions. |
| `tests/conftest.py`, `scripts/capture_screens.py` | Mac-safe font/profile isolation, preserving Windows behavior. |
| New `build_macos.py` | Bundle with existing Nuitka/data/notice inputs; ad-hoc sign; create the Mac ZIP and hashes. |
| `scripts/build_third_party_notices.py` | Locate the installed Python license on either host, retaining current Windows output. |
| New `scripts/qualify_macos_pilot.py` | Hosted-runner-only bundle, signature, architecture and offline-startup qualification. |
| New `tests/test_desktop.py`, `test_macos_pilot_workflow.py`, `test_macos_build.py`, `test_macos_qualification.py`, `test_macos_compatibility.py`; existing settings/resource/notice/widget tests | Focused regressions and mocked packaging. No external tools run in the Windows source suite. |
| New `docs/macos-pilot.md`, `packaging/macos/MAC-PILOT-README.txt`; later `docs/builds/macos-arm64-pilot-ci.json`, `macos-arm64-pilot-native.json` | Pilot instructions, exact build identity and separately recorded hosted/native results. |

## Testing and execution policy

- For each implementation task: write new regression tests, observe the relevant failure, implement the minimum change, run targeted tests and the isolated full Windows suite. Do not manufacture a red result for existing behavior: resource and preservation conformance tests may already pass.
- Local full-suite command remains `.venv/Scripts/python.exe -m pytest -q --basetemp .venv/pytest-tmp`, with USERPROFILE, APPDATA and LOCALAPPDATA redirected under `.venv/test-home`. Never modify, skip or weaken a business assertion to obtain a pass. Record actual counts, not predicted totals.
- Hosted Mac source checks use Python 3.11, `QT_QPA_PLATFORM=offscreen`, an isolated HOME and corresponding test profile variables under RUNNER_TEMP, and `python -m pytest -vv -o faulthandler_timeout=60 --basetemp "$RUNNER_TEMP/simplicitor-pytest"`. Test-job timeout: 15 minutes. No real Ollama or model download.
- A failure or freeze is recorded with its log. No blind retries. A packaging/platform defect gets a bounded correction and rerun after review; a document-engine defect, missing dependency or required paid service stops for Alex's decision.
- Mac source checks run on the pilot draft PR's `opened`, `reopened`, `synchronize` and `labeled` events. Task 0 records the baseline; Task 2 records passing platform suites. The full Mac package runs only at Task 4 when Alex adds `mac-package`, after reviewing the current head and source checks. A retained label does not rebuild on later pushes. Any approved package rerun needs Alex to remove and re-add the label after review; no full Mac build per commit or automatic retry.
- Proposed commits below require execution/commit/push authorization. Update REPO_MAP after file/signature changes. Keep the feature branch unmerged until the native gate is accepted.

## Task 0: Open the draft PR and run the free Mac source probe

**Files:** Create `.github/workflows/macos-pilot.yml`, `tests/test_macos_pilot_workflow.py`; later record the baseline in `docs/builds/macos-arm64-pilot-ci.json`.

**Interfaces:** Use only `pull_request`, with `types: [opened, reopened, synchronize, labeled]` and base `branches: [main]`. Filter jobs to `github.head_ref == 'codex/macos-apple-silicon-pilot'`, a same-repository PR and a public repository. `branches` filters the base, not the head. Initial workflow only runs source checks; Task 4 adds the label-gated packaging job. Check out the event's immutable `github.event.pull_request.head.sha` explicitly, rather than the default synthetic merge commit, and record/verify that source SHA. Repository contents permission is read-only. Do not use `pull_request_target`, secrets or a dispatch input.

- [ ] Confirm the colleague has an M-series Mac, record macOS version/RAM, confirm they can run an unnotarized pilot under their own policy, and confirm a non-synced synthetic working folder. Do not collect serial numbers or private documents. Hardware information is a pilot prerequisite, not a new product hardware check.
- [ ] Begin Task 0 on `codex/macos-apple-silicon-pilot` from the approved main head. Its initial workflow/test commit and push open a draft PR immediately in this task, before app changes or Tasks 1-2. Keep the PR draft and unmerged through review and the native trial. No bootstrap commit goes to main.
- [ ] Write workflow-contract tests that fail while the workflow is absent. Assert the PR events, base/head/same-repository filters, immutable head checkout, standard `macos-14`, 15-minute source timeout, read-only permissions, no secrets and a public-repository job condition. Assert no dispatch, tag, push or `pull_request_target` trigger. Parse YAML using `yaml.BaseLoader` so YAML 1.1 does not turn `on` into a boolean.
- [ ] Add the source-probe workflow using existing checkout/setup-python/upload-artifact actions. Assert Darwin and arm64 before installing existing requirements. Record Python, macOS, Xcode/Clang, Qt/Nuitka versions and availability of installed Python license text. Use no larger runner or new requirement.
- [ ] Run local contract/full tests, commit and push the initial workflow/tests on the feature branch, then open its draft PR as above. The PR uses the workflow from the branch without adding it to main. Proposed commit: `ci: add pull request Apple silicon source checks`.
- [ ] Record the PR-triggered Mac baseline's exact source commit, run URL, test totals and any failures without pretending it passed. Only demonstrated desktop/font/path/test-fixture differences within this plan may proceed into Tasks 1-2; an unexplained document/preservation failure stops work. Also confirm the existing Windows PR source job runs with its build skipped. Do not add the packaging label at this stage.

**Exit:** The feature branch's draft PR runs source checks without any main bootstrap; a zero-cost arm64 runner is confirmed and baseline failures are understood. No Mac application artifact yet.

## Task 1: Adapt active desktop actions, defaults and font

**Files:** Create `simplicitor/app/utils/desktop.py`, `tests/test_desktop.py`; modify the two active widget callers, settings/defaults, `simplicitor/templates_engine/config.py` and their existing tests, including `tests/templates_engine/test_config.py`.

**Interface:** `open_local_path(path: str | Path) -> bool` in `app.utils.desktop`. Return false for a missing/unreadable target or a failed desktop-services request. Use `QDesktopServices.openUrl(QUrl.fromLocalFile(...))` with an absolute local path, never a shell command or raw URL string.

- [ ] Write failing tests for Qt file and folder opening, including a synthetic `Pilot É 100%.docx`, missing files, and `openUrl` returning false. Assert the URL is local and round-trips the complete path. Test the Create action and Settings action through the helper, including failure.
- [ ] Add Darwin-default tests: Generated/Uploads/Backups/Logs/Templates under the synthetic home `Simplicitor` folder; Windows still uses Documents/Simplicitor. Persisted custom folders and all settings keys remain unchanged. For `get_app_data_dir()`, assert Darwin returns `~/Library/Application Support/Simplicitor` both with and without APPDATA set, and never uses the old `~/.simplicitor` fallback. Assert Windows still uses APPDATA/Simplicitor and the existing non-Darwin fallback is unchanged when APPDATA is absent.
- [ ] Add the Darwin branch to `get_app_data_dir()` before APPDATA resolution. Settings and jobs use that root through their existing callers. There are no existing Mac users: add no migration, compatibility lookup or settings schema. Keep the separate `~/Simplicitor` working folders above.
- [ ] Implement the helper and callers. Retain Create's existing failure message. On Settings failure use the normal warning dialog, tested with a simulated answer: `Could not open the logs folder. Open it from the path shown in Settings.` Keep paths out of logs.
- [ ] Select `APP_FONT_FAMILY = "Helvetica Neue"` for Darwin and `"Segoe UI"` otherwise, without calling Qt font-database APIs before QApplication exists. Test both branches and the unchanged minimum size.
- [ ] Leave the hidden legacy Edit panel/DropZone and its unreachable `os.startfile` alone; retain the legacy-disabled tests. Do not clean up unrelated code.
- [ ] Run targeted/full tests and review the Windows UI effects. Proposed commit: `fix: make active desktop actions and defaults portable`.

**Exit:** Active Open actions work through Qt; Mac defaults are separate without migrating existing data, and Windows behavior remains covered.

## Task 2: Make the source test/capture harness Mac-safe

**Files:** Modify `tests/conftest.py`, `scripts/capture_screens.py`, `tests/test_file_utils.py`; create `tests/test_macos_compatibility.py`; extend existing settings/appearance tests only where required.

**Interfaces:** Keep `resource_path(relative: str) -> Path`, existing fixture/worker interfaces and capture arguments unchanged.

- [ ] Add tests proving capture setup isolates Darwin HOME before importing/constructing app settings, and does not install a `C:\Windows\Fonts` override on Mac. Windows keeps its existing font override. Do not change the main-thread GC or worker teardown fixtures.
- [ ] Add compiled-bundle conformance tests using `Simplicitor.app/Contents/MacOS`, a space/Unicode parent and unrelated cwd. Verify the existing `resource_path` resolves the actual S. These tests may already pass; retain the current resolver unless the real bundle demonstrates a different layout.
- [ ] On the Mac source runner, exercise existing DOCX edit verification, XLSX literal/evidence/precision tests and PDF text-layer tests. Add Mac filesystem cases for an existing original's symlink, hard link and case alias when the test volume supports it, plus a Unicode-path save. Assert the original stays byte-identical. Record filesystem capability explicitly; never silently count an unavailable case as passed.
- [ ] Keep existing native-dialog overwrite options, discard behavior and saving contracts. Simulate denied opening/writing and confirm an existing visible failure, no success and no source change. If an engine guard fails, stop rather than patching it under this task.
- [ ] Adapt only proven platform assumptions in fixtures/assertions. Windows build tests remain mocked; do not blanket-skip packaging, UI or preservation suites on Mac. Run the full local suite, then confirm the draft PR's Mac source checks on the exact feature head after pushing.
- [ ] Use the draft PR already opened in Task 0. Confirm the existing Windows `pull_request` source job passes on the app changes with its build skipped. Keep the PR unmerged through the native trial; no second PR or main bootstrap is needed.
- [ ] Generate synthetic captures on the Mac runner at 1280x800 and 1024x640 using the existing script, covering Write, Pull Describe, Choose columns, Review & save with acknowledgement, and Word Review. Check icon visibility, PDF text, controls and scrolling; source/offscreen captures are not native acceptance. Do not replace the public Windows README screenshot.
- [ ] Proposed commit: `test: qualify the source workflows on Apple silicon`.

**Exit:** Full source suites pass on Windows and Mac, with actual counts and platform exceptions justified. Engines/prompts remain unchanged.

## Task 3: Build the self-contained, ad-hoc-signed app

**Files:** Create `build_macos.py`, `tests/test_macos_build.py`; extend `scripts/build_third_party_notices.py` and `tests/test_third_party_notices.py`.

**Interfaces:** In `build_macos.py`, `nuitka_command(output_dir: Path) -> list[str]` is pure, and `build() -> tuple[Path, Path]` returns the pilot ZIP and manifest. `main()` refuses non-Darwin or non-arm64 execution before creating output or invoking a tool. Tests mock every external build/sign/archive command.

- [ ] Write failing command/guard tests. Assert the existing PySide plugin, isolated Python and all current data inputs are included: prompts, `templates/pptx_default.pptx`, both built-in template folders, assets, application LICENSE and generated third-party notices. Assert no Windows/WiX flags, model downloads, paid identity or notarization command.
- [ ] Use existing Nuitka 4.2.2 with `--mode=app`, `--enable-plugin=pyside6`, `--macos-app-name=Simplicitor`, `--macos-signed-app-name=com.simplicitor.pilot`, `--macos-sign-identity=ad-hoc`, `--macos-app-version=<version.py>` and `--macos-app-macos-min-version=15.0`. Build with arm64 Python and keep `MACOSX_DEPLOYMENT_TARGET=14.0` for Nuitka's own compiled code; this lower target is compatible with the app's 15.0 minimum. Cap compilation at two jobs for the standard runner. Output stays under `dist/macos-pilot/` and a distinct `.nuitka/macos-pilot/` build directory.
- [ ] Derive a build-time PNG from the largest image in the actual `assets/icons/simplicitor.ico`, using the already-installed Pillow dependency. Pass it to Nuitka's Mac icon conversion. Do not use `resources/create_icon.py`, redraw the S or commit replacement Windows artwork. Keep the original ICO in bundled assets for the existing Qt header.
- [ ] Reuse `build_notices`/`validate_notices`. Add a small installed-Python license resolver checking `sys.base_prefix/LICENSE.txt`, then `sysconfig.get_path("stdlib")/LICENSE.txt`; require a nonempty file, fail if neither exists. Preserve Windows precedence/output and test both locations and the missing-file failure. Gate any other Mac notice-layout mismatch rather than copying Windows binary inventories or downloading substitute license text.
- [ ] Record the produced bundle layout. Existing module-relative prompt/template lookups must work. Include assets at the existing executable-relative lookup path, or its internal bundle symlink, and prove all links stay inside `.app`. If a resolver change is necessary, add its failing source/Windows-preservation test first; do not refactor generators or workers.
- [ ] Keep the bundle non-sandboxed, using normal user-selected file access. Add no privileged helper, broad entitlement or protected-resource permission flag. Native permission failure stops acceptance for a proposed packaging correction; do not silently add access or claim offscreen CI establishes it.
- [ ] Assemble all bytes before Nuitka's final ad-hoc signing. Create the ZIP with macOS `ditto -c -k --sequesterRsrc --keepParent`, not the Windows archive helper, preserving executable modes and framework symlinks. Nothing inside the app is modified after signing.
- [ ] Manifest fields: `pilot=true`, product version, exact source commit, architecture, minimum OS target, Python/Qt/Nuitka versions, `signing="ad-hoc"`, `notarized=false`, ZIP SHA-256, and a bundle inventory of file hashes plus symlink targets. The manifest cannot hash itself; its own SHA-256 is recorded in the CI evidence later.
- [ ] Run mocked targeted/full tests. Proposed commit: `build: add a free Apple silicon app bundle`.

**Exit:** The builder is tested without running it on Alex's PC. The real bundle is built only at the next task's milestone.

## Task 4: Qualify and deliver one hosted pilot build

**Files:** Extend `.github/workflows/macos-pilot.yml` and its tests; create `scripts/qualify_macos_pilot.py`, `tests/test_macos_qualification.py`, `docs/macos-pilot.md`, `packaging/macos/MAC-PILOT-README.txt`; record `docs/builds/macos-arm64-pilot-ci.json` after the run.

**Interfaces:** `qualify(bundle: Path, manifest: Path, report: Path) -> None`; CLI accepts `--bundle`, `--manifest`, `--report`. The command refuses a non-GitHub, non-Darwin, non-arm64 host before staging files or launching a process. The `build` job needs passing Mac source tests in that run, the same public/same-repository/head-branch filters as Task 0, and an Alex-added PR label: `github.event.action == 'labeled'`, `github.event.label.name == 'mac-package'` and `github.actor == 'alexnosx'`. Verify Alex's account at execution preflight. A label merely present on a later `synchronize` event does not authorize another build. Use the immutable PR head SHA from that label event, read-only permissions and a 120-minute timeout; no `workflow_dispatch` input.

- [ ] Write failing tests for guards, bundle/manifest mismatch, missing icon/template/license, x86-only Mach-O dependency, invalid signature and early process exit. Extend workflow tests for the Alex-added label condition, dependency on source tests, pinned PR head, 14-day final-artifact retention and no package on an ordinary push/synchronize, another label or another actor. External commands/processes are mocked locally.
- [ ] Add the conditional packaging job. Install only existing requirements on the runner. Assert no Ollama endpoint is available; do not install Ollama or any model. Check free artifact storage and expected standard runner before Alex adds the label; lack of free capacity is a stop, not a paid fallback.
- [ ] Write both `docs/macos-pilot.md` and `packaging/macos/MAC-PILOT-README.txt` before packaging, following Task 5's must-pass/optional/feedback sections. Copy the tracked README to the output folder outside the signed app; include it in the workflow artifact. Assert both instructions name ad-hoc signing, no notarization, GitHub sign-in for artifact downloads, the two ZIP layers, Alex's alternative of sending the unchanged pilot ZIP for a browser download, the hash check, local working folders, the Application Support settings/jobs location and the required existing Ollama/model. Do not advertise public Mac support in the main README or website.
- [ ] In both instruction files, state the recorded results by workflow for Q4_K_M: **Edit for Word:** `qwen3:8b-q4_K_M` and `llama3.1:8b-instruct-q4_K_M` both passed, 11/12 each (see [Word check](../../evaluation/2.3.0-edit-model-check.json)). **Pull information into Excel:** `qwen3:8b-q4_K_M` passed, 272/280 (97.14%) with zero unflagged wrong; `llama3.1:8b-instruct-q4_K_M` failed the 95% accuracy bar, 262/280 (93.57%) (see [extraction rerun](../../evaluation/2026-10-08-task1-rerun.md)). Whole-file extraction was then qualified on `qwen3:8b` only. These are prior Windows results, not Mac qualification. Other local Ollama models can be used but are unchecked; results depend on the model. The colleague may use their own installed models. Do not install one, force a model choice or rerun the benchmark.
- [ ] Qualify a `ditto`-extracted copy in a runner-owned temporary path containing spaces/Unicode outside the checkout. Verify inventory/symlinks, executable modes, Info.plist name/identifier/version, minimum OS, actual S and all data/notices. Check every bundled Mach-O includes arm64; universal dependencies are acceptable, x86-only ones are not. Read the declared minimum from Info.plist and reject any bundled binary whose deployment minimum exceeds it. Keep every offending path, architecture and actual minimum in the report/error, alongside all passing minima; a plist value alone is not evidence of compatibility.
- [ ] Run `codesign --verify --deep --strict --verbose=2` on the extracted app and confirm the signature is ad-hoc with no Team ID. Record `notarized=false`. Do not require a successful Gatekeeper assessment or imply ad-hoc signing establishes publisher trust.
- [ ] Launch the extracted executable twice with `QT_QPA_PLATFORM=offscreen`, isolated HOME, Windows profile variables unset, minimal PATH and unrelated cwd. It must remain running for 20 seconds without Ollama on each launch. Preserve a synthetic pre-existing settings file and local sentinel document. Stop only the process started by qualification; no GUI-thread wait or application self-test mode is added. Hashes of bundled files must remain unchanged.
- [ ] Run local targeted/full tests. Review shared-code and packaging diffs and confirm the current head's Windows/Mac source checks before the first real package run. Once packaging is authorized, Alex adds `mac-package` to the existing draft PR. Record its head SHA and verify the label-triggered run builds that exact SHA. The branch workflow stays off main. After a failure, stop and report before any fix or newly approved label-triggered run.
- [ ] Upload only the four final outputs with `retention-days: 14`; no `.build` tree or new release. The report names checks individually with pass/fail, source/run identity, runner image, versions, architecture, signature result, hashes and explicit limits: no native Cocoa, Gatekeeper, real model or Office acceptance.
- [ ] Record the passing run/artifact URLs, source commit, full test counts, ZIP size/hash, manifest/report hashes, dependency versions and hosted checks in the CI record. Retain Task 0's baseline in `baseline_probe`; record Task 2's passing platform suites in `source_validation` and this milestone in `package_validation`. On Alex's PC, download/hash only; use completed runner logs for qualification details rather than unpacking the app. Record commits remain distinguishable from the built source.
- [ ] Proposed code commit: `ci: qualify the Apple silicon pilot artifact`; evidence commit: `docs: record the Apple silicon pilot build`.

**Exit:** A reproducible artifact exists with passing hosted checks. This is permission to propose a native trial, not evidence that the native trial passed.

## Task 5: Native colleague trial and pilot acceptance

**Files:** Update `docs/macos-pilot.md`, record `docs/builds/macos-arm64-pilot-native.json`, and update PROJECT_STATUS with the measured result. The instructions already shipped in Task 4's artifact; this task adds the actual native outcome.

**Interfaces:** Native record fields: exact source/run/artifact identity and ZIP hash; chip family, RAM and macOS version; download route and Gatekeeper outcome; separate `must_pass_checks`, `optional_checks` and `feedback`; known limits and Alex's final decision. Each check has a result (`passed`, `failed` or `not checked`), a plain-language observation and its actual `model_tag` whenever a model was used (null for a check not run or not using a model). Record the tag actually selected, not a recommended tag substituted afterwards. Original-file checks record synthetic fixture identifiers and before/after SHA-256, not personal filenames or paths. No personal account name, customer document or content.

### Preparation and first download

- [ ] Explain both delivery routes in both instruction files. Direct route: sign into GitHub (required), download the workflow artifact through the browser, extract the outer container, verify the pilot ZIP's SHA-256, then extract `Simplicitor-macos-arm64-pilot.zip`. Alternative: Alex downloads the artifact and sends the unchanged pilot ZIP with its expected hash and instructions; the colleague downloads that ZIP through their browser, verifies it and extracts it. Do not send an already-extracted app or strip quarantine. Record actual quarantine/first-launch behavior for the route used; do not assume CI establishes it. Artifact availability is 14 days.
- [ ] Place `Simplicitor.app` in the user's own `~/Applications` folder. Use a non-synced synthetic working folder and copies of existing fixtures linked to the exact built source. No Python, Xcode, package manager or Office setup. The colleague uses their existing local Ollama and their own installed model; the instructions give the recorded Q4_K_M results by workflow as in Task 4 without restricting the pilot to those models. No agent installs software or models on their Mac.

### Must-pass native checks

- [ ] **First launch:** Double-click the browser-downloaded app in Finder. Record the actual Gatekeeper message/outcome. If macOS asks and the colleague chooses to trust this app, use Apple's one-time per-app Open Anyway procedure, then confirm the app launches. Never script an override or remove quarantine. Blocking or declining the needed exception means this check has not passed.
- [ ] **S visible:** Confirm the actual S logo is visible in the app header. Record the observed result, not the runner's icon-file check.
- [ ] **Pull to Excel:** With local Ollama and the colleague's chosen model, use one synthetic DOCX or text-layer PDF, confirm columns, extract, review values/evidence, acknowledge issues if required, and Save As a new XLSX. Inspect the saved table/evidence using the app's saved-grid review and an existing viewer if available. Record the model tag actually used and whether the saved result is correct. This is one end-to-end Mac check, not a rerun or relaxation of the model benchmark.
- [ ] **Word edit:** Open `word-basic.docx`, describe the synthetic payment-period change from 30 to 45 days, review before/after with red deletions/green additions, use the change and Save As a new DOCX. Confirm the saved candidate reflects the reviewed change and record the actual model tag. Do not silently substitute a checked model if the user's model fails; report the outcome.
- [ ] **Originals unchanged:** Compare SHA-256 before and after both workflows above. Both original source files must be byte-identical, with results recorded per fixture.

The pilot passes when every must-pass check is `passed`. A failed or not-checked must-pass item means it has not passed; report the cause without changing the checks. Hosted qualification is a prerequisite, not a substitute for these native results. Optional checks below do not gate that result.

### Optional native checks

- [ ] Record **each** optional check as `passed`, `failed` or `not checked`, with its actual model tag whenever a model is used. No suitable viewer or no time means `not checked`, never an assumed pass. Keep any screenshots synthetic.
- [ ] Generate Word, PDF, Excel and PowerPoint from prompts; exercise both built-in templates. Check outputs in applications already installed. Try the other source format not used in the must-pass Pull check, and the existing Open file action.
- [ ] Check 1280x800 and 1024x640 reachability for Write/Pull, acknowledgement/Save to Excel and Edit Review, plus header labels, Finder/Dock icon, fonts/focus and native display scaling. CI scale emulation is not Retina/native acceptance.
- [ ] Try Finder drag/drop, Unicode paths, denied file access, overwrite/original refusal, discard/Keep editing, cancellation and closing during work. Report each case separately.
- [ ] Try Open logs, disconnected startup without Ollama, normal close/reopen and settings/files surviving reopening. Confirm chosen working folders remain outside configured sync locations. Do not claim a network-security audit or control over OS backups/iCloud settings.

### Feedback from the colleague's own use

- [ ] After the must-pass checks, invite the colleague, a real target user and local-LLM enthusiast, to use Simplicitor for their own work with their own models. Their documents stay on their Mac; do not request files, logs, screenshots of real work or remote access.
- [ ] Record their answers in plain words: **what they tried; what worked; what failed or annoyed them; what they wished it did**. Omit document contents, quotes, filenames and private paths. Record the actual model tag for any model-assisted check they report; if it was not recorded, say so and do not count that account as a verified check. If they provide no feedback, record `not provided`, not an assumed positive result. Feedback is separate from the must-pass score.

### Record and decision

- [ ] Record the must-pass outcome, every optional status and the feedback separately. Alex decides whether to accept the result and merge, widen testing or stop. No public Mac support/download announcement or publication follows automatically.
- [ ] Proposed commit after an actual report: `docs: record native Apple silicon pilot acceptance`. Update PRD/platform wording and public instructions only within the support scope Alex then approves; do not claim every M-series model or every macOS version was tested.

**Exit:** A native pilot outcome tied to exact bytes and actual model tags, with explicit optional results and real-use feedback. The existing Windows release stays unchanged.

## Effort and stop points

Estimated engineering effort: **4-7 working days**, plus colleague/reviewer availability. This is a planning estimate, not measured Mac implementation time. The low-cost stopping points are the source probe, passing source suites, the qualified package and the native trial. Stop at any of them if the next step cannot remain free or within the preservation contract. Ongoing Mac support adds a second platform test/build lane even if compilation costs nothing.

Plan approval is the next decision. This revision's commit/push is authorized; implementation, feature-branch/draft-PR creation, label-triggered Mac packaging, implementation commits/pushes, merging and distribution need Alex's execution go. Nothing in this plan requires a default-branch workflow bootstrap.

## Sources checked for this proposal

- [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners): free standard public-repository arm64 runners, `macos-15` for packaging and `macos-14` for source tests. Verified again on 2026-10-19; availability is not an everlasting guarantee.
- [GitHub PR events and branch filters](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request): `pull_request` with `labeled`, head-branch conditions and explicit head-SHA checkout. No default-branch dispatch bootstrap.
- [GitHub artifact downloads](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts): GitHub sign-in and repository read access are required for workflow artifacts. Alex can instead send the unchanged inner pilot ZIP for a browser download.
- [Qt 6.11 supported platforms](https://doc.qt.io/qt-6.11/supported-platforms.html): arm64 macOS support. Retain the project's pinned 6.11.2 runtime.
- [Nuitka deployment](https://nuitka.net/user-documentation/user-manual.html), plus installed 4.2.2 `nuitka/options/OptionParsing.py`, `Options.py` and `freezer/MacOSApp.py`: bundle flags, ad-hoc identity and plist behavior. No Nuitka build was run while drafting.
- [Ollama on macOS](https://docs.ollama.com/macos): macOS 14+, Apple M-series CPU/GPU support.
- [Apple first-launch policy](https://support.apple.com/en-us/102445): limits of unnotarized distribution and the user-controlled per-app exception.
- [Apple Documents/iCloud behavior](https://support.apple.com/en-us/109344): why a Mac pilot should not blindly inherit Documents as its default working root.
