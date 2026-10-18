# Apple Silicon Mac Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. No execution method is selected or authorized by this draft.

**Status:** Draft 1, proposed on 2026-10-18. Alex authorized committing and pushing this plan for Claude's review. Implementation, workflow dispatches, merging and distribution are not approved.

**Goal:** Give one Apple silicon Mac user a self-contained Simplicitor pilot, retaining the current document workflows and spending nothing on certificates, services or build infrastructure.

**Architecture:** Keep the Python/PySide6 app, Ollama client, workers and document engines. Make small desktop/path/font adaptations, and add a separate Nuitka Mac build and manual GitHub workflow. Deliver an ad-hoc-signed `Simplicitor.app` in a ZIP; qualify it on the runner and then on the colleague's actual Mac.

**Tech Stack:** Existing Python 3.11, PySide6 6.11.2, Nuitka 4.2.2 and document libraries; Qt desktop services; macOS `codesign`, `ditto`, `lipo` and `otool`; standard GitHub-hosted arm64 runner.

**Spec:** Alex's request for a free Apple silicon pilot, the existing [PRD](../../../PRD.md), [architecture](../specs/2026-10-08-document-architecture-design.md), [UI design](../specs/2026-10-08-document-workspace-ui-design.md), [Word preservation design](../specs/2026-10-13-edit-for-word-design.md), and [packaging policy](../../code-signing.md). This proposal adds a pilot platform, not a new document workflow. The Windows-only product scope stays in force until execution is approved and the pilot passes.

**Inspected baseline:** Main at `f565f573e5886f7af76891b17a22b6589f040cf5`, with product version 2.5.1. The recorded Windows suite has 1,395 tests. No Mac run has been performed; this is not a claim that 1,395 tests pass on macOS.

## Global constraints

- Apple silicon only. Target macOS 14.0 or newer; qualify only the OS versions actually tested. No Intel build, Rosetta dependency, universal-app project or App Store work.
- No paid certificate, Apple Developer subscription, notarization, paid runner or new dependency. Ad-hoc signing is free and required by this build route; it establishes bundle integrity, not a verified publisher or Gatekeeper trust.
- No cloud model, remote Ollama endpoint, telemetry, cloud fallback or bundled/downloaded model. Keep existing prompts, options, profiles, grounding, evidence and model-size warning.
- Preserve document patch/verification/save rules, source protection, cancellations, stale-result handling, worker retirement and legacy Edit disabling. A defect requiring an engine change stops the pilot for a separate decision.
- No version bump. Read `version.py`; distinguish the pilot by its artifact name, source commit and evidence. Do not tag, create a GitHub Release, add Mac assets to v2.5.1 or change its release records.
- Leave `build.py`, `.github/workflows/build.yml`, the MSI route, current Windows defaults, LICENSE and existing release artifacts unchanged. Reuse their data/notice conventions without redesigning the Windows builder.
- Future app branch: `codex/macos-apple-silicon-pilot`. No branch is created by writing this plan. No app merge into main before the native pilot result and Alex's approval.
- On Alex's PC: existing source tests and synthetic captures only. No build script, installer, uninstaller, msiexec, Sandbox, WiX, qualification script or tool/dependency installation. Download/hash a Mac artifact only; do not unpack or run it here.
- Mac builds, dependency installation and automated qualification run only on GitHub's disposable Mac runner. The colleague performs native checks on their own Mac, with their consent. No remote access is assumed.
- Use synthetic fixtures only. No customer documents, file contents, prompts, responses, sensitive filenames or private paths in reports/logs.

## Pilot decisions

