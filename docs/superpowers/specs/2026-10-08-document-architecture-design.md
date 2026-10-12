# Simplicitor document architecture, 2.1.0

[PRD.md](../../../PRD.md) owns requirements and acceptance values. [Project status](../../PROJECT_STATUS.md) owns current state and B1. [UI design](2026-10-08-document-workspace-ui-design.md) owns presentation; the [2.0.0 extraction plan](../plans/2026-10-08-first-release-extraction.md) and [2.1.0 plan](../plans/2026-10-09-release-2.1.0.md) own signatures and checks. Updated 2026-10-12 to describe the implemented 2.1.0 release candidate.

## Structure

Keep Python/PySide6, existing generation/template workers, the plain-Python extraction package and its Qt worker adapter. MainWindow mounts one CreateScreen and an explanatory EditPlaceholder; TopBar selects the mode and Settings. CreateScreen emits requests with frozen setup, while MainWindow owns worker wiring, cancellation and teardown.

~~~mermaid
flowchart TD
    UI[CreateScreen] --> OLD[Existing Create and template workers]
    UI --> WORKER[Extraction QObject worker]
    WORKER --> READERS[Anchored DOCX and PDF readers]
    READERS --> COLUMNS[Suggest and confirm columns]
    COLUMNS --> PIPE[Whole-file or sectioned extraction and grounding]
    PIPE --> OLLAMA[Existing OllamaClient]
    PIPE --> XLSX[Data and Evidence workbook]
    XLSX --> GRID[Saved workbook grid]
    GRID --> SAVE[Native Save As and staged copy]
~~~

The core has no Qt dependency. Readers open sources read-only, close handles, and retain extracted units rather than uploaded file copies. Code owns one record per attachment, identified independently of filename.

## Module responsibilities

| Path | Responsibility |
|---|---|
| simplicitor/extraction/models.py | Small shared source, column, field, issue, result, and candidate contracts; response schema. |
| simplicitor/extraction/source_readers.py | DOCX/PDF reading adapted from legacy primitives, with stable anchors and coverage. |
| simplicitor/extraction/grounding.py | Source quote matching, literal value-in-quote check, then English type conversion. |
| simplicitor/extraction/request_format.py | Shared extraction system prompt and source/column serialization for the gate and production. |
| scripts/evaluate_extraction.py | Actual-file evaluation with direct Ollama HTTP calls, independent labels, and aggregate scoring. |
| simplicitor/extraction/sectioning.py | Non-overlapping structural sections for large production inputs. |
| simplicitor/extraction/pipeline.py | Column proposals, sectioned calls, field accumulation, issues, and cancellation. |
| simplicitor/extraction/xlsx_writer.py | Dedicated typed/literal workbook writing and saved-grid data reading. |
| simplicitor/extraction/jobs.py | Candidate folder, Save As copying, source-path refusal, and age-based cleanup. |
| simplicitor/app/workers/extraction_worker.py | QObject adapter for core actions. |
| simplicitor/app/widgets/create_screen.py | Describe, Choose columns, saved grid/evidence, native export request and Saved page; prompt/template route on the same screen. |
| simplicitor/app/widgets/step_indicator.py | Preserve the active step across prompt and source routes. |
| simplicitor/app/widgets/plain_labels.py | Present source anchors, issues and coverage in plain language without interpreting rich text. |
| simplicitor/app/widgets/edit_placeholder.py | Explain deferred selective editing and return to Create new. |
| simplicitor/app/generators/pdf_generator.py | Render the parsed Word structure to a validated, staged PDF. |

Reuse declared document libraries. Configuration stays in defaults.py. The legacy manipulator remains for its tests and template exception imports; new readers are independent.

## Source reading and sectioning

Adapt _extract_docx/_extract_pdf into structured readers without truncation. DOCX body paragraphs use source_id#p:index; cells use source_id#t:table:r:row:c:cell with zero-based indices including empty units. Traverse paragraphs/tables in document order and enumerate physical cells once. Report unsupported structures.

