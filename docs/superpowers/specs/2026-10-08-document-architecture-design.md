# Simplicitor first-release architecture

[PRD.md](../../../PRD.md) owns requirements and acceptance values. [Project status](../../PROJECT_STATUS.md) owns current state and B1. [UI design](2026-10-08-document-workspace-ui-design.md) owns presentation; the [single plan](../plans/2026-10-08-first-release-extraction.md) owns signatures and checks. This revision follows Alex's review of a1cd16f.

## Structure

Keep Python/PySide6 and existing Create/template workers. Add a small plain-Python extraction package and one Qt adapter for source inspection, column suggestions, and extraction.

~~~mermaid
flowchart TD
    UI[Create workspace] --> OLD[Existing Create and template workers]
    UI --> WORKER[Extraction QObject worker]
    WORKER --> READERS[Anchored DOCX and PDF readers]
    READERS --> COLUMNS[Suggest and confirm columns]
    COLUMNS --> PIPE[Sectioned extraction and grounding]
    PIPE --> OLLAMA[Existing OllamaClient]
    PIPE --> XLSX[Data and Evidence workbook]
    XLSX --> GRID[Saved workbook grid]
    GRID --> SAVE[Native Save As and staged copy]
~~~

The core has no Qt dependency. Readers open sources read-only, close handles, and retain extracted units rather than uploaded file copies. Code owns one record per attachment, identified independently of filename.

## Module responsibilities

| Proposed path | Responsibility |
|---|---|
| simplicitor/extraction/models.py | Small shared source, column, field, issue, result, and candidate contracts; response schema. |
| simplicitor/extraction/source_readers.py | DOCX/PDF reading adapted from legacy primitives, with stable anchors and coverage. |
| simplicitor/extraction/grounding.py | Source quote matching, literal value-in-quote check, then English type conversion. |
| scripts/evaluate_extraction.py | Actual-file evaluation with direct Ollama HTTP calls, independent labels, and aggregate scoring. |
| simplicitor/extraction/sectioning.py | Non-overlapping structural sections for large production inputs. |
| simplicitor/extraction/pipeline.py | Column proposals, sectioned calls, field accumulation, issues, and cancellation. |
| simplicitor/extraction/xlsx_writer.py | Dedicated typed/literal workbook writing and saved-grid data reading. |
| simplicitor/extraction/jobs.py | Candidate folder, Save As copying, source-path refusal, and age-based cleanup. |
| simplicitor/app/workers/extraction_worker.py | QObject adapter for core actions. |
| simplicitor/app/widgets/extraction_panel.py | Sources, request, column editor, saved grid/evidence, and Save As. |
| simplicitor/app/widgets/create_workspace.py | Host extraction and the existing CreatePanel. |

Reuse declared document libraries. Configuration stays in defaults.py. The legacy manipulator remains for its tests and template exception imports; new readers are independent.

## Source reading and sectioning

Adapt _extract_docx/_extract_pdf into structured readers without truncation. DOCX body paragraphs use source_id#p:index; cells use source_id#t:table:r:row:c:cell with zero-based indices including empty units. Traverse paragraphs/tables in document order and enumerate physical cells once. Report unsupported structures.

PDF page text uses source_id#page:number with one-based page numbers. Call each pdfplumber page's extract_text(); retain page counts and zero/near-zero-text issues. File mode needs no PDF table extraction.

record_id equals source_id. Same-named or identical-content attachments keep separate rows. Production sends the whole file when its token count fits num_ctx minus prompt, schema, and reserved output tokens. Otherwise derive the section budget from the same remaining context and split at paragraph, DOCX table-row, or PDF page boundaries without overlap. Carry the file's accumulated values/anchors; retain agreeing evidence and flag conflicts. Oversized indivisible units become coverage issues.

## Implementation settings

Implementation values are approved. Store shared values once in defaults.py.

