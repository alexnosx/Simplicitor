# Simplicitor product requirements

Updated 2026-10-16 for 2.5.0 preparation: the Azure workspace and display-only Word review amendment. Extraction requirements and evaluation settings are unchanged from 2.0.0. This file owns requirements and acceptance values. [Architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md) owns implementation detail; [UI design](docs/superpowers/specs/2026-10-08-document-workspace-ui-design.md), the [2.0.0 extraction plan](docs/superpowers/plans/2026-10-08-first-release-extraction.md), the [2.5.0 plan](docs/superpowers/plans/2026-10-16-release-2.5.0.md), and [project status](docs/PROJECT_STATUS.md) complete the review set.

## Purpose

Make local AI useful for confidential documents without scripts or agent configuration. General document creation and selective editing remain the longer-term identity. The first release adds structured extraction into Excel; contracts and invoices are examples, not a restriction to accounting.

## Workflow scope

This is the single workflow table. Other documents link here.

| Workflow | Release scope |
|---|---|
| Prompt-only Create | Preserve Word, PDF, Excel and PowerPoint generation in 2.5.0. |
| PowerPoint creation from built-in templates | Built-in picker only; preserve the generation engine. |
| Create new from DOCX and text-layer PDF sources into XLSX | Introduced in 2.0.0; unchanged in 2.5.0, with one record per file. |
| Invoice line items / one record per table row | After Edit for Word in 2.3.0, with its own design. |
| Edit for Word (2.3.0) | Selected whole body paragraphs; tables, headers, footers, fields, links, pictures, comments and tracked changes read-only; Excel and PowerPoint later. Preservation contract below. |
| XLSX-to-DOCX reporting | Post-first-release; blocked on the closed operation set below. |
| Local OCR/vision for scanned PDFs | Separate post-first-release milestone. |

The 2.5.0 prerequisites are Windows and local Ollama with a local model. A GPU with 8 GB VRAM is recommended only and is not checked. Microsoft Office is not required by the application; the one-off Word compatibility check uses installed Word on Alex's PC. No COM, pywin32, Office helper process, OCR engine, or OCR packaging work is added to the application. Sources for extraction are DOCX and PDFs with a usable text layer only; source-based output remains XLSX only. Prompt-only Create retains PDF output and does not acquire a new approval pipeline. Source-based Word/PDF reports remain a later milestone.

English is the target language. Other languages may work but are not tested or claimed.

The published v1.2.1 safety release disabled legacy Edit at its UI and worker entry points, preserving Create/templates. The new Word editor uses an independent editing package; legacy editing remains disabled.

## 2.5.0 UI

Offer two modes: Create new (default) and Edit document. Edit document opens the selective Word editor described below. Show the shared product version in the window title, top bar and Settings.

Create new starts with two options, each with a one-line explanation: **Write a new document** and **Pull information into Excel**. The chosen option determines the request. Writing uses its description, file type and save folder, and never sends attached source files. PowerPoint offers the built-in templates business_pitch and technical_overview, with the chosen name and Clear. Pulling uses its request and DOCX/text-layer PDF attachments, always produces Excel, and advances through Choose columns, then Review and save. The user can edit, add, remove and confirm columns before extraction. Reports from source files remain unavailable.

The Azure presentation uses a blue brand row with the actual icon, name/version, **Powered by your local LLM** below the name and **Your documents. Your computer. Your control.** on the right. A second row holds modes, connection status and Settings. Write has four file-format choices. Keep save folders on one middle-elided line with the full path available in a tooltip. At 1280x800, Write and Pull Describe fit without scrolling and show three complete source rows; smaller windows may scroll while their actions remain reachable. Styling introduces no processing, cancellation, review or save rule.

Each option retains its own inputs during switching. Leaving Pull clears columns, review and acknowledgement through setup_changed and discards the owned job. Block switching while any work runs and ignore late results for the other option. Mode switching and Settings also remain disabled during work. Use body text of at least 11 pt, darker borders and numbered boxes, with blue hover, choice and focus states. Source names, paths and evidence are plain text.

File rows show Reading, Ready or Partly read; Partly read means the file has reading problems. Show progress on the file row and the main action. While extracting, retain at least four visible column rows and a light disabled selection. The UI spec owns the reading-problems heading and acknowledgement labels.

Show review acknowledgement whenever the candidate has issues, whether highlighted values, reading problems, or both. The UI spec owns the three acknowledgement labels. Successful generation or extraction export opens a Saved page; source extraction still uses the native XLSX Save As dialog.

Read the selected model's parameter size from Ollama metadata (/api/show). Below 8B or unknown, show this non-blocking warning: **Simplicitor works best with models of 8B parameters or more.** This is the product's only model check. Do not infer size from a name, check hardware, or disable actions because of the warning. Thinking is off for all extraction calls, including column suggestions.

Review the saved XLSX candidate in a read-only Qt grid. Highlight flagged Data cells; selecting any cell shows its value/proposal, quote, source anchor, and issue. Show coverage issues separately. Re-running replaces the job candidate and resets review and acknowledgement. No PDF preview is needed.