Read each explicit Word header/footer part once, including first/even-page definitions; inherited parts are not repeated for each section. Their paragraphs use source_id#header:index:p:index and source_id#footer:index:p:index; tables use the same t:table:r:row:c:cell suffix within that part. Body anchors remain unchanged. Header/footer text contributes to the DOCX page-equivalent count. Footnotes/endnotes and unsupported structures remain coverage issues. Header/footer containers use python-docx's [document-order API](https://python-docx.readthedocs.io/en/latest/api/section.html).

PDF page text uses source_id#page:number with one-based page numbers. Call each pdfplumber page's extract_text(); retain page counts and zero/near-zero-text issues. File mode needs no PDF table extraction.

record_id equals source_id. Same-named or identical-content attachments keep separate rows. Production sends the whole file when its conservative estimated request count fits num_ctx after reserved output. Otherwise split at paragraph, DOCX table-row, or PDF page boundaries without overlap, using the same budget. Plan each request using only its current source units, columns, and user request. Section requests have exactly the whole-file payload format, without previous_fields or source_scope; accumulation happens only in code. Retain additional proposals in FieldResult.alternatives. A verified value wins over unverified grounding/conversion proposals in either order; keep it unflagged and retain every failed alternative, including when several unverified proposals preceded it. Two verified values that disagree remain a flagged conflict. Schema/request failures still require flags and coverage issues. Oversized indivisible groups become coverage issues with every affected unit recorded.

## Implementation settings

Implementation values are approved. Store shared values once in defaults.py.

| Setting | Proposal |
|---|---|
| DOCX page equivalents | max(1, ceil(extracted_characters / 3000)) per file, including supported body, header/footer, and table text. Display estimates. |
| Input file limit | 50 MiB per file. The aggregate page limit belongs to PRD.md. |
| PDF near-zero text | Fewer than 40 non-whitespace extracted characters per page. |
| Production input budget | ceil((system prompt UTF-8 bytes + serialized request UTF-8 bytes) / 2.5), plus 256 template tokens and num_predict reserved output tokens. Compare against num_ctx. Do not include accumulated fields in the serialized request or its budget. Exclude JSON schema: Ollama applies it as an output constraint. No tokenizer dependency or fixed source-byte limit is added. |
| Request settings | num_ctx=16384, num_predict=4096, temperature=0, seed=0, think=False, HTTP timeout=180 seconds. |

The early fixtures fit whole in one request and do not use sectioning. Production column suggestions use the first source's leading complete units within the request budget, labelled a sample; extraction still covers all supported units.

## Model requests

