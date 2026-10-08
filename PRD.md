# Simplicitor product requirements

Updated 2026-10-08. Alex's revised decisions supersede the earlier Office-backed proposal. This file owns requirements. [Project status](docs/PROJECT_STATUS.md) owns implementation state and open decisions; [architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md) and the [first-release plan](docs/superpowers/plans/2026-10-08-first-release-extraction.md) describe implementation.

## Purpose

Make local AI useful for confidential documents without scripts or agent configuration. General document creation and selective editing remain the longer-term identity. The first release adds structured extraction into Excel; contracts and invoices are examples, not a restriction to accounting.

## Workflow scope

This is the single workflow table. Other documents link here.

| Workflow | Release scope |
|---|---|
| Existing prompt-only Create | Preserve existing behavior. |
| Existing PowerPoint template creation | Preserve existing behavior. |
| Create new from DOCX and text-layer PDF sources into XLSX | The only new workflow in the first release. |
| Selective editing of DOCX, XLSX, PPTX | Next milestone after extraction; preservation contract below. |
| XLSX-to-DOCX reporting | Post-first-release; blocked on the closed operation set below. |
| Local OCR/vision for scanned PDFs | Separate post-first-release milestone. |

First-release prerequisites are Windows, local Ollama, and a usable local model. Microsoft Office is not required. No COM, pywin32, Office helper process, OCR engine, or OCR packaging work belongs in this release. Sources are DOCX and PDFs with a usable text layer only; the new output is XLSX only. Existing Create does not acquire a new approval pipeline.

A separate v1.2 safety patch must disable legacy Edit or prevent destructive failures. The plan selects disabling the UI and worker entry points until selective editing replaces them. Do not rewrite legacy manipulation while implementing source readers.

## First-release UI

Create new is the default mode. Edit document is not shown. Preserve existing prompt-only creation and PowerPoint templates. The extraction route collects sources, a request, confirmed columns, and a record mode.

Review the saved XLSX candidate in a read-only Qt grid. Highlight flagged Data cells; selecting a cell shows its proposed value, quote, source anchor, and issue. Show coverage issues separately. Changing sources, columns, mode, or request invalidates the candidate and approval. No PDF preview is needed.

## Source reading and anchors

Reuse python-docx and pdfplumber, and pypdf where suitable within its existing dependency. Start from the reading logic in simplicitor/app/services/file_manipulator.py, but put new readers in an independent small module. Return structured units, not a joined string. Source reading never calls _truncate and never changes supplied files.

Read DOCX body paragraphs and tables in document order, retaining stable indices including empty units. Anchor body paragraphs as source_id#p:index and table cells as source_id#t:table:r:row:c:cell, with zero-based indices. Read physical cells once where merged cells have aliases. Disclose body scope and flag ambiguous or unsupported structure instead of claiming whole-document coverage.

Anchor PDF page text as source_id#page:number, with one-based page numbers. Where tables are found, use source_id#page:number:t:table:r:row, with zero-based table/row indices. Retain table cells and header structure. Source IDs are unique within a job and bound to snapshot hashes, not just filenames.

Inspect every PDF page's extracted non-whitespace character count against the proposed threshold below. List zero/near-zero-text pages in review and Evidence; never presume they are empty. They block a claim of complete extraction. A fully unreadable source fails preflight; partially readable output needs explicit acknowledgement of incomplete coverage. This screen does not certify reading order or recognize image-borne text on otherwise text-bearing pages.

## Records and sectioning

Support two record modes:

- One record per file, the main case. Each attachment defines a row, even when files contain identical text. The known file record can accumulate fields across sections; discovering multiple implicit narrative records is deferred.
- One record per table row, including continued tables and repeated headers across pages. Use confirmed header/column mappings. Carry pending incomplete rows across section boundaries; flag ambiguous continuations rather than guessing a merge.

Split only at paragraph, table-row, or page boundaries, with no overlap. Carry open record state and anchors forward. Do not split a table row's cell units across sections. There is no record-deduplication requirement. Field conflicts still require review; repeated headers are structure, not records. Consume the mode's page or table view without submitting duplicate representations.

