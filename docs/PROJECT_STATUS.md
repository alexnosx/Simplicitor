# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single implementation plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit | Still enabled in source. Known reconstruction, truncation, empty-response, and filename-collision hazards; separate disabling patch is planned. |
| Structured source readers and field extraction | Reading primitives/libraries exist; new anchored readers and extraction pipeline are planned. |
| Model evaluation | Candidates discovered locally; no inference, labelled scoring, or latency benchmark has run. |
| Saved XLSX grid and evidence review | Planned. |
| Standalone installer and portable ZIP | Planned; current build produces an unsigned onefile executable. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and first-release plan | Revised for the latest decisions; awaiting Alex's review before application/harness code. |

Earlier source regression evidence: the source baseline reviewed on 2026-10-07 passed 668 tests with an isolated test home. It does not establish extraction accuracy or package readiness. Known additional defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths. No application code was changed during this planning revision.

## Benchmark environment

B1, inspected read-only on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; nvidia-smi reports 24463 MiB VRAM and driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reports version 0.32.13.

The candidate names/quantizations and measurement definitions belong to [PRD evaluation gates](../PRD.md#proposed-limits-and-evaluation-gates). Discovery showed completion/thinking capabilities and no remote_host value for those candidates. This is availability evidence, not a local-only inference or quality test. CIM queries were unavailable; CPU/OS facts came from registry reads and memory from the Windows API, not the failed queries.

## Open decisions

- Alex's approval of the plan and proposed PRD numbers, including DOCX page-equivalent accounting and text-layer threshold.
- Passing model/configuration, supported thinking policy, measured latency, and the numeric timing target after evaluation.
- Alex's license decision, owned by [PRD.md](../PRD.md#license-decision); LICENSE remains unchanged.
- Exact Windows warning/detection and tested unsigned artifact behavior.
- Pilot documents/layout variation needed to validate table continuation and grounding beyond the synthetic gate.

## Next step

Review and approve the first-release plan. Execution begins with the separately planned safety patch and model evaluation; stop dependent work if the quality gate fails. Packaging preparation can progress alongside that work as the plan specifies. No commit, push, model evaluation, or implementation is included in this documentation task.
