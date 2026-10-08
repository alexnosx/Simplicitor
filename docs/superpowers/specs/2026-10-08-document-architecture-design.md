# Simplicitor first-release architecture

The release contract, later milestones, and acceptance values are in [PRD.md](../../../PRD.md). Current state is in [project status](../../PROJECT_STATUS.md). This design replaces the earlier Office-backed proposal; its execution steps are in the [single first-release plan](../plans/2026-10-08-first-release-extraction.md).

## Structure

Keep the Python/PySide6 application and existing Create/template engines. Add a small plain-Python extraction package and one Qt worker adapter. Existing Create continues through its current workers; extraction has a dedicated candidate writer and review route.

~~~mermaid
flowchart TD
    UI[Create workspace] --> OLD[Existing Create and template workers]
    UI --> WORKER[Extraction QObject worker]
    WORKER --> CORE[Extraction core]
    CORE --> READERS[python-docx and pdfplumber readers]
    CORE --> MODEL[Existing OllamaClient]
    CORE --> WRITE[openpyxl candidate writer]
    WRITE --> GRID[Saved workbook grid and evidence]
    GRID --> SAVE[Approve exact candidate and publish new file]
~~~

The extraction core has no Qt dependency. Readers consume immutable source bytes and produce anchored units. The pipeline owns structural sections, known record identities, field proposals, grounding, and coverage. The writer materializes those results; publication accepts a reviewed candidate identity rather than another model request.

## Module responsibilities

Exact signatures and tests belong to the plan's Interfaces blocks.

| Path proposed for implementation | Responsibility |
|---|---|
| simplicitor/extraction/models.py | Shared column, source, record, field, issue, section, result, profile, and candidate data contracts; response-schema construction. |
| simplicitor/extraction/grounding.py | Whitespace-normalized evidence matching and strict typed derivation, reused by evaluation and production. |
| simplicitor/extraction/source_readers.py | New DOCX/PDF reading entry points adapted from legacy reading logic, with anchors, table structure, limits, and coverage issues. |
| simplicitor/extraction/sectioning.py | Mode-specific record roster and non-overlapping structural sections, with open-record carry state. |
| simplicitor/extraction/pipeline.py | Schema-constrained calls, parsing, field validation/merging, issue retention, and cooperative cancellation. |
| simplicitor/extraction/xlsx_writer.py | Dedicated typed Data/Evidence workbook generation and saved-file verification. |
| simplicitor/extraction/jobs.py | Private candidate directories, hashes, approval invalidation, exclusive publication, and owned-file cleanup. |
| scripts/evaluate_extraction.py | Synthetic-fixture CLI evaluation and aggregate scoring; no UI dependency. |
| simplicitor/app/workers/extraction_worker.py | QObject/QThread adapter around core operations. |
| simplicitor/app/widgets/extraction_panel.py | Sources, column confirmation, mode selection, progress, and grid/evidence review. |
| simplicitor/app/widgets/create_workspace.py | Host extraction and the existing CreatePanel without changing its generation behavior. |

Use existing libraries rather than introducing a PDF service, database, agent harness, or extra runtime. Keep shared style/configuration in the existing defaults module. The legacy manipulator remains available to its existing tests and exception imports; it is not the new reader dependency.

## Source and record representation

Source identity combines a job-local ID and the original bytes' hash. Keep immutable bytes/units through the job. Readers expose a file-content view and a table-record view; sectioning consumes the appropriate view once. A PDF page's text and its detected table representation are alternatives, not overlapping model submissions.

Known record IDs come from source/file or table-row structure before model calls. The pipeline fills every requested column for every known record. It never lets model omission shrink the output roster. Continued table headers define mapping/context, not extra data rows. Unsupported structures and ambiguous continuations become explicit issues.

The main file mode can collect a known file record's fields across sections. This does not introduce discovery of multiple narrative records. Carry verified values and anchors, not repeated source text. Same-value field observations can retain the first evidence; contradictory observations become flagged alternatives. No record-deduplication subsystem is needed.

## Model and grounding boundary

Generate schema from the confirmed columns and allowed record IDs using the existing client's output-format argument. Optional extraction profile arguments must preserve existing callers' defaults. Parsing is strict JSON; an invalid section creates issues and missing/flagged fields rather than silently disappearing.

Grounding runs after parsing and again when assembling final records. Validate against immutable anchored units, not text invented by a prior model call. Code applies the derivation rules owned by PRD.md. Labels never influence flags. Keep the semantic-error counterexample in the scorer tests so evidence consistency cannot be mistaken for accuracy.

## Candidate and review boundary

Write to a private job directory, reopen the actual candidate, and build the review grid from that saved file. Keep raw proposals and errors in Evidence rather than promoting failed fields to valid typed Data values.

Binding candidate hash, source hashes, and confirmed request/columns/mode makes approval specific. Schema changes or a new extraction discard approval. Publication stages a verified copy in the destination directory and performs a no-replacement rename. A collision or write failure leaves both the source and existing destination unchanged. Only then emit saved success.

Readers and model calls run off the UI thread. Cancellation is checked at boundaries and after blocking calls; late responses cannot publish a cancelled job. No Office process isolation is part of this design.

## Evaluation dependency order

The early CLI gate exercises models using independent canonical units supplied with synthetic fixture documents. It needs the shared contracts, schema, and grounding checker, but not production readers or UI. Expected labels are loaded only by the scorer.

After the early gate passes, implement readers and sectioning and rerun the selected model on actual fixture documents. This second check establishes end-to-end input fidelity. It prevents the early model-only result being presented as evidence that PDF/DOCX reading works. A failed gate stops dependent work.

Packaging can prepare a standalone build in parallel and later incorporate extraction modules. It does not authorize UI work before evaluation or permit progress around a failed quality gate.

## Later architecture

The exact retained contracts live under [post-first-release requirements](../../../PRD.md#post-first-release-requirements). Later editing uses bounded OOXML patches with package-part preservation checks. Shared-string aliases and XML serialization boundaries require a separate design. Office can assist disposable preview/recalculation copies only; it must not rewrite the preserved output.

Reporting waits for the PRD's closed operation contract. Recognition and narrative-record discovery require separate milestones. None introduces first-release dependencies.

## Technical references

- [python-docx document order and tables](https://python-docx.readthedocs.io/en/latest/api/document.html).
- [pdfplumber extraction capabilities and OCR limits](https://github.com/jsvine/pdfplumber#comparison-to-other-libraries).
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [generate API](https://docs.ollama.com/api/generate).
- [openpyxl cell binding and string typing](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/cell/cell.html).

Version compatibility, schema behavior, literal-cell round trips, and packaging must be verified by the plan's checks rather than inferred from documentation.
