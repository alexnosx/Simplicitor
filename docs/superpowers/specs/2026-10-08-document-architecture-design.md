# Simplicitor first-release architecture

[PRD.md](../../../PRD.md) owns requirements and acceptance values. [Project status](../../PROJECT_STATUS.md) owns implementation state and the recorded benchmark machine. Exact interfaces and execution checks belong to the [single plan](../plans/2026-10-08-first-release-extraction.md). This revision follows Alex's review of f565f81.

## Structure

Keep the Python/PySide6 application and existing Create/template engines. Add a small plain-Python extraction package with a Qt worker adapter. The same worker can inspect sources, propose columns, and extract using frozen confirmed settings; these are separate actions. Existing generation keeps its current workers.

~~~mermaid
flowchart TD
    UI[Create workspace] --> OLD[Existing Create and template workers]
    UI --> WORKER[Extraction QObject worker]
    WORKER --> READERS[Anchored source readers]
    READERS --> PROPOSE[Model proposes columns from first source]
    PROPOSE --> CONFIRM[User edits and confirms columns]
    CONFIRM --> CORE[Sectioned extraction and grounding]
    CORE --> MODEL[Existing OllamaClient]
    CORE --> WRITE[Dedicated XLSX candidate writer]
    WRITE --> GRID[Saved workbook grid and evidence]
    GRID --> SAVE[Native Save As and staged copy]
~~~

The extraction core has no Qt dependency. Code enumerates one record per attachment, with a job-local ID independent of its filename. Source snapshots stay in memory during a run.

## Module responsibilities

| Path proposed for implementation | Responsibility |
|---|---|
| simplicitor/extraction/models.py | Column, source, file-record, proposal/result, issue, section, profile, candidate, and review-cell contracts; JSON schema builders. |
| simplicitor/extraction/grounding.py | Whitespace-normalized quote matching and deterministic English typed derivation. |
| simplicitor/extraction/source_readers.py | Independent DOCX/PDF readers adapted from legacy primitives, with anchors, limits, and coverage. |
| simplicitor/extraction/sectioning.py | Non-overlapping structural sections and file-record carry state. |
| simplicitor/extraction/pipeline.py | Column proposals, confirmed-schema calls, validation/merging, coverage, and cancellation. |
| simplicitor/extraction/xlsx_writer.py | Data/Evidence writing and reading the saved candidate for grid review. |
| simplicitor/extraction/jobs.py | One candidate per app-data job, staged Save As copying, source-path refusal, and age-based cleanup. |
| scripts/evaluate_extraction.py | Independent labels, model eligibility, aggregate scoring, and optional informational timings. |
| simplicitor/app/workers/extraction_worker.py | QObject/QThread adapter around core actions. |
| simplicitor/app/widgets/extraction_panel.py | Sources, request, proposed-column editor, progress, grid/evidence, and Save As. |
| simplicitor/app/widgets/create_workspace.py | Host extraction and the existing CreatePanel. |

Reuse existing document libraries and the Ollama client. Shared configuration belongs in simplicitor/app/config/defaults.py. The legacy manipulator stays available to existing tests and template exception imports; new readers do not depend on it.

## Source reading and sectioning

Adapt _extract_docx/_extract_pdf into an independent reader module, without their joined-string/truncation contract. Read immutable bytes after allocation checks.

DOCX body paragraphs use source_id#p:index; cells use source_id#t:table:r:row:c:cell, with zero-based structural indices including empty units. Read body paragraphs/tables in document order. Read each physical cell once when library views alias a merged cell; this is unit enumeration, not row continuation or record discovery. Flag unsupported structures rather than pretending whole-document coverage.

PDF page text uses source_id#page:number with one-based page numbers. Call page.extract_text() on each pdfplumber page; no PDF table detector or alternate table view is required. Retain page counts and unreadable-page issues.

Known record_id equals source_id. Same-named and identical-content files keep separate IDs and rows. Sections split only at paragraph, DOCX table-row, or PDF page boundaries, without overlapping source text. Keep a DOCX row's anchored cells together. Carry verified partial file fields/anchors across sections; agreeing values retain the first evidence and conflicts stay flagged. An oversized indivisible unit fails visibly. No record-deduplication subsystem is needed.

## Proposed implementation limits

These are implementation proposals reviewed with the plan, not PRD requirements or measurements. Store accepted settings once in defaults.py and reference them from the evaluation manifest.

| Setting | Proposal |
|---|---|
| DOCX page-equivalent accounting | max(1, ceil(extracted_body_characters / 3000)) per file, including supported table cells. Display estimates; do not use stale DOCX pagination metadata. |
| Allocation limits | 50 MiB per input file; 100 MiB input bytes per job; 100 MiB declared uncompressed DOCX package content per file. Check before expensive work. |
| PDF near-zero text | Fewer than 40 non-whitespace extracted characters per page. |
| Structural section budget | Up to 8000 UTF-8 source bytes, plus a conservative schema/request/carry-state context check. Reject oversized units without cutting text. |
| Generation profile | num_ctx=16384, num_predict=4096, temperature=0, seed=0, HTTP timeout=180 seconds. Freeze supported thinking settings per model before scoring. |
| Fit accounting | Interpret the supported 8 GB GPU class as 8 GiB (8192 MiB) for measured allocation checks. Record bytes as well as MiB. |
| Runtime setup for fit runs | One loaded candidate, one concurrent request; record Ollama parallelism, Flash Attention, and KV-cache type. Start with f16 KV cache; any alternative must be frozen and reevaluated. |

