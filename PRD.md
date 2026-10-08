# Simplicitor product requirements

Updated 2026-10-09 after Alex's 2.0.0 sectioned-source review decision. This file owns requirements and acceptance values. [Architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md) owns implementation detail; [UI design](docs/superpowers/specs/2026-10-08-document-workspace-ui-design.md), the [single implementation plan](docs/superpowers/plans/2026-10-08-first-release-extraction.md), and [project status](docs/PROJECT_STATUS.md) complete the review set.

## Purpose

Make local AI useful for confidential documents without scripts or agent configuration. General document creation and selective editing remain the longer-term identity. The first release adds structured extraction into Excel; contracts and invoices are examples, not a restriction to accounting.

## Workflow scope

This is the single workflow table. Other documents link here.

| Workflow | Release scope |
|---|---|
| Existing prompt-only Create | Preserve existing behavior. |
| Existing PowerPoint template creation | Preserve existing behavior. |
| Create new from DOCX and text-layer PDF sources into XLSX | The only new workflow in the first release; one record per file. |
| Invoice line items / one record per table row | Next extraction increment, with its own design. |
| Selective editing of DOCX, XLSX, PPTX | Post-first-release milestone; preservation contract below. |
| XLSX-to-DOCX reporting | Post-first-release; blocked on the closed operation set below. |
| Local OCR/vision for scanned PDFs | Separate post-first-release milestone. |

First-release prerequisites are Windows and local Ollama with a local model. A GPU with 8 GB VRAM is recommended only and is not checked. Microsoft Office is not required. No COM, pywin32, Office helper process, OCR engine, or OCR packaging work belongs in this release. Sources are DOCX and PDFs with a usable text layer only; the new output is XLSX only. Existing Create does not acquire a new approval pipeline.

English is the target language. Other languages may work but are not tested or claimed.

A separate v1.2.1 safety release must disable legacy Edit before extraction ships. The plan selects disabling its UI and worker entry points, preserving existing Create/templates. Prepare and qualify this patch independently, then obtain Alex's explicit go before publication. Its release does not wait for extraction evaluation or the new installer.

## First-release UI

Create new is the default mode. Edit document is not shown. The extraction route collects sources and a request, proposes columns, then lets the user edit, add, remove, and confirm them.

Read the selected model's parameter size from Ollama metadata (/api/show). Below 8B or unknown, show this non-blocking warning: **Simplicitor works best with models of 8B parameters or more.** This is the product's only model check. Do not infer size from a name, check hardware, or disable actions because of the warning. Thinking is off for all extraction calls, including column suggestions.

Review the saved XLSX candidate in a read-only Qt grid. Highlight flagged Data cells; selecting any cell shows its value/proposal, quote, source anchor, and issue. Show coverage issues separately. Re-running replaces the job candidate and resets review and acknowledgement. No PDF preview is needed.

## Source reading and records

Read structured units with stable source references, without truncation or source changes. Read DOCX body paragraphs and table cells in document order, plus Word headers and footers as separately anchored units. Read PDF page text; PDF table extraction is unnecessary for this release. Disclose supported scope and flag unsupported structures.

Every attachment defines exactly one output row, even when files share a name or identical contents. Send the whole file in one request whenever it fits the estimated num_ctx budget after accounting for prompt and output tokens. Use the approved conservative estimate described in architecture; it may section files that an exact tokenizer would fit. Only files exceeding this budget are sectioned, using that same context. Accumulate the file's fields across non-overlapping sections in code. Each section uses the whole-file request format with only its current source units; never send previous_fields or source_scope. Do not discover multiple narrative records or implement row-level continuation/header matching. Code owns the complete file/column roster; model omission cannot silently remove rows or fields.

Inspect every PDF page for zero/near-zero extracted text. List affected pages in review and Evidence; never presume they are empty. They block a claim of complete extraction. A fully unreadable source fails preflight; partially readable output requires explicit acknowledgement of incomplete coverage. This check cannot recognize image-borne text on otherwise text-bearing pages.