| Decision | Proposed implementation |
|---|---|
| Build host | Standard `macos-14` runner, Python 3.11 arm64, with runtime assertions for Darwin and arm64. Recheck availability before execution; never substitute a paid `-large`/`-xlarge` runner. |
| Cost | The repository was confirmed PUBLIC on 2026-10-18. Standard public-repository runners are free. Check available free artifact storage before dispatch; retain only final outputs for one day. If zero-cost execution cannot be confirmed, stop. Do not enable billing or change account settings. |
| Distribution | One workflow artifact containing `Simplicitor-macos-arm64-pilot.zip`, `SHA256SUMS-macos-pilot.json`, `macos-pilot-qualification.json` and `MAC-PILOT-README.txt`. The inner ZIP contains `Simplicitor.app` at its root. |
| Signing | Explicit Nuitka `--macos-sign-identity=ad-hoc`. No signing secret, identity auto-detection, Apple account credential or notarization call. Verify the final signature after ZIP round-trip. |
| First launch | State plainly that macOS may block this unidentified, unnotarized app. The user may choose Apple's per-app Open Anyway procedure. Never remove quarantine, disable Gatekeeper, request blanket Full Disk Access or work around managed-device policy. A blocked/declined first launch is a failed native gate, not a passing pilot. |
| Settings/jobs | Reuse native Mac fallback `~/.simplicitor` through `get_app_data_dir()`. No new settings schema or migration. |
| New Mac working folders | Default to `~/Simplicitor/{Generated,Uploads,Backups,Logs,Templates}`, outside the usual Desktop/Documents iCloud sync locations. Preserve saved custom paths. Explicitly tell the pilot user to use folders not managed by any sync provider; no automatic cloud-folder detector or guarantee about OS backup/sync. |
| Appearance | Keep the Azure layout, actual S and wording. Use `Helvetica Neue` on Darwin, Segoe UI elsewhere, retaining 11 pt minimum body text. No Mac redesign. |
| Compatibility claim | No Office installation required. Existing OOXML/PDF behavior is retained; no new Pages, Numbers, Keynote or PDF-editing claim. |

## Review focus

1. A browser-downloaded, quarantined app must be judged separately from an unquarantined CI launch. Task 5 owns the native first-launch gate.
2. Spaces, Unicode, a changed working directory and `.app` resource locations must not break the S, prompts or either built-in template. Tasks 2, 3 and 4 own these checks.
3. Mac fonts and Qt metrics must keep PDF text readable and the header, review acknowledgement and Save actions reachable. Tasks 2 and 5 own the source/native checks.
4. Existing settings must survive; the new Mac defaults must not silently use iCloud Documents or modify Windows defaults. Tasks 1 and 4 own the tests.
5. Mac filesystem aliases and denied access must not bypass original-file protection or turn failed saving into success. Tasks 2 and 5 exercise existing guards; they do not rewrite them.

## Files and responsibilities

| Files | Responsibility |
|---|---|
| New `.github/workflows/macos-pilot.yml` | Manual source probe and, later, conditional pilot packaging. No release permissions or tag/push trigger. |
| New `simplicitor/app/utils/desktop.py` | One Qt-based file/folder opening helper. |
| `simplicitor/app/widgets/create_screen.py`, `settings_dialog.py` | Use that helper for the existing active desktop actions. |
| `simplicitor/app/config/settings.py`, `defaults.py` | Darwin-only default working root and font selection. |
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
- Manual Mac milestones only: the Task 0 baseline and Task 4 final package. Source-probe reruns are justified by an actual compatibility change or failed check; no full Mac build per commit.
- Proposed commits below require execution/commit/push authorization. Update REPO_MAP after file/signature changes. Keep the feature branch unmerged until the native gate is accepted.

## Task 0: Bootstrap the free Mac source probe

**Files:** Create `.github/workflows/macos-pilot.yml`, `tests/test_macos_pilot_workflow.py`; later record the baseline in `docs/builds/macos-arm64-pilot-ci.json`.

**Interfaces:** `workflow_dispatch` input `package` is boolean, default false. Initial workflow only runs source checks; Task 4 adds packaging behind this already-declared input. Repository contents permission is read-only.

- [ ] Confirm the colleague has an M-series Mac, record macOS version/RAM, confirm they can run an unnotarized pilot under their own policy, and confirm a non-synced synthetic working folder. Do not collect serial numbers or private documents. Hardware information is a pilot prerequisite, not a new product hardware check.
- [ ] Write workflow-contract tests that fail while the workflow is absent. Assert manual dispatch only, `package=false`, standard `macos-14`, 15-minute source timeout, read-only permissions, no secrets and a public-repository job condition. Parse YAML using `yaml.BaseLoader` so YAML 1.1 does not turn `on` into a boolean.
- [ ] Add the source-probe workflow using existing checkout/setup-python/upload-artifact actions. Assert Darwin and arm64 before installing existing requirements. Record Python, macOS, Xcode/Clang, Qt/Nuitka versions and availability of installed Python license text. Use no larger runner or new requirement.
- [ ] Run local contract/full tests. GitHub requires a dispatch workflow on the default branch: propose a separately reviewed **workflow-and-test-only bootstrap commit on main**, with Alex's explicit approval before it is pushed. Do not merge app changes as a shortcut to enabling dispatch. This default-branch prerequisite must be settled before execution starts.
- [ ] Dispatch the baseline with `package=false`. Record the source commit, run URL, test totals and any failures without pretending it passed. Only demonstrated desktop/font/path/test-fixture differences within this plan may proceed into Tasks 1-2; an unexplained document/preservation failure stops work.
- [ ] After the bootstrap, create the feature branch from the resulting main head when branch creation is authorized. Proposed bootstrap commit: `ci: add a manual Apple silicon source probe`.

