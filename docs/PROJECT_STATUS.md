# Simplicitor project status

Updated 2026-10-12 after 2.2.0 B1-B3 implementation; the real-deck gate remains pending. [PRD.md](../PRD.md) owns requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md) and the [2.2.0 plan](superpowers/plans/2026-10-12-release-2.2.0.md) are the current review set. The [2.1.0 plan](superpowers/plans/2026-10-09-release-2.1.0.md) and [2.0.0 extraction plan](superpowers/plans/2026-10-08-first-release-extraction.md) retain their earlier execution records.

## Current status

| Area | Current state |
|---|---|
| Published releases | [v2.1.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.1.0) is published and verified as Latest with Simplicitor-2.1.0.msi, portable ZIP, checksums and the tagged notes as its body. The tag points to 2202cce; [release evidence](releases/v2.1.0.json). Earlier [v2.0.0](releases/v2.0.0.json) and [v1.2.1](releases/v1.2.1.json) releases and licenses remain unchanged. |
| 2.1.0 release | Task 0, Parts A/B/C1/C2, both C2 follow-ups, D1 and the final README corrections are accepted. Published from the tested README commit 2202cce; MSI version 2.1.0 and executable version 2.1.0.0. The [tag workflow](https://github.com/alexnosx/Simplicitor/actions/runs/38233039100) passed source tests, build, MSI qualification and publication. Downloaded hashes and the release body are verified in the release record. |
| 2.2.0 Part A | A1-A4 complete in source: finished extraction progress clears while final messages stay; source-aware prompt hints and Settings guidance; one shared version for UI/build/upgrade qualification; named Word reading problems and a general review heading. The product version remains 2.1.0 until E1; no 2.2.0 build or release. |
| 2.2.0 B1-B3 | Effective style capture and routing, the restyled bundled-template builder, shared prepare_template and the sample-deck script are implemented and source-tested. Claude's review and Alex's real-deck B3 gate are pending. The app import route is unchanged until B4; B4/B5 and later implementation have not started. |
| Prompt creation and templates | Word, Excel and PowerPoint generation remain available. PDF uses the existing Word response structure and Qt writer with staged validation. PowerPoint's template picker/import/generation remains available. Alex reports that PDF generation from a prompt and click-through of the new screens passed from source. |
| Create and Edit modes | Create new uses Describe, optional sources, Choose columns, Review and save, then Saved. Edit document is explanatory only; legacy editing remains disabled. Settings/mode switching freeze during work. |
| Extraction and review | DOCX and text-layer PDF reading coverage, column proposals, grounding, cancellation and XLSX Data/Evidence behavior remain unchanged. Word coverage issues now name the skipped structures. The saved grid displays number formats and hides Record; Record stays in workbook/Evidence. Every sectioned-source Data cell requires review while preserving valid values/types/formats. Save to Excel requires acknowledgement for highlighted values, reading problems or both, then uses native XLSX Save As. |
| Model warning | Queued /api/show metadata lookup; below 8B or unknown shows the PRD's non-blocking recommendation. No hardware check. Explicit local model selection is preserved and stale metadata is ignored. |
| Model evaluation | The [2.0.0 review-policy run](evaluation/2026-10-09-sectioned-review-policy.md) passes both criteria: whole-file 277/280 (98.93%, zero unflagged wrong); sectioned 33/40 (82.5%, informational), all 40 cells flagged and zero unflagged values. CLI exits 0. Settings, prompts, fixtures/labels and criteria are unchanged in 2.1.0. This is retained evaluation, not a new D1 model run. |
| MSI and portable packaging | One Nuitka 4.2.2 standalone payload, pinned WiX 5.0.2 per-user MSI and matching ZIP/checksums. The published MSI is 61,187,961 bytes. The tag workflow passed all 57 hosted lifecycle checks. Release asset digests and both artifact hashes match; all 535 portable payload files match the manifest. [Release evidence](releases/v2.1.0.json). Earlier [Part B](builds/2.1.0-msi-ci.json) and [C2.7](builds/2.1.0-ui-ci.json) milestones retain their historical results. |
| Licensing | MIT for 2.0.0 onward, copyright (c) 2026 Alexandru Pop. Versions through v1.2.1 retain PolyForm Noncommercial 1.0.0. Application LICENSE and separately validated third-party notices remain packaged. No licensing change in 2.1.0. |
| Windows trust | Installer is unsigned. Exact warning/detection and downloaded-artifact reputation remain unverified; MSI does not establish publisher trust. |
| Later work | Selective editing, source-based Word/PDF reports, table-row extraction and scanned-PDF recognition remain deferred under PRD scope. |

## 2.2.0 B1-B3 verification

The new tests failed on the expected missing modules/functions before implementation. Targeted suites passed after B1 (28), B2 (6) and B3 (11); full isolated source suites passed 1,123, 1,129 and 1,140 tests respectively. Counts include the six accepted Part A follow-up cases. The code follows the reviewed revision-3 blocks without implementation deviations. REPO_MAP was regenerated after each task.

Tests use synthetic decks only and cover inherited styles/backgrounds, multiple masters, corrupt image pixels, both preparation routes, rendering each captured slide type, saved-package checks and refusal of overlapping source/output folders. No real decks or PowerPoint visual checks were run; no gate score is recorded. No AI model, installer, packaging tools or qualification script was run. The existing pytest cache-permission warning remains.

## 2.2.0 Part A verification

The planned test-first checks reproduced their expected failures before each change. Isolated full local source suites passed after A1 (1,079), A2 (1,081), A3 (1,085) and A4 (1,089). Targeted suites passed 23, 70, 137 and 315 tests respectively. The qualification script has zero parse errors and was not executed; packaging tools stay mocked in source tests. Existing prompts, model settings and evaluation fixtures/labels were preserved; no live-model evaluation was run.

The final block review found two bounded edge cases in the plan: cleanup errors could be hidden by progress clearing, and property-only revision markers could claim readable text was omitted. Regressions reproduced both; fixes keep cleanup errors visible and retain a truthful review warning for tracked formatting/row changes without changing extracted text. That follow-up suite passed 1,095 tests. The tracked-move follow-up now reports `w:moveFrom` and `w:moveTo` as `skipped_tracked_changes` with "Text in tracked changes was not read." Both regression cases first reproduced the missing warning, then passed while their `90` text remained absent from source units. The targeted source-reader suite passed 21 tests and the full isolated suite passed 1,142; REPO_MAP was regenerated. `smartTag`, `customXml` and `dir` handling and Part B are unchanged; one pytest cache-permission warning remains.

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

Claude reviews the completed implementation, then Alex judges the samples for the [B3 real-deck gate](superpowers/plans/2026-10-12-release-2.2.0.md#task-b3-one-preparation-step-and-the-test-run-with-alexs-decks-gate). Generate samples from the repository with `.venv/Scripts/python.exe scripts/sample_deck_styles.py "<decks folder>" "<separate output folder>"`; results stay local, and tracked gate results use anonymized deck labels. Stop before B4/B5 until the gate decision and next scope. Claude and Alex own the C1 mockup. Part D follows mockup approval; E1 owns the hosted packaging milestone and E2 still needs explicit release go. v2.1.0 remains published and verified; its [release record](releases/v2.1.0.json) owns the publication evidence. Historical releases remain unchanged.