The timeout bounds a failed request; it is not a speed acceptance target. Proposal input uses the first source's leading complete structural units within the same budget, explicitly labelled a sample. Large first sources are still read fully for subsequent extraction. An empty/unreadable sample fails visibly; source content is never silently discarded from extraction.

## Model profile and fit check

Initial eligible candidates to test are [qwen3:8b-q4_K_M](https://ollama.com/library/qwen3:8b-q4_K_M) and [llama3.1:8b-instruct-q4_K_M](https://ollama.com/library/llama3.1:8b-instruct-q4_K_M). These are registry-verified tags/quantizations, not verified fits or quality results. Record local digest and /api/show details on the actual run.

For each candidate, load and exercise the exact generation profile above on B1, including a near-budget request. Inspect /api/ps for the matching digest: require context_length to match num_ctx, positive size, size_vram equal to size, and reported running allocation within the fit ceiling above. Missing fields, a different context, CPU offload, or an over-budget allocation makes it ineligible. Record observed process GPU allocation/headroom alongside the API snapshot; if the runtime's size accounting cannot establish weights plus KV-cache fit, report eligibility unverified. A small download alone is insufficient evidence.

B1 has more VRAM than the support minimum. Loading wholly onto B1 alone is insufficient: the measured footprint must also satisfy the minimum-class budget. Record runtime versions, weight quantization, KV-cache type, parallelism, context, and thinking settings; do not change them between fit verification and scoring. Accuracy is evaluated on that configuration, not inferred from B1's GPU or a larger model.

Optional reference runs may use the previously discovered qwen3.8:27b/Q4_K_M, qwen3.6:27b/Q4_K_M, and gemma4:12b-it-q8_0/Q8_0. Mark reference-only in the report and exclude them from configuration selection regardless of score. Follow the PRD stop gate when eligible models fail.

For the product warning, query the selected model's /api/show details, reuse existing metadata parsing, and handle unknown size explicitly. Selection changes must request that model's metadata even if a different model is loaded. Do not infer size from a tag or convert this warning into a generation block.

## Model and grounding boundary

Column proposals consume the request and first-source sample, with a constrained column-proposal schema. User-confirmed columns then determine the extraction response schema and record IDs. Malformed overall proposals produce an editable empty setup/error; a missing or unrecognized column type falls back to text.

Use the existing client's output_format argument. Optional extraction-only options/think/local_only arguments preserve existing generation callers. Parsing is strict JSON. Grounding validates against anchored snapshot units and the confirmed column type; labels never influence flags.

Implement English numeric/date grammar without process-locale dependence. Apply PRD separator defaults, English full/abbreviated month names, and numeric formats; detect genuinely ambiguous numeric dates during source inspection. Prompt for order only for affected date columns. Invalid proposed types fall back to text, preserving the ability to edit. Conflicting or unsupported conversions stay literal and flagged rather than being coerced.

## Workbook, review, and Save As

Use a dedicated openpyxl writer, not ExcelGenerator._coerce_value. Valid fields use confirmed types; failed fields with proposals use literal proposed strings and highlighted Data cells. Absent proposals are highlighted blanks. Evidence stores the proposal, quote, anchor, and issue. Force all text to data_type s after assignment, including formula-like content in both sheets.

Each job owns one candidate.xlsx under the app-data jobs directory. On a rerun, clear the old review immediately and replace the same candidate only after successful writing; an old candidate is never offered as the new result after failure. Reopen the saved workbook to produce review cells and Evidence mappings.

A native QFileDialog Save As provides normal overwrite confirmation. Pass the returned destination to the copy operation; refuse any normalized source path, including an existing source alias. Copy to a temporary file in the destination directory, close it, then rename/replace the chosen destination. An error leaves the previous destination intact, removes the temporary file when possible, and retains the review without a success banner. Cancellation of the dialog changes no files.

Normal close deletes the job after worker/reader handles finish. Startup scans only Simplicitor's job directories and removes those older than the retention period owned by PRD.md; younger jobs and unrelated files stay untouched. There is no orphan-recovery UI or separate approval ledger.

Workers use existing QObject/QThread patterns; cancellation is cooperative and late responses are ignored. No Office process isolation is part of this design.

## Evaluation and release order

The early CLI checks models against independently authored canonical fixture units, confirmed columns, and known file records before production readers/UI exist. Keep expected labels only in the scorer. Repeat the selected model on actual files and production sectioning before writer/UI work.

Evaluate the PRD accuracy and unflagged-error fractions against all scored slots, without rounding percentages before comparison. A semantic substitution that passes grounding is still an unflagged error. Record correct-value flag rates separately. Optional timings do not influence pass/fail, selection, publication, or release claims.

The v1.2.1 safety patch uses the existing build route, independently of extraction and its gates. Qualify its own artifact and prepare release notes; request Alex's explicit go before creating the publication-triggering tag. New installer preparation can run alongside model work and stops if the extraction gate fails.

## Later architecture and references

Retained editing/reporting/recognition contracts live under [post-first-release requirements](../../../PRD.md#post-first-release-requirements). Later editing uses bounded OOXML patches and package-part preservation checks; Office assists disposable preview/recalculation copies only.

- [python-docx document order and tables](https://python-docx.readthedocs.io/en/latest/api/document.html).
- [pdfplumber extraction capabilities](https://github.com/jsvine/pdfplumber#comparison-to-other-libraries).
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), [generate API](https://docs.ollama.com/api/generate), [running-model fields](https://docs.ollama.com/api/ps), and [KV-cache/parallelism settings](https://docs.ollama.com/faq).
- [openpyxl cell binding and string typing](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/cell/cell.html).

Runtime/packaged verification remains necessary; references alone are not fit or accuracy evidence.