Track selected units as processed, structurally excluded, or failed, with reasons. An oversized unit or failed section is a visible coverage issue. Reading and sectioning details belong to [architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md#source-reading-and-sectioning).

## Columns and grounding

The model proposes column names, descriptions, and types from the request and first source. The user edits and confirms the proposal before extracting all files; manual add/remove/edit remains available after a failed proposal. Types are text, integer, decimal, and date, defaulting from the proposal and falling back to text.

Use English numeric defaults: comma thousands separator and full-stop decimal separator, changeable per column. Accept numeric dates and English month-name forms, including "15 March 2026", "March 15, 2026", and "15-Mar-2026". Ask for day/month order only when the source contains ambiguous numeric dates. Preserve text identifiers and distinguish missing values from zero.

For every field, require a nullable string value, a verbatim quote, and a stable anchor. Code checks that the anchor belongs to that file and the quote occurs in its unit after whitespace normalization. For every column type, the value must appear word for word inside the quote at token boundaries: adjacent characters cannot be letters/digits, or commas/periods continuing a number. Check those boundaries in both the quote and its matched source context, so a shortened quote cannot hide a partial token. Sentence-ending punctuation is allowed. Only then does code convert that literal value to the confirmed column type; the model never normalizes it. For example, quote "Total: USD 12,500.00" with value "12,500.00" passes, and code converts it to 12500.00. Values "12500.00", "2,500.00", and "500.00" do not pass that quote. English date conversion includes ordinal days and legal wording such as "the 15th day of March 2026".

Build JSON schema from confirmed columns and permitted file record IDs; use the existing Ollama format argument and validate responses in code. Missing fields, schema failures, bad evidence, unsupported conversions, and conflicts remain present and flagged. Source/model text cannot execute commands or formulas.

A verified value wins over an unverified grounding/conversion proposal regardless of section order; retain the unverified proposal and its evidence in alternatives. Multiple unverified proposals cannot prevent a later verified value from winning. Two verified values that disagree remain a flagged conflict. Request/schema failures, including actual context truncation, cannot be hidden by this merge rule.

Numeric conversion accepts a currency symbol (£, $, €, ¥) or three-letter uppercase code immediately before or after the number, with optional space. Strip that marker only after the complete proposed value passes verbatim grounding. Preserve it in Evidence. In integer/decimal columns, a leading zero followed by another digit is flagged as leading_zero and retained as literal text; 0.50 remains valid. Empty or whitespace-only model values and the trimmed, case-insensitive string "null" represent absent nulls, remain flagged for review, and project to blank Data cells.

Grounding checks evidence consistency, not semantic correctness. A correctly quoted invoice date placed in a due-date column can pass it. Review exposes every cell's quote, and the labelled gate limits these unflagged errors.

## Workbook and save

Write a dedicated Data/Evidence workbook. Data contains one row per file and all confirmed columns. Write grounded values under the confirmed types. Write validation-failed proposed values as literal text, highlighted, with their issues in Evidence. For 2.0.0, every extracted Data cell from a file requiring sectioning must be highlighted and flagged with sectioned_source, including otherwise verified values and blank fields. This review flag preserves verified values, Excel types, and number/date formats; existing validation failures retain their literal proposals and original issues. The whole-file path retains its existing validation behavior. Fields with no proposal remain blank and flagged. Exporting flagged or incomplete output requires acknowledgement.

Evidence contains record, field, verbatim model value, quote, source anchor, status, and issue; each Data cell resolves its entry. Include file labels and stable row references without absolute paths. Distinguish coverage issues from model fields.

Keep identifiers and formula-like text literal in both sheets. Never activate formulas/hyperlinks or silently clip, round, or coerce values to fit Excel. Numbers Excel cannot represent exactly are retained as highlighted literal proposals with issue excel_precision; save the remaining fields normally. Over-long text and invalid control characters in values/evidence cause a visible error before saving a candidate.

Keep one candidate per job in the application-data folder. Re-running replaces it and resets review. Build the grid from the saved candidate file. Save uses a standard Save As dialog with normal Windows overwrite confirmation, then copies that candidate. Require an .xlsx destination suffix (case-insensitive) and refuse a destination equal to any source path. Stage the copy in the destination folder and rename only after a successful write; failure cannot leave a partial output or show success.

Delete job folders on normal close after handles/workers finish. At startup, delete only Simplicitor's own job folders older than 24 hours. No crash-recovery UI is required.

## Limits and evaluation gates

| Measure | Requirement or retained proposal |
|---|---|
| Maximum source size per job | 300 pages total, approved. PDF uses actual pages; DOCX uses displayed page equivalents as defined in architecture, without Office pagination. |
| Labelled fixtures | At least 20 synthetic English DOCX/text-PDF contracts and invoices and 200 scored field slots. Include eight prose-based documents with parties in preambles, ordinal dates, sentence-contained amounts, and supplier/invoice identifiers in Word headers. One record per file, including table-contained fields, competing dates, missing fields, literal strings, and fields spread across pages. |
| Field accuracy | Whole-file path: at least 95% correct Data values against independent labels under confirmed column types. Missing records/fields count as incorrect except labelled absent values. Flagging alone does not make a wrong value correct. Sectioned accuracy is reported without gating it. |
| Unflagged wrong values | Whole-file path: at most 1% of its scored slots, including semantic errors that pass grounding. At 200 slots, at most two; fail at three. Sectioned path: zero unflagged values, whether correct or incorrect. Every sectioned Data cell requires review with sectioned_source. Flags come from extraction/validation, never labels. |
| Review burden | Report flag rates on correct values and expected missing values separately. Whole-file indiscriminate flagging is not a usability pass; sectioned sources intentionally require review of every value in 2.0.0. |
| Evaluation candidates | qwen3:8b and llama3.1:8b at Q4_K_M, with reported parameter size of 8B or more. Larger models are optional reference results and cannot be selected. |

Run evaluation on [B1](docs/PROJECT_STATUS.md#benchmark-environment) using the actual English fixture files, anchored readers, and shared grounding/scorer. The Task 1 fixtures fit one request; the full-pipeline corpus also includes larger sectioned files. Record the candidate, quantization, and fixed settings described in [architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md#model-requests).

Task 1 is the single early stop gate on actual fixture files, testing the common whole-file production path. Stop and report if neither candidate passes, including when only a reference model passes; Alex decides any scope change. Task 6 reruns the corpus through the full production pipeline as the release check, including the existing labelled files too large for a single request. For 2.0.0, the 40 sectioned slots are diagnostic and do not qualify autonomous extraction accuracy; no extra sectioned fixtures are required. The sectioned criterion checks mandatory review coverage, and its accuracy remains informational. Full-pipeline evaluation checks each path against its own criterion and exits non-zero if any evaluated non-reference candidate has a failing path. Saved-output and complete-coverage checks still apply. Aggregate counts are diagnostic and cannot hide a failing path. Timings may be recorded for information only; speed is not a release criterion and these measurements are not performance claims.

## Privacy and failure behavior

Processing stays local with a confirmed local model and local-only runtime configuration. No cloud fallback or remote OCR. Keep contents, prompts, responses, quotes, identifiers, and sensitive paths out of diagnostics and tracked evaluation reports. Use synthetic fixtures.

Retain instructions after failure, prevent duplicate jobs, and support cooperative cancellation. A blocking HTTP request can finish or time out before cancellation completes. Cancelled jobs cannot save results.

## Packaging

Use the existing Nuitka/PySide6 foundation, a standalone payload, NSIS installer, and portable ZIP. Distribute through GitHub Releases and simplicitor.com. No Microsoft Store or paid signing. Customers need no Python, Office, OCR runtime, or agent configuration for the new workflow.

Preserve settings, templates, and user documents during upgrades/uninstall. Investigate unsigned Windows blocks with default protection enabled. [Packaging procedures](docs/code-signing.md) may progress alongside extraction, subject to its model stop gate; the independent safety release follows its own checks.

## Post-first-release requirements

Invoice line-item/table-row extraction is the next extraction increment and needs its own design. Multiple narrative records, table continuation/repeated-header matching, and OCR/vision remain outside the first release.

Selective editing remains a later milestone. Confirm exact targets, patch a separate candidate, and review before publication. Apply edits directly to OOXML parts: w:t, a:t, cell values, and shared strings. Every unedited package part's bytes remain identical; edited parts differ only at approved target nodes. Define shared-string alias handling so a selected cell edit cannot affect other cells. Do not broadly reserialize unrelated content.

Office COM is reserved for later PDF preview export and Excel recalculation on disposable copies. COM-saved copies cannot replace preserved patched output. Feature support and allowed node changes need a later design.

XLSX-to-DOCX reporting is blocked on a closed operation set: sum, count, average, difference, and percent, filtered by period or group over a confirmed range. The model selects a structured query; code validates and executes it.

PDF write-back, general agents, RAG/indexing, model management, cloud services, and other platforms remain outside this release.

## License decision

PolyForm Noncommercial conflicts with the business audience. Alex owns this decision. Leave LICENSE and existing rights unchanged; free distribution does not imply business-use permission.
