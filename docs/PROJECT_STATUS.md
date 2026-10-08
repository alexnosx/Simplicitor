# Simplicitor project status

Updated 2026-10-08. [PRD.md](../PRD.md) owns release requirements; [architecture](superpowers/specs/2026-10-08-document-architecture-design.md), [UI design](superpowers/specs/2026-10-08-document-workspace-ui-design.md), and the [single plan](superpowers/plans/2026-10-08-first-release-extraction.md) are the review set.

## Current status

| Area | Current state |
|---|---|
| Existing prompt-only Create and PowerPoint templates | Present in v1.2 source; to be preserved. |
| Legacy Edit / v1.2.1 safety patch | Published as [v1.2.1 Latest](https://github.com/alexnosx/Simplicitor/releases/tag/v1.2.1). Public executable version and SHA-256 verified; [release evidence](releases/v1.2.1.json). Local build/smoke checked; clean-machine walkthrough waived under the [patch exception](code-signing.md). |
| Selected-model warning | Current UI uses the older small-model threshold and hides unknown sizes; selected-model recommendation warning is planned. |
| Structured readers, column proposals, and extraction | Anchored DOCX body/header/footer and PDF readers, token-bounded literal grounding, and ordinal date conversion implemented independently of legacy Edit. Production requests, column proposals, and conditional sectioning remain planned. |
| Model evaluation | Revised Task 1 gate complete on 28 files/280 fields: Qwen passes, Llama fails accuracy. [Scores, narrative breakdown, and recommendation](evaluation/2026-10-08-task1-rerun.md). Production and saved-XLSX release evaluation remain pending. |
| Saved XLSX grid and Save As | Planned. |
| Standalone installer and portable ZIP | Planned; current build produces an unsigned onefile executable. |
| Windows security block | Reported; exact warning/detection is still needed. |
| Later extraction/editing/reporting/recognition | Deferred under PRD scope, with separate designs required. |
| Documentation and plan | Approved with whole-file-first extraction and tasks renumbered 0 to 6. Tasks 0 and 1 authorized. |

The revised source passed 732 tests with isolated user folders, including the grounding/source-context regressions. Existing Create/template regressions pass. Known legacy defects include Excel text-ID coercion, omitted DOCX tables, and content-bearing diagnostic paths; the new readers do not share legacy extraction behavior. Source tests and the synthetic model gate do not establish packaged UI or clean-machine readiness.

## Benchmark environment

B1, recorded from read-only inspection on 2026-10-08:

- Intel Core Ultra 9 275HX; 63.4 GiB physical RAM reported by the Windows memory API.
- NVIDIA GeForce RTX 5090 Laptop GPU; recorded driver 592.01.
- Windows x64, build 26200, display version 25H2.
- Local Ollama API reported version 0.32.13.

CPU/OS facts came from registry reads and memory from the Windows API; CIM queries were unavailable. Prior metadata discovery is not a quality test. [Architecture](superpowers/specs/2026-10-08-document-architecture-design.md#model-requests) owns request settings. Hardware is recorded only as benchmark context.

## Open decisions

- Recommended production candidate: qwen3:8b, the sole passing candidate in the [revised Task 1 report](evaluation/2026-10-08-task1-rerun.md). Its narrative subgroup remains below the overall accuracy target.
- Alex's license decision, owned by [PRD.md](../PRD.md#license-decision); LICENSE remains unchanged.
- Exact Windows warning/detection and tested unsigned artifact behavior.

## Next step

Task 1 fixes and both revised candidate scores are complete. v1.2.1 is published and its public asset verified. Stop before Task 2; it has not started.
