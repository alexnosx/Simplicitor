# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit / v1.2.1 safety patch | Edit remains enabled with known reconstruction, truncation, empty-response, and filename-collision hazards. Independent disabling/release work is planned. |
| Selected-model warning | Current UI uses the older small-model threshold and hides unknown sizes; selected-model recommendation warning is planned. |
| Structured readers, column proposals, and extraction | Reading primitives/libraries exist; the new file-record pipeline is planned. |
| Model evaluation | No labelled candidate scores have been produced. The planned early gate reads actual fixture files and calls Ollama directly, one whole file per request. |
| Saved XLSX grid and Save As | Planned. |
| Standalone installer and portable ZIP | Planned; current build produces an unsigned onefile executable. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later extraction/editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and plan | Revised for Alex's review decisions; awaiting approval before application/harness code. |

Earlier source regression evidence: the source reviewed on 2026-10-07 passed 668 tests with an isolated test home. Known additional defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths.

## Benchmark environment

B1, recorded from read-only inspection on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; recorded driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reported version 0.32.13.

CPU/OS facts came from registry reads and memory from the Windows API; CIM queries were unavailable. Prior metadata discovery is not a quality test. [Architecture](superpowers/specs/2026-10-08-document-architecture-design.md#model-requests) owns request settings. Hardware is recorded only as benchmark context.

## Open decisions

- Alex's approval of the revised plan and remaining implementation proposals, including DOCX page accounting and text-layer threshold.
- Passing evaluation candidate after labelled scoring.
- Alex's license decision, owned by [PRD.md](../PRD.md#license-decision); LICENSE remains unchanged.
- Alex's explicit go to publish the separately qualified safety release.
- Exact Windows warning/detection and tested unsigned artifact behavior.

## Next step

Review and approve the revised plan. Prepare the independent safety patch/release first, then run the actual-file stop gate before dependent extraction work. Stop and report if none passes. No application/harness changes or model benchmark are included in this documentation revision.
