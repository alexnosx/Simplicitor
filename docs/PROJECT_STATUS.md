# Simplicitor project status

Updated 2026-10-12 for 2.1.0 release preparation. [PRD.md](../PRD.md) owns requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md) and the [2.1.0 plan](superpowers/plans/2026-10-09-release-2.1.0.md) are the current review set. The [2.0.0 extraction plan](superpowers/plans/2026-10-08-first-release-extraction.md) retains its earlier execution record.

## Current status

| Area | Current state |
|---|---|
| Published releases | v2.0.0 was published and verified as Latest, with installer, portable ZIP, checksums and notes. Its tag points to 7793d61; [release evidence](releases/v2.0.0.json). The earlier [v1.2.1 safety patch](releases/v1.2.1.json) disabled legacy Edit. Historical assets/licenses are unchanged. |
| 2.1.0 release preparation | Task 0, Parts A/B/C1/C2 and both C2 follow-ups are complete and accepted. D1 aligns release documentation and notes. MSI version is 2.1.0; executable version is 2.1.0.0. No 2.1.0 tag or publication is authorized. The final D1 manual milestone must qualify the exact pushed documentation commit; its URL and result are reported before a tag decision. |
| Prompt creation and templates | Word, Excel and PowerPoint generation remain available. PDF uses the existing Word response structure and Qt writer with staged validation. PowerPoint's template picker/import/generation remains available. Alex owns the Part A manual PDF check. |
| Create and Edit modes | Create new uses Describe, optional sources, Choose columns, Review and save, then Saved. Edit document is explanatory only; legacy editing remains disabled. Settings/mode switching freeze during work. |
| Extraction and review | DOCX and text-layer PDF readers, column proposals, grounding, cancellation and XLSX Data/Evidence output remain unchanged. The saved grid displays number formats and hides Record; Record stays in workbook/Evidence. Every sectioned-source Data cell requires review while preserving valid values/types/formats. Save to Excel requires acknowledgement for highlighted values, reading problems or both, then uses native XLSX Save As. |
| Model warning | Queued /api/show metadata lookup; below 8B or unknown shows the PRD's non-blocking recommendation. No hardware check. Explicit local model selection is preserved and stale metadata is ignored. |
| Model evaluation | The [2.0.0 review-policy run](evaluation/2026-10-09-sectioned-review-policy.md) passes both criteria: whole-file 277/280 (98.93%, zero unflagged wrong); sectioned 33/40 (82.5%, informational), all 40 cells flagged and zero unflagged values. CLI exits 0. Settings, prompts, fixtures/labels and criteria are unchanged in 2.1.0. This is retained evaluation, not a new D1 model run. |
| MSI and portable packaging | One Nuitka 4.2.2 standalone payload, pinned WiX 5.0.2 per-user MSI and matching ZIP/checksums. The [Part B milestone](builds/2.1.0-msi-ci.json) and [C2.7 milestone](builds/2.1.0-ui-ci.json) passed hosted qualification. C2.7 MSI size: 61,187,961 bytes. These are earlier commits, not substitutes for the D1 build. |
| Licensing | MIT for 2.0.0 onward, copyright (c) 2026 Alexandru Pop. Versions through v1.2.1 retain PolyForm Noncommercial 1.0.0. Application LICENSE and separately validated third-party notices remain packaged. No licensing change in 2.1.0. |
| Windows trust | Installer is unsigned. Exact warning/detection and downloaded-artifact reputation remain unverified; MSI does not establish publisher trust. |
| Later work | Selective editing, source-based Word/PDF reports, table-row extraction and scanned-PDF recognition remain deferred under PRD scope. |

## 2.1.0 verification

| Part | Verification |
|---|---|
| Task 0 | CI split and isolated local testing policy complete; [baseline milestone](builds/2026-10-11-task0-baseline.json) passed the historical NSIS route. |
| Part A and logging follow-up | PDF content, line breaks, multipage output, staged failure behavior and generator log privacy are source-tested. Logging follow-up full suite: 1,017 passed. Generation paths omit the specified paths, prompt-derived names, slide content and exception text; retained metadata is file type, length where applicable and exception class. Manual PDF acceptance remains Alex's check. |
| Part B | Local suite reached 1,024. [Hosted milestone](builds/2.1.0-msi-ci.json) verifies old-NSIS refusal, install, shortcut targets/registration, 20-second offscreen startup without Ollama, same-version repair, synthetic major upgrade and settings-preserving uninstall. Publication skipped. |
| Part C1 | [HTML mockup](design/document-workspace.html) approved by Alex on 2026-10-12. Acknowledgement for reading problems as well as highlighted values is included. |
| Part C2 | Accepted; [C2.7 evidence](builds/2.1.0-ui-ci.json) records the source walkthrough, six screenshots, passing hosted suite/build, all 57 lifecycle checks, artifacts and matching hashes. Publication skipped. |
| C2 follow-ups | Full local suites: 1,072 and 1,077 passed. Thread/dialog fixes and central-background correction accepted. [UI evidence](builds/2026-10-12-c2-ui-followup.json) records six refreshed 1280x800 images, 19 rendered label checks and zero grey strips. |
| D1 | PRD, specs, status, changelog, README, generated map and [release notes](releases/v2.1.0-notes.md) prepared. Full isolated local source suite: 1,077 passed. Qualify that exact pushed documentation commit with the final [manual Build workflow](https://github.com/alexnosx/Simplicitor/actions/workflows/build.yml). No tag or publication. |

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

After a passing D1 final milestone on its exact documentation commit, wait for Alex's explicit go to tag and publish v2.1.0. The [release notes](releases/v2.1.0-notes.md) will be the tag-triggered release body. Published v2.0.0 and historical releases remain unchanged.