Track every selected unit as processed, structurally excluded, or failed, with a reason. An oversized unit or failed section produces a visible coverage issue, never truncation. Code enumerates record identities from files/table rows; model output cannot silently remove them.

## Columns and grounding

Confirm names, descriptions, and types before extraction. Proposed initial types are text, integer, decimal, and date. Numeric separators and ambiguous date order require explicit interpretation. Text identifiers remain text; missing values differ from zero.

For every field the model returns value, quote, and anchor. Its value is a nullable string so code owns type conversion. Code verifies that:

1. The anchor belongs to an allowed unit of the record's source snapshot.
2. The verbatim quote occurs in that unit after whitespace normalization only.
3. The value derives from the quote under the confirmed type: a literal text substring, a finite number under the confirmed numeric grammar, or a date under the confirmed date grammar. No inferred arithmetic, unrelated-unit joining, or invented normalization is allowed.

Build JSON schema from confirmed columns and permitted record IDs; pass it through OllamaClient.generate(output_format=...). Validate the response again in code. Do not bypass a schema failure with unconstrained prose. Model/source text cannot execute commands or formulas.

Missing fields, invalid schema, unknown anchors, unsupported conversions, conflicting values, and failed grounding remain present and flagged. Preserve the requested record/column roster. Grounding proves evidence consistency, not semantic correctness: an invoice date used as a due date can pass literal checks. The labelled evaluation gate must catch unflagged semantic errors.

## Workbook and publication

Use openpyxl for a new candidate, not ExcelGenerator._coerce_value. Type grounded values from the confirmed schema. Reject non-finite numbers and unapproved grammars. Do not coerce identifiers, NaN, inf, or 1_000 merely because Python accepts them.

Data has one row per known record and the confirmed columns. Flagged fields remain present as highlighted blank cells; Evidence retains their proposed values. Evidence columns are record, field, value, quote, source anchor, status, and issue. Record references identify the corresponding Data row and stable record ID; source references include a readable file label and anchor without absolute paths. Coverage issues are distinguished from model-derived fields. Every Data cell resolves its Evidence entry.

Force text cells to string type after assignment, including text/quotes beginning with =. Do not activate formulas or hyperlinks from source/model text. Reopen the saved workbook and verify types, records, evidence, and flags before review. Cell-length, unsafe numeric-precision, and control-character violations fail visibly; values and evidence are never silently clipped or rounded to fit Excel.

Keep immutable source units in memory and candidates in a private local application-data job directory with unique identity. Publish only the exact approved candidate after checking its hash and observed source changes. Destination collisions fail without replacement; write failures cannot publish partial outputs or emit success. Exporting flagged/incomplete output requires acknowledgement and retains its issues in Evidence.

Clean owned temporary files on normal save/discard/close after worker/reader handles close. After a crash, never automatically publish an orphan; offer removal of identified owned job directories. Never delete arbitrary directories or follow reparse points outside the workspace.

## Proposed limits and evaluation gates

All numbers and profile choices here are proposals for Alex's approval, not measured performance. After approval, runtime constants and the evaluation manifest trace to this section.

