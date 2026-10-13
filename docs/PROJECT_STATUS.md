# Simplicitor project status

Updated 2026-10-13 after v2.2.0 publication and verification as Latest. B3 ended in a drop, B5 is complete and B4 was not executed. [PRD.md](../PRD.md) owns requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md) and the [2.2.0 plan](superpowers/plans/2026-10-12-release-2.2.0.md) are the current review set. The [2.1.0 plan](superpowers/plans/2026-10-09-release-2.1.0.md) and [2.0.0 extraction plan](superpowers/plans/2026-10-08-first-release-extraction.md) retain their earlier execution records.

## Current status

| Area | Current state |
|---|---|
| Published releases | [v2.2.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.2.0) is published and verified as Latest with Simplicitor-2.2.0.msi, portable ZIP, checksums and the tagged notes as its body. The tag points to d57bc6e; [release evidence](releases/v2.2.0.json). Earlier [v2.1.0](releases/v2.1.0.json), [v2.0.0](releases/v2.0.0.json) and [v1.2.1](releases/v1.2.1.json) releases and licenses remain unchanged. |
| 2.1.0 release | Task 0, Parts A/B/C1/C2, both C2 follow-ups, D1 and the final README corrections are accepted. Published from the tested README commit 2202cce; MSI version 2.1.0 and executable version 2.1.0.0. The [tag workflow](https://github.com/alexnosx/Simplicitor/actions/runs/38233039100) passed source tests, build, MSI qualification and publication. Downloaded hashes and the release body are verified in the release record. |
| 2.2.0 Part A | A1-A4 complete in source: finished extraction progress clears while final messages stay; source-aware prompt hints and Settings guidance; one shared version for UI/build/upgrade qualification; named Word reading problems and a general review heading. Product version 2.2.0 is published after the E1 milestone and E2 tag workflow passed. |
| 2.2.0 B3 gate and B5 | Gate B3 failed (3 of 8 decks acceptable, 1 of 4 real) and Alex chose to drop the upload without a fix round (2026-10-12). B5 removed the template upload, the rejection dialog and the B1-B3 capture code; the picker offers built-in templates only. B4 was not executed. |
| 2.2.0 C1 | Alex reassigned the [Create new mockup](design/document-workspace.html) to Codex and approved it on 2026-10-13. The approved artifact is 38af728, including the 2.2.0 preview version and revised Edit wording, integrated into main. It shows all seven requested points and ten preset states. |
| 2.2.0 Part D | Merged into main from `feature/2.2.0-create-new-qt` at c51b8ee with Alex's explicit approval, after Claude's review and the verified layout/label follow-ups. Explicit Write/Pull routes retain their own inputs and apply the existing invalidation/busy gates. Numbered cards, larger text, blue choices, template Clear, reading states and per-file/action progress match C1's requested behavior. Published in 2.2.0. [Tasks as built](superpowers/plans/2026-10-12-release-2.2.0.md#part-d-tasks-as-built). |
| 2.2.0 E1 | Complete: scope/specs and release notes follow the B3 drop and merged Create routes. Isolated suites passed 1,100 tests after the version change and before the source commit (49.92 and 51.00 seconds; existing cache warning). The [manual milestone](https://github.com/alexnosx/Simplicitor/actions/runs/38361208855) built exact source commit 4bf7d864dd4a3f9707cd25ac168523ae55db5e6e: 1,100 hosted tests, build and all 58 MSI qualification checks passed. Its MSI 2.2.0 is 61,200,249 bytes; executable 2.2.0.0; derived upgrade probe 2.2.1. Downloaded MSI/ZIP hashes match the manifest and qualification report; [build evidence](builds/2.2.0-ci.json) records all downloaded hashes. Publication was skipped for this milestone; E2 publication is recorded separately. |
| 2.2.0 E2 | Published from Alex's approved tagged commit d57bc6eceb522a6c17d9ab0df04fd3026ce7ff6b after its push tests passed. The [tag workflow](https://github.com/alexnosx/Simplicitor/actions/runs/38366925435) passed 1,100 source tests, rebuild, all 58 MSI qualification checks and publication. Latest status, exactly three assets, downloaded hashes against the manifest/GitHub digests and the body against tagged notes are verified in the [release record](releases/v2.2.0.json). No release payload ran locally. |
| 2.3.0 C2 | Alex approved the [Edit for Word mockup](design/edit-document.html) on 2026-10-13, after Claude's review. The approved artifact is 1dd4949. It shows the flow, read-only parts with reasons, continuous whole-paragraph selection rules, before and after review of the selected part, saving as a new file, the mode switch, the discard confirmation and 16 preset states. |
| 2.3.0 technical design | Alex approved the [Edit for Word design](superpowers/specs/2026-10-13-edit-for-word-design.md) on 2026-10-13 at c770a74 (draft 4), after Codex's [four reviews](reviews/2026-10-13-edit-for-word-design-codex.md). Findings F1 to F14 are resolved; no open findings. |
| 2.3.0 implementation plan | Alex approved the [implementation plan](superpowers/plans/2026-10-13-release-2.3.0.md) on 2026-10-13 at c0b7a91 (draft 4), with design amendments A1 to A3, after [four Codex reviews](reviews/2026-10-13-release-2.3.0-plan-codex.md). Findings F1 to F13 are resolved; no open findings. |
| 2.3.0 Part A | A1-A7 are committed and pushed; their targeted suites passed 27, 21, 15, 9, 37, 10 and 10 tests, and the last full isolated suite passed 1,229. A8's model-check and Word-check tools are written, but its targeted rerun returned 26 passed and 1 failed: `test_builds_every_sample_into_an_empty_folder` supplies a repository-contained temporary folder, which the builder correctly rejects. A8's full suite has not run; Part A is incomplete and Part B has not started. No live-model or Word sample check has run. |
| Prompt creation and templates | Word, Excel and PowerPoint generation remain available. PDF uses the existing Word response structure and Qt writer with staged validation. PowerPoint's picker offers built-in templates only; generation and developer CLI import remain available. Alex reports that PDF generation from a prompt and click-through of the new screens passed from source. |
| Create and Edit modes | Create new offers Write a new document and Pull information from documents into Excel, retaining separate inputs. Pull advances through columns/review and always produces XLSX; Write sends no sources. File rows and actions show progress. Edit document explains Word editing in 2.3.0; legacy editing stays disabled. Settings/mode/route switching freeze during work. |
| Extraction and review | DOCX and text-layer PDF reading coverage, column proposals, grounding, cancellation and XLSX Data/Evidence behavior remain unchanged. Word coverage issues now name the skipped structures. The saved grid displays number formats and hides Record; Record stays in workbook/Evidence. Every sectioned-source Data cell requires review while preserving valid values/types/formats. Save to Excel requires acknowledgement for highlighted values, reading problems or both, then uses native XLSX Save As. |
| Model warning | Queued /api/show metadata lookup; below 8B or unknown shows the PRD's non-blocking recommendation. No hardware check. Explicit local model selection is preserved and stale metadata is ignored. |
| Model evaluation | The [2.0.0 review-policy run](evaluation/2026-10-09-sectioned-review-policy.md) passes both criteria: whole-file 277/280 (98.93%, zero unflagged wrong); sectioned 33/40 (82.5%, informational), all 40 cells flagged and zero unflagged values. CLI exits 0. Settings, prompts, fixtures/labels and criteria are unchanged in 2.1.0. This is retained evaluation, not a new D1 model run. |
| MSI and portable packaging | One Nuitka 4.2.2 standalone payload, pinned WiX 5.0.2 per-user MSI and matching ZIP/checksums. The published 2.2.0 MSI is 61,204,345 bytes; executable version 2.2.0.0, derived upgrade probe 2.2.1. The tag workflow passed all 58 hosted lifecycle checks. Downloaded MSI/ZIP hashes match the manifest and GitHub asset digests; the manifest's own hash matches its GitHub digest. [Release evidence](releases/v2.2.0.json). Earlier [2.1.0 release](releases/v2.1.0.json), [Part B](builds/2.1.0-msi-ci.json) and [C2.7](builds/2.1.0-ui-ci.json) records retain their historical results. |
| Licensing | MIT for 2.0.0 onward, copyright (c) 2026 Alexandru Pop. Versions through v1.2.1 retain PolyForm Noncommercial 1.0.0. Application LICENSE and separately validated third-party notices remain packaged. No licensing change in 2.2.0. |
| Windows trust | Installer is unsigned. Exact warning/detection and downloaded-artifact reputation remain unverified; MSI does not establish publisher trust. |
| Later work | Edit for Word in 2.3.0 precedes table-row extraction and needs its own approved mockup/design/plan. Source-based Word/PDF reports, Excel/PowerPoint editing and scanned-PDF recognition remain deferred under PRD scope. |

## 2.2.0 B3 gate

Alex judged one sample per deck in PowerPoint with the question "would I show this to a client?". The set had four of Alex's real decks; Claude added four synthetic decks with fictional content to complete the source mix, one of them a stand-in for a Google Slides export. No deck name, path or content is recorded.

| Deck | Source | Route | Taken from the deck | Result |
|---|---|---|---|---|
| 1 | Company template made in PowerPoint (real) | Own layouts | | Fail: text on top of other text, sideways text, overflowing text, empty picture boxes |
| 2 | AI presentation tool (real) | Captured | Colors, fonts, background, logo | Pass |
| 3 | AI presentation tool (real) | Captured | Colors, fonts, background | Fail |
| 4 | Design tool (real) | Captured | Colors, fonts, background | Fail: the deck's design was lost |
| 5 | Built by hand on PowerPoint's white template (synthetic) | Captured | Colors, fonts, background, logo | Pass |
| 6 | Built by hand on PowerPoint's dark 4:3 template (synthetic) | Captured | Colors, fonts, background | Fail |
| 7 | Design-tool style with photo backgrounds (synthetic) | Captured | Colors, fonts, background, logo | Pass |
| 8 | Google Slides-style stand-in (synthetic) | Own layouts | | Fail: as Deck 1 |

- 5 of 8 decks failed, 3 of the 4 real ones. The own-layouts route is the import the app has shipped since 2.0; on a real company template it fills unsuitable layouts and overflows. The captured route was always readable but always the same plain layout; it passed only decks whose look is simple (a logo, one color, a photo background).
- A first run found that captured templates with a logo would not open in PowerPoint (a shape id above PowerPoint's limit). That defect was fixed in 973f263 before judging; it did not use the fix round. The test script cut sample titles mid-sentence and repeated one sentence; that made every sample look worse but does not explain overlapping, sideways or overflowing text or a lost design.
- Decision (Alex, 2026-10-12): drop the upload now, without the fix round. The two failure causes, fitting real company templates and copying more of a design than the bounded scope, could not be fixed in one bounded round. Task B5 runs; Task B4 is not executed.

B5 verification: the four new dialog cases failed before implementation (six retained cases passed), then all ten dialog cases passed within the 251-test targeted run. The full isolated source suite passed 1,076 tests in 42.10 seconds; one existing pytest cache-permission warning remains. The code follows revision 4's literal blocks and removals; R4-D1 and R4-D2 are reflected in the documentation. REPO_MAP was regenerated. No real decks or samples were copied or run by Codex, and no model, build, installer or qualification action was performed.

## 2.2.0 Part A verification

The planned test-first checks reproduced their expected failures before each change. Isolated full local source suites passed after A1 (1,079), A2 (1,081), A3 (1,085) and A4 (1,089). Targeted suites passed 23, 70, 137 and 315 tests respectively. The qualification script has zero parse errors and was not executed; packaging tools stay mocked in source tests. Existing prompts, model settings and evaluation fixtures/labels were preserved; no live-model evaluation was run.

The final block review found two bounded edge cases in the plan: cleanup errors could be hidden by progress clearing, and property-only revision markers could claim readable text was omitted. Regressions reproduced both; fixes keep cleanup errors visible and retain a truthful review warning for tracked formatting/row changes without changing extracted text. That follow-up suite passed 1,095 tests. The tracked-move follow-up now reports `w:moveFrom` and `w:moveTo` as `skipped_tracked_changes` with "Text in tracked changes was not read." Both regression cases first reproduced the missing warning, then passed while their `90` text remained absent from source units. The targeted source-reader suite passed 21 tests and the full isolated suite passed 1,142; REPO_MAP was regenerated. `smartTag`, `customXml` and `dir` handling and Part B are unchanged; one pytest cache-permission warning remains.

## 2.2.0 Part D verification

The new route, appearance and progress checks failed before their implementation.
Targeted source suites passed 130, 134 and 147 tests, then 150 after layout and stale
write-event follow-ups. The final isolated full suite passed **1,098 tests in 44.60
seconds**, with the existing pytest cache-permission warning. Existing behavioral
tests were migrated, not dropped. A full-run stack dump identified native `QTest.qWait`
blocking in the existing inspection-to-extraction test; its wait now uses pytest-qt's
timed event loop. Both handoff/cancellation cases passed 25 repetitions each and the
final suite passed without diagnostic hooks. The underlying native wait cause is
not proven. Production cancellation/closing algorithms remain unchanged.

`scripts/capture_screens.py` produced 13 synthetic 1280x800 states under
`.venv/screens-part-d`; rendered card-label checks show no grey backgrounds. The
README image is the new Pull-ready view. Captures stage fictional values without
model calls and use isolated profile paths; they do not establish model accuracy
or native installer behavior. REPO_MAP was regenerated. No dependencies, model
settings, evaluation corpus, engines, version or LICENSE changed. No packaging
tool or installer ran locally, and no hosted milestone was dispatched.

Part D review follow-ups: the column table keeps four full rows visible while
extracting at 1280x800; the progress row is compact and disabled selection is
light blue. The chosen template again reads `Template: <name>`. Geometry and
rendered-color regressions failed before the fix, then the targeted suite passed
153 tests and the isolated full suite passed 1,100 in 40.53 seconds. The existing
cache-permission warning remains. All 13 screens were recaptured and REPO_MAP was
regenerated; the README screenshot was retained because its hash did not change.

## 2.1.0 verification

| Part | Verification |
|---|---|
| Task 0 | CI split and isolated local testing policy complete; [baseline milestone](builds/2026-10-11-task0-baseline.json) passed the historical NSIS route. |
| Part A and logging follow-up | PDF content, line breaks, multipage output, staged failure behavior and generator log privacy are source-tested. Logging follow-up full suite: 1,017 passed. Generation paths omit the specified paths, prompt-derived names, slide content and exception text; retained metadata is file type, length where applicable and exception class. Alex reported source PDF and screen click-through acceptance on 2026-10-12. |
| Part B | Local suite reached 1,024. [Hosted milestone](builds/2.1.0-msi-ci.json) verifies old-NSIS refusal, install, shortcut targets/registration, 20-second offscreen startup without Ollama, same-version repair, synthetic major upgrade and settings-preserving uninstall. Publication skipped. |
| Part C1 | [HTML mockup](design/document-workspace.html) approved by Alex on 2026-10-12. Acknowledgement for reading problems as well as highlighted values is included. |
| Part C2 | Accepted; [C2.7 evidence](builds/2.1.0-ui-ci.json) records the source walkthrough, six screenshots, passing hosted suite/build, all 57 lifecycle checks, artifacts and matching hashes. Publication skipped. |
| C2 follow-ups | Full local suites: 1,072 and 1,077 passed. Thread/dialog fixes and central-background correction accepted. [UI evidence](builds/2026-10-12-c2-ui-followup.json) records six refreshed 1280x800 images, 19 rendered label checks and zero grey strips. |
| D1 | Release documentation and notes complete and accepted. Local suite: 1,077 passed. The [final manual milestone](https://github.com/alexnosx/Simplicitor/actions/runs/38217184344) passed on d2010e5; the later release tag points to the tested README correction 2202cce. Published-release verification is recorded separately. |

The final README correction passed 1,077 isolated local source tests and its [push test run](https://github.com/alexnosx/Simplicitor/actions/runs/38232604557) before tagging. The tag workflow passed 1,077 hosted source tests and all 57 MSI lifecycle checks. Alex reported source PDF-from-prompt and screen click-through checks passed; this user acceptance is distinct from the hosted installer check.

The C2 source walkthrough used local qwen3:8b-q4_K_M and two synthetic files: four proposed columns, two saved rows and eight Evidence rows. Four non-verbatim proposals required acknowledgement. The Save As boundary supplied a workspace path and real extraction/writer/save/cleanup workers ran; source hashes were unchanged. It is a functional sample, not a new accuracy gate. [README](../README.md#run-from-source-without-building) has launch and fixture steps.

The hung 80592bb push run was cancelled. Its quiet log records 720 outcomes (68%) without a test node or stack, so the exact blocked test and historical cause remain unproven. The C2.3 local abort names test_import_unexpected_status_shows_error_stays_selection; keep the incidents linked. Controlled regressions exposed early template-dialog dismissal before native thread exit and GUI-blocking teardown joins. Results now wait for joined ownership; cleanup polls non-blocking completion. Headless tests reject unmocked dialogs. CI has a 15-minute tests-job limit, verbose nodes and a 60-second stack dump. [Investigation evidence](builds/2026-10-12-c2-test-followup.json) records the limitations and the initial diagnostic's profile-redirection mistake; the empty real app-data directory was left untouched.

All current local source suites use USERPROFILE, APPDATA and LOCALAPPDATA under .venv/test-home and a workspace basetemp. Synthetic temporary-file creation/deletion is permitted. No installers, uninstallers, msiexec, Windows Sandbox, WiX, build.py or qualification run on Alex's PC; no tools/dependencies are installed locally. Full builds and lifecycle actions run on the hosted GitHub Windows runner only.

Hosted lifecycle checks do not establish every native UI interaction, a clean machine without developer Python/Office, native Excel display, or SmartScreen reputation. The complete packaged extraction walkthrough remains unverified. Legacy manipulator defects (text-ID coercion and omitted DOCX tables) do not describe the independent extraction route and cannot be reached through Edit document.

## Benchmark environment

B1, recorded from read-only inspection on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; recorded driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reported version 0.32.13.

CPU/OS facts came from registry reads and memory from the Windows API; CIM queries were unavailable. Prior metadata discovery is not a quality test. [Architecture](superpowers/specs/2026-10-08-document-architecture-design.md#model-requests) owns request settings. Hardware is benchmark context, not a product eligibility check.

## Open decisions

- Exact Windows warning/detection and tested unsigned artifact behavior.

## Next step

Resolve A8's test setup conflict with the repository-local temporary-folder policy, then rerun its 27 targeted tests and the expected 1,256-test isolated full suite. Part A is incomplete; Part B has not started.

Input from Claude's review: in the app, ask to discard after the new file is picked, so cancelling the file picker keeps the current work.