[PRD.md](../../../PRD.md#limits-and-evaluation-gates) names the evaluation candidates and reference-only policy. The selected-model parameter-size lookup uses existing /api/show metadata parsing. It drives the product warning and the evaluation candidate-size rule; no other hardware/model validation is added.

Task 1's CLI calls /api/generate directly through requests.Session with trust_env=False and a loopback URL check. It submits all anchored units of each fixture in one request, with confirmed fixture columns and a JSON response schema. Thinking is always off.

Task 2 adds optional options, think, and local_only arguments to OllamaClient.generate while preserving existing callers. Extraction calls use output_format for schema, think=False, and local_only for the same loopback/trust_env=False transport. Column suggestions use these same settings. Diagnostics contain aggregate metadata and short errors, not document content or raw response bodies.

The shared client retains its string return. For local-only output exhaustion, OllamaOutputLimitError carries partial response_text separately from its safe message; the pipeline retains recognizable proposals but marks the request coverage failed. The [generate API](https://docs.ollama.com/api/generate) supplies done_reason. Cancellation is checked before and after blocking requests and between sections; a late reply cannot produce a result.

After every local extraction or column-suggestion response, the shared client checks prompt_eval_count against num_ctx minus num_predict. At or above that boundary, OllamaContextLimitError retains response_text with a safe error message. Extraction flags the reply's fields and records context_truncated coverage issues; a prior verified value cannot hide this request failure. Column suggestions return no usable columns and raise ExtractionError with issues for the sampled units. Missing or invalid token-usage metadata fails the request rather than assuming zero usage.

## Grounding and conversion

Check the anchor against the file's extracted units and match the quote after whitespace normalization. Then require the model value to be a literal, case-sensitive token-bounded span of its quote under the PRD grounding rule. Do not normalize the model value before this check. Code converts the verified span using confirmed English numeric/date settings, including ordinal/legal dates; conversion failure retains the proposal as flagged text.

FieldProposal normalizes blank strings and trimmed case-insensitive "null" to None once, so parsing and Data projection agree about absence. Numeric conversion strips an allowed currency marker after grounding. Shared response parsing lives alongside grounding and retains identifiable requested proposals when extra records/properties invalidate the response schema.

Test quotes with currency symbols, codes, and labels around the value, including the PRD amount example. A correctly quoted value assigned to the wrong column still counts as a semantic error in scoring.

Column suggestions consume the request and first-source sample. Users edit/confirm names and types; missing/unrecognized types fall back to text. Malformed suggestions retain editable setup. English date/number settings follow PRD.md.

## Workbook and Save As

Use a dedicated openpyxl writer. Valid fields use confirmed types; flagged proposals use highlighted literal strings, and absent proposals are highlighted blanks. Evidence maps every Data cell to its quote, anchor, and issue. Force text to data_type s, including formula-like strings.

Data starts with Record and File, followed by confirmed columns. Evidence stores the Data cell address, record, file basename, field, verbatim value, quote, anchor, status, and issue. Alternatives have their own rows; file coverage rows apply to every field of that record. ReviewCell uses saved worksheet coordinates, number_format, and evidence rows. The review grid hides the Record column while preserving worksheet coordinates and all saved Evidence. Candidate retains source paths only for Save As refusal; absolute paths are not written into the workbook. Validate Excel text limits/characters and numeric precision before serialization. Numeric representation failure creates a local flagged FieldResult with issue excel_precision, so FieldResult.data_value preserves the original proposal in Data and Evidence without changing the extraction result. Then reopen the staged workbook to check values, types, formats, flags, and Evidence before accepting it.

Each app-data job has one candidate.xlsx. Rerunning clears review and replaces that candidate; a failed run cannot revive the old review. Read grid values/Evidence from the saved workbook.

Jobs live under app-data/extraction-jobs/job-<UUID>, with an ownership marker containing the job ID and UTC creation time. Clear review and discard the previous job before starting a new run, including reruns that fail or are cancelled before writing. The writer also invalidates an existing candidate before attempting replacement. Cleanup checks the directory name and ownership marker; the age boundary is strictly older than retention. Its caller waits for workers and file handles before normal-close deletion.

Native Save As handles overwrite confirmation. Refuse a normalized source path, copy through a destination-folder temporary file, close it, then rename/replace. Write failure retains the previous destination and review, without saved success. Normal close removes the job after workers/handles finish; startup removes only owned jobs older than the PRD retention period.

Use existing QObject/QThread patterns and cooperative cancellation. The source readers never write back to supplied files.

The Qt adapter freezes source paths, request, columns, and model profile for each operation. GUI receivers use Qt slots, and thread-finished handlers poll non-blocking wait(0), retaining ownership until native completion before close can stop the GUI event loop. Template import retains its result and disables dismissal until its thread has exited. Cancellation invalidates review immediately, including a candidate emitted just before cancellation. An accepted Save As copy finishes without a Cancel action; close waits for it. See Qt's [signal/slot thread guidance](https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html) and [QThread completion semantics](https://doc.qt.io/qt-6/qthread.html#isFinished).


From 2.0.0 onward, extraction records one source-level Issue(sectioned_source, source_id, "", safe_message) when context planning requires sectioning. The writer applies it to every extracted Data cell for that source: highlight and flagged Evidence status with sectioned_source, retaining prior issues. This is a review policy, not a coverage failure or failed conversion. Verified values keep their saved types and numeric/date formats; invalid proposals remain literal. The saved grid and Save As acknowledgement consume these saved flags as before. Multiple whole files do not trigger the policy merely because the job has several requests.

## Evaluation and release order

The sequence below records the completed 2.0.0 extraction plan; its criteria remain unchanged in 2.1.0. D1 qualifies the final 2.1.0 documentation commit with the hosted build, without a new model run.

Task 1 reads actual English DOCX/PDF fixtures and runs the single early stop gate. Labels are independently authored field expectations, not alternate source units. Score accuracy, unflagged errors, and review burden using shared grounding and Data-value projection.

After it passes, implement the production pipeline and UI. Task 2 has unit checks only. Task 6 adds the CLI's --full-pipeline option and labelled files exceeding one request context to score both whole-file and sectioned production paths as the final release check. Both paths use the same saved-cell scorer and their PRD criteria separately. The sectioned path requires zero unflagged values and reports accuracy without gating it; whole-file criteria are unchanged. Failed saving or incomplete coverage still fails the path. Full-pipeline exit status requires every evaluated non-reference candidate path to pass, regardless of aggregate fractions. Optional timings decide nothing.

The published v1.2.1 safety release used its independent historical build/check route. The 2.0.0 installer preparation ran alongside extraction subject to the early stop gate. The 2.1.0 MSI route is described below; tagging and publication still require Alex's explicit go.

## Prompt generation and PDF output

CreateScreen routes prompt-only Word, Excel and PowerPoint generation through the existing FileGenerator and workers; PowerPoint template generation retains its separate pipeline. PDF uses the Word system prompt and the same parsed title/section structure. PdfGenerator escapes text into QTextDocument HTML, renders with Qt's bundled QPdfWriter on A4 pages with 20 mm margins, then validates the staged file with pypdf before replacing the destination. Failed writes leave the prior destination intact and remove their own temporary file. No Office or external PDF converter is required.

Generation diagnostics retain file type, response length where applicable and exception class, never output paths, prompt-derived names, slide content or exception text. This describes the updated generation route; legacy manipulation remains disabled.

## MSI packaging and hosted CI

Nuitka 4.2.2 compiles the standalone Python/PySide6 payload with product version 2.1.0.0. build.py generates a WiX fragment from the actual payload: one component per folder, stable path-derived IDs and UUID5 component GUIDs, HKCU registry key paths, all packaged files, and uninstall RemoveFolder entries. The authored packaging/simplicitor.wxs fixes the per-user Programs/Simplicitor directory and shortcuts, refuses the old NSIS registration, and schedules major-upgrade removal afterInstallInitialize for rollback. WiX 5.0.2 is pinned as a repo-local .NET tool on the hosted runner only. MSI validation suppresses only ICE91 for intentional per-user paths.

LICENSE and validated third_party notices are in the payload; the MSI and portable ZIP use that same payload. SHA256SUMS.json records payload and artifact hashes. The runner-only qualification checks NSIS refusal, install/registration/shortcuts, 20-second offscreen startup without Ollama, same-version repair, a synthetic major upgrade and settings-preserving uninstall. It does not establish native UI acceptance, SmartScreen reputation or a clean machine without developer runtimes.

The workflow runs source tests on pushes and pull requests. Only manual milestone dispatches and authorized version tags run the full build and qualification. Tests have a 15-minute job limit, verbose node logging and a 60-second stack dump. Artifact upload follows successful qualification. Publication is restricted to version tags and uses the versioned release-notes file as its body; a missing file fails that route. Local tests mock external build tools. See the [testing policy](../plans/2026-10-09-release-2.1.0.md#testing-policy-alex-2026-10-09) and [packaging procedures](../../code-signing.md) for scope and historical checks.

## Later architecture and references

[Post-first-release requirements](../../../PRD.md#post-first-release-requirements) retain editing, reporting, and recognition contracts. Later editing patches bounded OOXML nodes; Office supports disposable preview/recalculation copies only.

- [python-docx document order and tables](https://python-docx.readthedocs.io/en/latest/api/document.html).
- [pdfplumber text extraction](https://github.com/jsvine/pdfplumber#comparison-to-other-libraries).
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs) and [generate API](https://docs.ollama.com/api/generate).
- [openpyxl string typing](https://openpyxl.readthedocs.io/en/stable/_modules/openpyxl/cell/cell.html).