## 2.3.0 Edit for Word

The editor introduced in 2.3.0 keeps its engine and preservation contract in 2.5.0. The D2 red Before markers and removed/merged-paragraph notice are a display-only review amendment for 2.5.0.

Open one standard Word document (.docx), select a continuous range of whole body paragraphs, describe a change, review the selected part before and after, and save a new file. A selection cannot cross a table or a read-only paragraph. Tables, headers and footers are shown read-only. Paragraphs containing fields, links, pictures, form fields, tracked changes, comments, section breaks, unsupported constructs or non-collapsed inline bookmarks are read-only with a reason. The collapsed Word _GoBack bookmark is supported. The [technical design](docs/superpowers/specs/2026-10-13-edit-for-word-design.md) defines the exact editability and formatting rules.

Refuse password-protected, digitally signed and Word-protected documents. Refuse unreadable or malformed packages, macro-enabled files, templates, Strict OOXML, unsupported encodings and field/comment structures that cannot be mapped safely. Protection is refused when enforced; Track Changes being on is allowed. File refusals leave the original unchanged and show a plain message.

| Acceptance value | Requirement |
|---|---|
| Input size | At most 50 MiB for one .docx. |
| Document length | At most 300 page equivalents, computed by the existing reader using 3,000 extracted characters per equivalent, without Word pagination. |
| Selection | At most 6,000 characters in a continuous whole-body-paragraph range. |
| Description | At most 2,000 characters. |
| D1: saved changes | One change per saved file. After saving, show the path, "The original is unchanged." and Open another document. Further changes require opening the saved file. |
| D2: review | Show only the selected part before and after. Highlight changed or added words in light green in After. Show removed or replaced text in pale red with a strike-through in Before, and a clear notice when original paragraphs are removed or merged. These markers are display-only; the original stays unchanged. Warn that longer text can change page breaks. |
| D3: Track Changes | Allow editing and show: "Track Changes is on in this document. This change is saved without revision marks." Do not create revision marks. |
| D4: model gate | Each of qwen3:8b-q4_K_M and llama3.1:8b-instruct-q4_K_M must pass at least 11 of 12 fixed tasks with zero candidate verification failures. Confirm installed tag, digest and Q4_K_M identity. Run seed 0 with the approved prompts, tasks and mechanical checks; do not send checks to the model. |

Only selected paragraphs may be patched. Preserve every other package part's decompressed bytes and every byte outside the selected range of the main document part. All six candidate checks must pass before Review. Preserve unchanged formatting and supported bookmark boundaries according to the design; never silently substitute a broadly reserialized document. The preservation contract below is unchanged.

Save As defaults to `<name> (edited).docx` beside the original. Never overwrite the original, including equivalent paths. Require a .docx destination and normal overwrite confirmation for another existing file. The worker records the destination after dialog acceptance, stages and reads back the file, rechecks the original and destination at the commit point, then replaces the destination. An original that changed, disappeared or became unreadable requires reopening; a changed or unreadable destination requires choosing again. Write failures keep the proposal available without showing success.

Open and proposal work can be cancelled. An accepted save finishes before close; show the waiting message on the visible screen. If that save fails during closing, keep the window open with the failure on Save. Discarding a selection, description or unsaved proposal requires confirmation, with Keep editing as the default; pick a replacement file before asking so cancelling the picker retains the current work. Settings and mode switching are blocked during work, and cancelled or stale replies cannot reach Review.

English synthetic fixtures and the one-off read-only Word compatibility check are the acceptance evidence. No broader LibreOffice or Google Docs compatibility is claimed. Excel and PowerPoint editing, table editing, PDF preview and multiple unsaved changes remain later work.

## Source reading and records

Read structured units with stable source references, without truncation or source changes. Read DOCX body paragraphs and table cells in document order, plus Word headers and footers as separately anchored units. Read PDF page text; PDF table extraction is unnecessary for this release. Disclose supported scope and flag unsupported structures.

Name detected unread Word content in coverage: text boxes, tracked insertions/deletions/moves, form fields, fields, embedded documents, footnotes/endnotes and nested tables. Text in tracked moves uses the same not-read warning as other tracked text. Tracked formatting or row changes instead require review in Word while their text remains readable. Show reading problems before the table is used, under the UI spec's incomplete-reading heading.

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

Write a dedicated Data/Evidence workbook. Data contains one row per file and all confirmed columns. Write grounded values under the confirmed types. Write validation-failed proposed values as literal text, highlighted, with their issues in Evidence. From 2.0.0 onward, every extracted Data cell from a file requiring sectioning must be highlighted and flagged with sectioned_source, including otherwise verified values and blank fields. This review flag preserves verified values, Excel types, and number/date formats; existing validation failures retain their literal proposals and original issues. The whole-file path retains its existing validation behavior. Fields with no proposal remain blank and flagged. Exporting flagged or incomplete output requires acknowledgement.

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
| Review burden | Report flag rates on correct values and expected missing values separately. Whole-file indiscriminate flagging is not a usability pass; sectioned sources intentionally require review of every value, including in 2.2.0. |
| Evaluation candidates | qwen3:8b and llama3.1:8b at Q4_K_M, with reported parameter size of 8B or more. Larger models are optional reference results and cannot be selected. |