| Measure | Proposal and definition |
|---|---|
| Maximum source size per job | 300 pages total. PDF uses actual pages. DOCX uses max(1, ceil(extracted_characters / 3000)) page equivalents per file, including body paragraph/table text. Display estimates; do not trust stale DOCX page metadata or require Office pagination. |
| File/allocation protection | 50 MiB per input file, 100 MiB input bytes per job, 100 MiB declared uncompressed DOCX package content per file. Reject excess before expensive processing; never truncate. |
| PDF near-zero threshold | Fewer than 40 non-whitespace extracted characters per page. Retain counts/reasons for review. |
| Model request budget | Up to 8000 UTF-8 source bytes per structural section, plus a request/schema/carry-state budget check. Oversized units fail visibly. Initial profile: context 16384, output 4096 tokens, temperature 0, seed 0, HTTP timeout 180 seconds. Freeze a supported model-specific thinking setting before scoring. |
| Labelled fixtures | About 20 synthetic DOCX/text-PDF documents with at least 200 scored field slots across both record modes, contracts, and invoices. Include missing fields, competing dates, formula-like strings, and continued tables. |
| Field accuracy | At least 95% correct final Data values under confirmed types. Missing records/fields count as incorrect except labelled absent values. Flagging does not make a wrong value correct. |
| Wrong-value visibility | 100% of incorrect slots must be flagged or fail grounding: zero unflagged incorrect fields on the fixture set. Flags come from extraction/validation, never scoring labels. Report wrong-value counts even when zero. |
| Review burden | Report flag rates for correct values and expected missing values separately. Flagging everything is not a usability pass. |
| Time per page | Measure cold-start and warm p50/p95 seconds per PDF page or DOCX page equivalent on B1 for each named model/configuration. Fix and approve the selected configuration's numeric target after measurement; none is claimed yet. |

Locally discovered candidate models: qwen3.8:27b (Q4_K_M), qwen3.6:27b (Q4_K_M), and gemma4:12b-it-q8_0 (Q8_0). [Project status](docs/PROJECT_STATUS.md#benchmark-environment) defines B1. Record model digests, runtime versions, configuration, errors, and timings in the evaluation report.

Evaluate models before extraction UI. If none passes both quality gates, stop and report; do not lower thresholds or proceed to UI. Early model-only evaluation can use independently authored canonical fixture units before production readers exist. The selected configuration must pass again on actual fixture files and the production sectioner before writer/UI work.

## Privacy and failure behavior

Processing stays local with a confirmed local model and local-only runtime configuration. No cloud fallback or remote OCR. Keep contents, prompts, responses, quotes, identifiers, and sensitive paths out of diagnostics. Use synthetic fixtures, never client records.

Use existing QObject/QThread patterns. Retain requests after failure, prevent duplicate jobs, and check cancellation between units and model calls. Cancellation is cooperative while blocking HTTP completes or times out; do not claim immediate cancellation or kill QThreads. Cancelled jobs cannot publish.

## Packaging

Use the existing Nuitka/PySide6 foundation, a standalone payload, NSIS installer, and portable ZIP. Distribute through GitHub Releases and simplicitor.com. No Microsoft Store or paid signing. Customers need no Python, Office, OCR runtime, or agent configuration for the new workflow.

Preserve settings, templates, and user documents during upgrades/uninstall. Unsigned artifacts can still warn or be blocked; investigate the reported block and test default Windows protection without disabling it. [Packaging procedures](docs/code-signing.md) may progress alongside feature work, subject to the model stop gate.

## Post-first-release requirements

Selective editing is the next milestone after extraction. Confirm exact targets, patch a separate candidate, and review before publication. Apply edits directly to OOXML parts: w:t, a:t, cell values, and shared strings. Every unedited package part's bytes remain identical; edited parts differ only at approved target nodes. Define shared-string alias handling so a selected cell edit cannot affect other cells using that entry. Do not rebuild or broadly reserialize unrelated content.

Office COM is reserved for later PDF preview export and Excel recalculation on disposable copies. It is not the editing backend, and COM-saved copies cannot replace preserved patched output. Feature support and allowed node changes need a later design.

XLSX-to-DOCX reporting is blocked on a closed operation set: sum, count, average, difference, and percent, filtered by period or group over a confirmed range. The model selects a structured query; code validates and executes it. Do not build reporting before that contract exists.

OCR/vision, scanned/mixed-PDF recognition, and discovery of multiple narrative records across sections are later milestones. PDF write-back, general agents, RAG/indexing, model management, cloud services, and other platforms remain outside this release.

## License decision

PolyForm Noncommercial conflicts with the business audience. Alex owns this decision. Leave LICENSE and existing rights unchanged; free distribution does not imply business-use permission.
