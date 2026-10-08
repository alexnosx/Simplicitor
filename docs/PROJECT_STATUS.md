# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit / v1.2.1 safety patch | Disabled in the UI and guarded before I/O at both entry points. Local artifact built and startup smoke checked; clean-machine qualification and publication remain pending. See [artifact evidence](releases/v1.2.1-local.json). |
| Selected-model warning | Current UI uses the older small-model threshold and hides unknown sizes; selected-model recommendation warning is planned. |
| Structured readers, column proposals, and extraction | Anchored DOCX/PDF readers and literal grounding implemented independently of legacy Edit. Production requests, column proposals, and conditional sectioning remain planned. |
| Model evaluation | Both candidates passed the actual-file Task 1 gate. [Measured scores and recommendation](evaluation/2026-10-08-task1.md); production and saved-XLSX release evaluation remain pending. |
| Saved XLSX grid and Save As | Planned. |
| Standalone installer and portable ZIP | Planned; current build produces an unsigned onefile executable. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later extraction/editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and plan | Approved with whole-file-first extraction and tasks renumbered 0 to 6. Tasks 0 and 1 authorized. |

The current source passed 709 tests with isolated user folders. Existing Create/template regressions pass. Known legacy defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths; the new readers do not share legacy extraction behavior. Source tests and the synthetic model gate do not establish packaged UI or clean-machine readiness.

## Benchmark environment

B1, recorded from read-only inspection on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; recorded driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reported version 0.32.13.

CPU/OS facts came from registry reads and memory from the Windows API; CIM queries were unavailable. Prior metadata discovery is not a quality test. [Architecture](superpowers/specs/2026-10-08-document-architecture-design.md#model-requests) owns request settings. Hardware is recorded only as benchmark context.

## Open decisions

- Recommended production candidate: qwen3:8b, based on equal accuracy and lower review burden in the [Task 1 report](evaluation/2026-10-08-task1.md).
- Alex's license decision, owned by [PRD.md](../PRD.md#license-decision); LICENSE remains unchanged.
- Alex's explicit go to publish the separately qualified safety release.
- Exact Windows warning/detection and tested unsigned artifact behavior.

## Next step

Task 1 is complete and both candidate scores have been reported. Stop before Task 2. Finish clean-machine qualification of the independently prepared safety patch; v1.2.1 publication remains pending Alex's explicit go.
