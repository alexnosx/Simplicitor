# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit / v1.2.1 safety patch | Published as [v1.2.1 Latest](https://github.com/alexnosx/Simplicitor/releases/tag/v1.2.1). Public executable version and SHA-256 verified; [release evidence](releases/v1.2.1.json). Local build/smoke checked; clean-machine walkthrough waived under the [patch exception](code-signing.md). |
| Selected-model warning | Queued /api/show lookup for the selected model; below 8B or unknown shows the PRD's dismissible, non-blocking recommendation. Loaded-model polling preserves an installed explicit selection and stale metadata is ignored. |
| Structured readers, column proposals, and extraction | Task 4 connects the existing core to the default From source files workspace: source picker/drop, editable/confirmed columns, conditional date-order settings, background extraction, coverage, and cooperative cancellation. From prompt hosts existing Create/templates; Edit is hidden. |
| Model evaluation | Alex selected qwen3:8b. Its [currency/null rerun](evaluation/2026-10-08-task1-qwen-currency-null.md) passes the unchanged Task 1 gate. Production and saved-XLSX release evaluation remain pending. |
| Saved XLSX grid and Save As | Saved read-only Data grid and Evidence panel implemented, with highlighted proposals/blanks, acknowledgement, native .xlsx Save As and ordinary overwrite confirmation. Failed saves retain review. Reruns/cancellation invalidate prior review; normal close waits for worker cleanup before deleting owned jobs. |
| Standalone installer and portable ZIP | Task 5 build route implemented: pinned Nuitka 4.2.2 standalone payload, built-in current-user NSIS installer, matching portable ZIP and SHA-256 inventory. Local build, 896-file ZIP/payload/hash comparison, generated uninstall correction, portable startup/bundled runtimes/template seeding, and normal close pass; install/upgrade/uninstall and clean-Windows qualification pending. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later extraction/editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and plan | Tasks 0 through 4 accepted. Two review-grid fixes and Task 5 packaging are current scope; Task 6 not started. |

The current source passed 968 tests with isolated user folders. The two review-grid fixes show saved decimal precision and omit Record from the grid while retaining it in Evidence. UI unit-test discovery is offline; the native sample uses the real runtime. Existing Create/template regressions pass. Task 4 checks cover column confirmation, supported numeric separators, selected-model warnings/empty discovery, bounded anchored coverage display, saved Evidence/flags, native-dialog delegation, source refusal, failed/confirmed overwrite, late cancellation, duplicate operations, and close/finished-handler ordering. The native Windows walkthrough used qwen3:8b-q4_K_M and invoice-01.docx: four suggested columns, confirmation/extraction, a literal ID/numeric total/date, selected-cell Evidence, Save As cancellation/new output/observed overwrite confirmation, unchanged source bytes, and normal-close job cleanup all passed. The exported bytes matched the candidate. This is a functional sample, not the Task 6 accuracy gate or installer qualification. [README](../README.md#run-from-source-without-building) has launch and fixture steps.

Numeric leading-zero and Excel precision failures remain flagged literals. Live-model accuracy remains the accepted Task 1 report; full-pipeline qualification is pending. Known legacy defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths; the new route does not share legacy reading/writing behavior. Portable startup uses the bundled Python runtime and Qt libraries from a working directory outside the checkout; both templates seed correctly. The complete packaged extraction walkthrough was not verified because native automation captured a clipped window and could not reliably drive its offscreen controls. No display settings were changed. Native Excel display and clean-machine readiness remain unverified.

## Benchmark environment

B1, recorded from read-only inspection on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; recorded driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reported version 0.32.13.

CPU/OS facts came from registry reads and memory from the Windows API; CIM queries were unavailable. Prior metadata discovery is not a quality test. [Architecture](superpowers/specs/2026-10-08-document-architecture-design.md#model-requests) owns request settings. Hardware is recorded only as benchmark context.

## Open decisions

- Alex's license decision, owned by [PRD.md](../PRD.md#license-decision); LICENSE remains unchanged.
- Exact Windows warning/detection and tested unsigned artifact behavior.

## Next step

Task 5 implementation and local artifact checks are complete, with [packaging evidence](builds/2026-10-08-task5.json). Full packaged UI, installation, upgrade, uninstall, and clean-Windows qualification remain pending: no clean environment is available, and Alex requires explicit approval for PC installation/registry/shortcut changes. Do not tag, publish, or start Task 6.
