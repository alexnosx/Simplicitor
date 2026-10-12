# Simplicitor project status

Updated 2026-10-12 after v2.1.0 publication and release verification. [PRD.md](../PRD.md) owns requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md) and the [2.1.0 plan](superpowers/plans/2026-10-09-release-2.1.0.md) are the current review set. The [2.0.0 extraction plan](superpowers/plans/2026-10-08-first-release-extraction.md) retains its earlier execution record.

## Current status

| Area | Current state |
|---|---|
| Published releases | [v2.1.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.1.0) is published and verified as Latest with Simplicitor-2.1.0.msi, portable ZIP, checksums and the tagged notes as its body. The tag points to 2202cce; [release evidence](releases/v2.1.0.json). Earlier [v2.0.0](releases/v2.0.0.json) and [v1.2.1](releases/v1.2.1.json) releases and licenses remain unchanged. |
| 2.1.0 release | Task 0, Parts A/B/C1/C2, both C2 follow-ups, D1 and the final README corrections are accepted. Published from the tested README commit 2202cce; MSI version 2.1.0 and executable version 2.1.0.0. The [tag workflow](https://github.com/alexnosx/Simplicitor/actions/runs/38233039100) passed source tests, build, MSI qualification and publication. Downloaded hashes and the release body are verified in the release record. |
| Prompt creation and templates | Word, Excel and PowerPoint generation remain available. PDF uses the existing Word response structure and Qt writer with staged validation. PowerPoint's template picker/import/generation remains available. Alex reports that PDF generation from a prompt and click-through of the new screens passed from source. |
| Create and Edit modes | Create new uses Describe, optional sources, Choose columns, Review and save, then Saved. Edit document is explanatory only; legacy editing remains disabled. Settings/mode switching freeze during work. |
| Extraction and review | DOCX and text-layer PDF readers, column proposals, grounding, cancellation and XLSX Data/Evidence output remain unchanged. The saved grid displays number formats and hides Record; Record stays in workbook/Evidence. Every sectioned-source Data cell requires review while preserving valid values/types/formats. Save to Excel requires acknowledgement for highlighted values, reading problems or both, then uses native XLSX Save As. |
| Model warning | Queued /api/show metadata lookup; below 8B or unknown shows the PRD's non-blocking recommendation. No hardware check. Explicit local model selection is preserved and stale metadata is ignored. |
| Model evaluation | The [2.0.0 review-policy run](evaluation/2026-10-09-sectioned-review-policy.md) passes both criteria: whole-file 277/280 (98.93%, zero unflagged wrong); sectioned 33/40 (82.5%, informational), all 40 cells flagged and zero unflagged values. CLI exits 0. Settings, prompts, fixtures/labels and criteria are unchanged in 2.1.0. This is retained evaluation, not a new D1 model run. |
| MSI and portable packaging | One Nuitka 4.2.2 standalone payload, pinned WiX 5.0.2 per-user MSI and matching ZIP/checksums. The published MSI is 61,187,961 bytes. The tag workflow passed all 57 hosted lifecycle checks. Release asset digests and both artifact hashes match; all 535 portable payload files match the manifest. [Release evidence](releases/v2.1.0.json). Earlier [Part B](builds/2.1.0-msi-ci.json) and [C2.7](builds/2.1.0-ui-ci.json) milestones retain their historical results. |
| Licensing | MIT for 2.0.0 onward, copyright (c) 2026 Alexandru Pop. Versions through v1.2.1 retain PolyForm Noncommercial 1.0.0. Application LICENSE and separately validated third-party notices remain packaged. No licensing change in 2.1.0. |
| Windows trust | Installer is unsigned. Exact warning/detection and downloaded-artifact reputation remain unverified; MSI does not establish publisher trust. |
| Later work | Selective editing, source-based Word/PDF reports, table-row extraction and scanned-PDF recognition remain deferred under PRD scope. |

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

v2.1.0 is published and verified; the [release record](releases/v2.1.0.json) owns its URL, Latest verification, workflow result, asset hashes and body comparison. Future extraction, editing, reporting or recognition work needs a separately approved scope. Historical releases remain unchanged.
