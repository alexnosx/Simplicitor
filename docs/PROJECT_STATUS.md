# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit / v1.2.1 safety patch | Published as [v1.2.1 Latest](https://github.com/alexnosx/Simplicitor/releases/tag/v1.2.1). Public executable version and SHA-256 verified; [release evidence](releases/v1.2.1.json). Local build/smoke checked; clean-machine walkthrough waived under the [patch exception](code-signing.md). |
| Selected-model warning | Current UI uses the older small-model threshold and hides unknown sizes; selected-model recommendation warning is planned. |
| Structured readers, column proposals, and extraction | Plain-Python core implemented: anchored sources, currency/ordinal conversion, blank-to-null handling, shared-client requests, column suggestions, conservative context sections, field accumulation, coverage, and cancellation. Not yet connected to the UI. |
| Model evaluation | Alex selected qwen3:8b. Its [currency/null rerun](evaluation/2026-10-08-task1-qwen-currency-null.md) passes the unchanged Task 1 gate. Production and saved-XLSX release evaluation remain pending. |
| Saved XLSX grid and Save As | Task 3 core implemented: typed/literal Data and Evidence, saved-cell review mapping, highlighted proposals/blanks, owned jobs, acknowledged Save As copying, and retention cleanup. Native dialog/grid wiring remains Task 4. |
| Standalone installer and portable ZIP | Planned; current build produces an unsigned onefile executable. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later extraction/editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and plan | Tasks 0 through 2 accepted; Task 3 authorized. Tasks remain numbered 0 to 6. |

The current source passed 866 tests with isolated user folders, including 61 Task 3 checks. Existing Create/template regressions pass. Task 3 checks reopen real XLSX files, exercise source aliases and failed copy/replace operations, invalidate stale candidates, and check owned cleanup at the retention boundary. Task 2 checks use controlled model replies; live-model accuracy remains the accepted Task 1 report. Known legacy defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths; the new route does not share legacy reading/writing behavior. Source tests and the synthetic model gate do not establish native Excel display, packaged UI, or clean-machine readiness.

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

Task 3 core is complete and locally verified. Stop before Task 4; no new UI or native Save As dialog has been implemented. Full-pipeline live-model and saved-output qualification remain Task 6.