| Setting | Proposal |
|---|---|
| DOCX page equivalents | max(1, ceil(extracted_body_characters / 3000)) per file, including supported table cells. Display estimates. |
| Input file limit | 50 MiB per file. The aggregate page limit belongs to PRD.md. |
| PDF near-zero text | Fewer than 40 non-whitespace extracted characters per page. |
| Production input budget | num_ctx minus prompt, schema, and reserved output tokens, also accounting for carried fields on subsequent calls. Prefer a whole file; derive sections from the remaining context only when needed. Oversized indivisible units fail visibly. |
| Request settings | num_ctx=16384, num_predict=4096, temperature=0, seed=0, think=False, HTTP timeout=180 seconds. |

The early fixtures fit whole in one request and do not use sectioning. Production column suggestions use the first source's leading complete units within the request budget, labelled a sample; extraction still covers all supported units.

## Model requests

[PRD.md](../../../PRD.md#limits-and-evaluation-gates) names the evaluation candidates and reference-only policy. The selected-model parameter-size lookup uses existing /api/show metadata parsing. It drives the product warning and the evaluation candidate-size rule; no other hardware/model validation is added.

Task 1's CLI calls /api/generate directly through requests.Session with trust_env=False and a loopback URL check. It submits all anchored units of each fixture in one request, with confirmed fixture columns and a JSON response schema. Thinking is always off.

Task 2 adds optional options, think, and local_only arguments to OllamaClient.generate while preserving existing callers. Extraction calls use output_format for schema, think=False, and local_only for the same loopback/trust_env=False transport. Column suggestions use these same settings. Diagnostics contain aggregate metadata and short errors, not document content or raw response bodies.

## Grounding and conversion

Check the anchor against the file's extracted units and match the quote after whitespace normalization. Then require the model value to be a literal, case-sensitive substring of its quote for every type. Do not normalize the model value before this check. Code converts the verified span using confirmed English numeric/date settings; conversion failure retains the proposal as flagged text.

Test quotes with currency symbols, codes, and labels around the value, including the PRD amount example. A correctly quoted value assigned to the wrong column still counts as a semantic error in scoring.

Column suggestions consume the request and first-source sample. Users edit/confirm names and types; missing/unrecognized types fall back to text. Malformed suggestions retain editable setup. English date/number settings follow PRD.md.

## Workbook and Save As

Use a dedicated openpyxl writer. Valid fields use confirmed types; flagged proposals use highlighted literal strings, and absent proposals are highlighted blanks. Evidence maps every Data cell to its quote, anchor, and issue. Force text to data_type s, including formula-like strings.

Each app-data job has one candidate.xlsx. Rerunning clears review and replaces that candidate; a failed run cannot revive the old review. Read grid values/Evidence from the saved workbook.

Native Save As handles overwrite confirmation. Refuse a normalized source path, copy through a destination-folder temporary file, close it, then rename/replace. Write failure retains the previous destination and review, without saved success. Normal close removes the job after workers/handles finish; startup removes only owned jobs older than the PRD retention period.

Use existing QObject/QThread patterns and cooperative cancellation. The source readers never write back to supplied files.

## Evaluation and release order

Task 1 reads actual English DOCX/PDF fixtures and runs the single early stop gate. Labels are independently authored field expectations, not alternate source units. Score accuracy, unflagged errors, and review burden using shared grounding and Data-value projection.

After it passes, implement the production pipeline and UI. Task 2 has unit checks only. Task 6 adds the CLI's --full-pipeline option and labelled files exceeding one request context to score both whole-file and sectioned production paths as the final release check. Both paths use the same scorer; optional timings decide nothing.

The v1.2.1 safety release uses the existing build route and its own checks, independently of extraction. Publication requires Alex's explicit go. New installer preparation may run alongside extraction and stops if the early gate fails.

## Later architecture and references

[Post-first-release requirements](../../../PRD.md#post-first-release-requirements) retain editing, reporting, and recognition contracts. Later editing patches bounded OOXML nodes; Office supports disposable preview/recalculation copies only.

- [python-docx document order and tables](https://python-docx.readthedocs.io/en/latest/api/document.html).
- [pdfplumber text extraction](https://github.com/jsvine/pdfplumber#comparison-to-other-libraries).
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [generate API](https://docs.ollama.com/api/generate).
- [openpyxl string typing](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/cell/cell.html).