**Exit:** A zero-cost arm64 runner is confirmed, the default-branch dispatch entry exists, and baseline failures are understood. No Mac application artifact yet.

## Task 1: Adapt active desktop actions, defaults and font

**Files:** Create `simplicitor/app/utils/desktop.py`, `tests/test_desktop.py`; modify the two active widget callers, settings/defaults and their existing tests.

**Interface:** `open_local_path(path: str | Path) -> bool` in `app.utils.desktop`. Return false for a missing/unreadable target or a failed desktop-services request. Use `QDesktopServices.openUrl(QUrl.fromLocalFile(...))` with an absolute local path, never a shell command or raw URL string.

- [ ] Write failing tests for Qt file and folder opening, including a synthetic `Pilot É 100%.docx`, missing files, and `openUrl` returning false. Assert the URL is local and round-trips the complete path. Test the Create action and Settings action through the helper, including failure.
- [ ] Add Darwin-default tests: Generated/Uploads/Backups/Logs/Templates under the synthetic home `Simplicitor` folder; Windows still uses Documents/Simplicitor. Persisted custom folders and all settings keys remain unchanged. Confirm the existing Mac `~/.simplicitor` fallback with APPDATA unset.
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
- [ ] Adapt only proven platform assumptions in fixtures/assertions. Windows build tests remain mocked; do not blanket-skip packaging, UI or preservation suites on Mac. Run the full local suite, then the manual Mac source probe on the exact feature head.
- [ ] When PR creation/pushing is authorized, open a draft PR for the feature branch so the existing Windows `pull_request` source job runs on the app changes; a feature-branch push alone does not trigger that job. Confirm it passes with the build skipped. Keep the PR unmerged through the native trial.
- [ ] Generate synthetic captures on the Mac runner at 1280x800 and 1024x640 using the existing script, covering Write, Pull Describe, Choose columns, Review & save with acknowledgement, and Word Review. Check icon visibility, PDF text, controls and scrolling; source/offscreen captures are not native acceptance. Do not replace the public Windows README screenshot.
- [ ] Proposed commit: `test: qualify the source workflows on Apple silicon`.

**Exit:** Full source suites pass on Windows and Mac, with actual counts and platform exceptions justified. Engines/prompts remain unchanged.

## Task 3: Build the self-contained, ad-hoc-signed app

**Files:** Create `build_macos.py`, `tests/test_macos_build.py`; extend `scripts/build_third_party_notices.py` and `tests/test_third_party_notices.py`.

**Interfaces:** In `build_macos.py`, `nuitka_command(output_dir: Path) -> list[str]` is pure, and `build() -> tuple[Path, Path]` returns the pilot ZIP and manifest. `main()` refuses non-Darwin or non-arm64 execution before creating output or invoking a tool. Tests mock every external build/sign/archive command.

- [ ] Write failing command/guard tests. Assert the existing PySide plugin, isolated Python and all current data inputs are included: prompts, `templates/pptx_default.pptx`, both built-in template folders, assets, application LICENSE and generated third-party notices. Assert no Windows/WiX flags, model downloads, paid identity or notarization command.
- [ ] Use existing Nuitka 4.2.2 with `--mode=app`, `--enable-plugin=pyside6`, `--macos-app-name=Simplicitor`, `--macos-signed-app-name=com.simplicitor.pilot`, `--macos-sign-identity=ad-hoc`, `--macos-app-version=<version.py>` and `--macos-app-macos-min-version=14.0`. Build with arm64 Python and `MACOSX_DEPLOYMENT_TARGET=14.0`; cap compilation at two jobs for the standard runner. Output stays under `dist/macos-pilot/` and a distinct `.nuitka/macos-pilot/` build directory.
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