Run evaluation on [B1](docs/PROJECT_STATUS.md#benchmark-environment) using the actual English fixture files, anchored readers, and shared grounding/scorer. The Task 1 fixtures fit one request; the full-pipeline corpus also includes larger sectioned files. Record the candidate, quantization, and fixed settings described in [architecture](docs/superpowers/specs/2026-10-08-document-architecture-design.md#model-requests).

Task 1 is the single early stop gate on actual fixture files, testing the common whole-file production path. Stop and report if neither candidate passes, including when only a reference model passes; Alex decides any scope change. Task 6 reruns the corpus through the full production pipeline as the release check, including the existing labelled files too large for a single request. For 2.0.0, the 40 sectioned slots are diagnostic and do not qualify autonomous extraction accuracy; no extra sectioned fixtures are required. The sectioned criterion checks mandatory review coverage, and its accuracy remains informational. Full-pipeline evaluation checks each path against its own criterion and exits non-zero if any evaluated non-reference candidate has a failing path. Saved-output and complete-coverage checks still apply. Aggregate counts are diagnostic and cannot hide a failing path. Timings may be recorded for information only; speed is not a release criterion and these measurements are not performance claims.

## Privacy and failure behavior

Processing stays local with a confirmed local model and local-only runtime configuration. No cloud fallback or remote OCR. Keep contents, prompts, responses, quotes, identifiers, and sensitive paths out of diagnostics and tracked evaluation reports. Use synthetic fixtures.

Retain instructions after failure, prevent duplicate jobs, and support cooperative cancellation. A blocking HTTP request can finish or time out before cancellation completes. Cancelled jobs cannot save results.

## Packaging

Use the existing Nuitka/PySide6 foundation and one standalone payload. Retain the per-user MSI introduced in 2.1.0, with a portable ZIP of that same payload and SHA256SUMS.json. Install into the fixed per-user Programs/Simplicitor folder, with Desktop and Start Menu shortcuts and current-user registration. The MSI refuses an existing 2.0.0 NSIS installation; users uninstall it first, preserving settings and documents. Distribute through GitHub Releases and simplicitor.com. No Microsoft Store or paid signing. Customers need no Python, Office, OCR runtime, or agent configuration for the new workflow.

Preserve settings, templates, and user documents during repair, upgrades and uninstall. Investigate unsigned Windows blocks with default protection enabled; MSI packaging does not establish publisher trust. [Packaging procedures](docs/code-signing.md) retain historical release evidence; the [2.1.0 plan](docs/superpowers/plans/2026-10-09-release-2.1.0.md#testing-policy-alex-2026-10-09) owns the current testing policy.

Run the isolated full local source suite after each task; synthetic temporary-file creation/deletion and mocked build tests are allowed. Never run installers, uninstallers, msiexec, Windows Sandbox, WiX, build.py or qualification on Alex's PC, or install tools/dependencies locally. Pushes run hosted source tests only. The 2.5.0 Task 5 milestone builds and qualifies the exact source commit by manual dispatch on GitHub. A passing milestone prepares the release; Task 6 tagging/publication still require Alex's separate go. Earlier milestone checks remain historical evidence.

## Post-first-release requirements

Edit for Word in 2.3.0 was built from its approved mockup, technical design and implementation plan and comes before invoice line-item/table-row extraction. Table-row extraction needs its own design. Multiple narrative records, table continuation/repeated-header matching, and OCR/vision remain outside this release.

Selective editing remains outside 2.2.0, with Word first and Excel/PowerPoint later. Confirm exact targets, patch a separate candidate, and review before saving. Apply edits directly to OOXML parts: w:t, a:t, cell values, and shared strings. Every unedited package part's bytes remain identical; edited parts differ only at approved target nodes. Word editing must preserve every byte of document.xml outside the approved selection without whole-part reserialization. Define shared-string alias handling so a selected cell edit cannot affect other cells. Do not broadly reserialize unrelated content.

Office COM is reserved for later PDF preview export and Excel recalculation on disposable copies. COM-saved copies cannot replace preserved patched output. Feature support and allowed node changes need a later design.

XLSX-to-DOCX reporting is blocked on a closed operation set: sum, count, average, difference, and percent, filtered by period or group over a confirmed range. The model selects a structured query; code validates and executes it.

PDF write-back, general agents, RAG/indexing, model management, cloud services, and other platforms remain outside this release.

## License decision

Decision made: Simplicitor 2.0.0 onward uses the MIT License. Copyright (c) 2026 Alexandru Pop. Releases up to and including v1.2.1 remain under PolyForm Noncommercial 1.0.0; their release licenses are unchanged. Bundle the application LICENSE at the payload root beside third_party/. Third-party libraries retain their separate terms and notices. Publication still requires explicit authorization.