**Interfaces:** `qualify(bundle: Path, manifest: Path, report: Path) -> None`; CLI accepts `--bundle`, `--manifest`, `--report`. The command refuses a non-GitHub, non-Darwin, non-arm64 host before staging files or launching a process. `build` job needs passing source tests and `inputs.package == true`, with a public-repository condition, read-only permissions and a 120-minute timeout.

- [ ] Write failing tests for guards, bundle/manifest mismatch, missing icon/template/license, x86-only Mach-O dependency, invalid signature and early process exit. External commands/processes are mocked locally.
- [ ] Add the conditional packaging job. Install only existing requirements on the runner. Assert no Ollama endpoint is available; do not install Ollama or any model. Check free artifact storage and expected standard runner before dispatch; lack of free capacity is a stop, not a paid fallback.
- [ ] Write the pilot instructions before packaging, following the exact native steps in Task 5. Copy the tracked `packaging/macos/MAC-PILOT-README.txt` to the output folder outside the signed app; include it in the workflow artifact. Assert the instructions name ad-hoc signing, no notarization, the two ZIP layers, the hash check, local folders and the required existing Ollama/model. Do not advertise public Mac support in the main README or website.
- [ ] Qualify a `ditto`-extracted copy in a runner-owned temporary path containing spaces/Unicode outside the checkout. Verify inventory/symlinks, executable modes, Info.plist name/identifier/version, minimum OS, actual S and all data/notices. Check every bundled Mach-O includes arm64; universal dependencies are acceptable, x86-only ones are not. Check dependency deployment minima do not exceed macOS 14.0; a plist value alone is not evidence of that.
- [ ] Run `codesign --verify --deep --strict --verbose=2` on the extracted app and confirm the signature is ad-hoc with no Team ID. Record `notarized=false`. Do not require a successful Gatekeeper assessment or imply ad-hoc signing establishes publisher trust.
- [ ] Launch the extracted executable twice with `QT_QPA_PLATFORM=offscreen`, isolated HOME, Windows profile variables unset, minimal PATH and unrelated cwd. It must remain running for 20 seconds without Ollama on each launch. Preserve a synthetic pre-existing settings file and local sentinel document. Stop only the process started by qualification; no GUI-thread wait or application self-test mode is added. Hashes of bundled files must remain unchanged.
- [ ] Run local targeted/full tests. Review shared-code and packaging diffs before the first real package run. Once dispatch is authorized: `gh workflow run macos-pilot.yml --ref codex/macos-apple-silicon-pilot -F package=true`. Capture the exact built commit before dispatch, and verify the run uses it.
- [ ] Upload only the four final outputs with one-day retention; no `.build` tree or new release. On failure, report it before any fix/retry. The report names checks individually with pass/fail, source/run identity, runner image, versions, architecture, signature result, hashes and explicit limits: no native Cocoa, Gatekeeper, real model or Office acceptance.
- [ ] Record the passing run/artifact URLs, source commit, full test counts, ZIP size/hash, manifest/report hashes, dependency versions and hosted checks in the CI record. Retain Task 0's baseline in `baseline_probe`; record Task 2's passing platform suites in `source_validation` and this milestone in `package_validation`. On Alex's PC, download/hash only; use completed runner logs for qualification details rather than unpacking the app. Record commits remain distinguishable from the built source.
- [ ] Proposed code commit: `ci: qualify the Apple silicon pilot artifact`; evidence commit: `docs: record the Apple silicon pilot build`.

**Exit:** A reproducible artifact exists with passing hosted checks. This is permission to propose a native trial, not evidence that the native trial passed.

## Task 5: Native colleague trial and pilot acceptance

**Files:** Update `docs/macos-pilot.md`, record `docs/builds/macos-arm64-pilot-native.json`, and update PROJECT_STATUS with the measured result. The instructions already shipped in Task 4's artifact; this task adds the actual native outcome.

**Interfaces:** Native record fields: exact source/run/artifact identity and ZIP hash; chip family, RAM and macOS version; local model tag; each check's result; Gatekeeper outcome; known limits and Alex's final decision. No personal account name, source path, customer document or content.

- [ ] Explain the two archive layers: download the GitHub Actions artifact (GitHub sign-in may be required), extract that container, verify the pilot ZIP hash, then extract `Simplicitor-macos-arm64-pilot.zip`. Place `Simplicitor.app` in the user's own `~/Applications` folder. No Python, Xcode, package manager or Office setup for the pilot user.
- [ ] The colleague downloads through their browser so normal quarantine/first-launch behavior is retained. Record the actual Gatekeeper message/outcome. If they choose to trust this specific app, point to Apple's Open Anyway instructions; never script an override. Managed-device blocking or refusal to make a per-app exception stops the trial.
- [ ] With Ollama stopped, double-click the app in Finder: S visible in Finder/Dock/header, full header labels, no terminal, clear disconnected state, normal close/reopen. Then start the colleague's locally installed Ollama and select an existing model. No agent installs a model or software on their Mac.
- [ ] Use copies of existing synthetic fixtures, supplied by linking to the exact built source. Exercise prompt generation for Word, PDF, Excel and PowerPoint, including both built-in templates. Open the resulting files in applications the colleague already has. If no suitable viewer is available, report that visual-output check as unverified rather than installing Office or claiming acceptance.
- [ ] Pull `invoice-01.docx` and a text PDF into Excel: confirm/edit columns, inspect quotes/anchors and saved Data/Evidence, acknowledge flagged/reading issues, use Save As, and use Open file. Preserve original hashes. Do not rerun or relax the existing model benchmark; this is an end-to-end compatibility check.
- [ ] Open `word-basic.docx`, change the synthetic payment period from 30 to 45 days, review red deletions/green additions, and save a new copy. Exercise overwrite/original refusal, discard/Keep editing, cancel and closing during work. Confirm original bytes remain unchanged and the saved result opens. Any unavailable or failed check is explicit.
- [ ] At 1280x800 and 1024x640 on the native display, check Write/Pull, acknowledgement/Save to Excel and Edit Review reachability, header S, font/focus, drag/drop from Finder, file permissions, Unicode paths and Open logs. Keep screenshots synthetic. CI scale emulation is not Retina/native acceptance.
- [ ] Confirm files/settings survive app close/reopen, chosen folders are outside the user's configured sync locations, and no cloud model is used. Do not claim a network-security audit or that the app controls OS backups/iCloud settings.
- [ ] Record pass/fail/unverified for every item and observed model/output quality. A missing required native check means the pilot is not yet accepted. Alex decides whether the result is acceptable and whether to merge, widen testing or stop. No public Mac support/download announcement or publication follows automatically.
- [ ] Proposed commit after an actual report: `docs: record native Apple silicon pilot acceptance`. Update PRD/platform wording and public instructions only within the support scope Alex then approves; do not claim every M-series model or every macOS version was tested.

**Exit:** A named pilot outcome on a real Mac, tied to exact bytes, with the existing Windows release unchanged.

## Effort and stop points

Estimated engineering effort: **4-7 working days**, plus colleague/reviewer availability. This is a planning estimate, not measured Mac implementation time. The low-cost stopping points are the source probe, passing source suites, the qualified package and the native trial. Stop at any of them if the next step cannot remain free or within the preservation contract. Ongoing Mac support adds a second platform test/build lane even if compilation costs nothing.

Plan approval is the next decision. It does not itself authorize the default-branch workflow bootstrap, implementation, Mac dispatches, commits/pushes, merging or public distribution unless Alex explicitly includes them in his execution go.

## Sources checked for this proposal

- [GitHub standard runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners): free standard public-repository runners and current arm64 `macos-14` label. Verify again before execution; availability is not an everlasting guarantee.
- [GitHub manual dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow): default-branch workflow prerequisite.
- [Qt 6.11 supported platforms](https://doc.qt.io/qt-6.11/supported-platforms.html): arm64 macOS support. Retain the project's pinned 6.11.2 runtime.
- [Nuitka deployment](https://nuitka.net/user-documentation/user-manual.html), plus installed 4.2.2 `nuitka/options/OptionParsing.py`, `Options.py` and `freezer/MacOSApp.py`: bundle flags, ad-hoc identity and plist behavior. No Nuitka build was run while drafting.
- [Ollama on macOS](https://docs.ollama.com/macos): macOS 14+, Apple M-series CPU/GPU support.
- [Apple first-launch policy](https://support.apple.com/en-us/102445): limits of unnotarized distribution and the user-controlled per-app exception.
- [Apple Documents/iCloud behavior](https://support.apple.com/en-us/109344): why a Mac pilot should not blindly inherit Documents as its default working root.
