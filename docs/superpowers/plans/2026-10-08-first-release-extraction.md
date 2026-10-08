# First-release extraction implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution or superpowers:subagent-driven-development if Alex selects delegation. Track steps with checkboxes. Tasks 0 and 1 are approved and complete. Current authorization covers the currency/null fixes, selected-Qwen rerun, and Task 2. Stop before Task 3.

**Goal:** Deliver the [PRD extraction workflow](../../../PRD.md#workflow-scope), preserve existing Create/templates, and release the independent safety patch.

**Architecture:** Task 1 proves the model/grounding result on actual files using direct HTTP. After that gate, build production sectioning, the saved XLSX, and Qt review using the [extraction components](../specs/2026-10-08-document-architecture-design.md#module-responsibilities).

**Tech stack:** Existing Python, PySide6, python-docx, pdfplumber, pypdf, openpyxl, requests, pydantic, and Nuitka/NSIS. No new runtime dependency.

**Spec:** [PRD.md](../../../PRD.md) owns requirements/gates; [architecture](../specs/2026-10-08-document-architecture-design.md) owns anchors and settings; [UI design](../specs/2026-10-08-document-workspace-ui-design.md) owns presentation; [status](../../PROJECT_STATUS.md) owns B1 and open decisions.

## Global constraints

- Task 2 is authorized after the selected-Qwen rerun. Commit/push to main are authorized for this scope. New dependencies and release publication require separate explicit authorization. Stop before Task 3.
- File records and English fixtures only. Keep labels out of prompts and flags, and preserve all requested files/columns.
- Use the PRD page limit and architecture per-file size limit/settings. Thinking is off for every extraction/column-suggestion call.
- The only model check is reported parameter size: product warning stays non-blocking; evaluation candidates follow PRD.md. Hardware recommendations are not checked.
- HTTP transport uses a loopback URL check and requests.Session with trust_env=False. Logs/reports contain aggregate metadata, not document content or raw response bodies. Timings are optional information.
- Use .venv/Scripts/python.exe for checks, with a fresh --basetemp under .venv. Redirect USERPROFILE/APPDATA/LOCALAPPDATA into an isolated home for widget/full-suite runs.

Start each task with focused failing tests, implement its contract, then rerun those tests. Keep tests tied to output accuracy, normal user actions, and real failure cases.

## Review focus

- A real quote in the wrong column still counts as an unflagged error; Task 1 pins the PRD fraction boundaries.
- A normalized amount can look correct while lacking literal evidence; Task 1 tests currency symbols, codes, labels, and exact value spans.
- Same-named attachments and table/page fields must retain one row per file; Tasks 1 and 2 test reading and accumulation.
- Flagged values, leading-zero IDs, and formula-like text must survive Excel; Task 3 tests actual saved cells.
- Cancelled/rerun work and failed Save As must not export stale or partial results; Tasks 2 through 4 test these ordinary workflow failures.

## Work order

Task 0 released v1.2.1 independently. Task 1 contains readers and the actual-file gate; its selected-Qwen currency/null rerun is recorded below. Task 2 builds production requests, column proposals, and conditional sectioning. Tasks 3 and 4 build writer and UI. Task 5 prepares packaging; Task 6 checks release quality. Current execution stops after Task 2.

### Task 0: Disable legacy Edit and release v1.2.1 independently

**Modify:** simplicitor/app/main_window.py, simplicitor/app/workers/manipulate_worker.py, simplicitor/app/config/defaults.py, build.py for patch version, CHANGELOG.md, and docs/PROJECT_STATUS.md. Inspect .github/workflows/build.yml's tag-triggered publication before any release action.
**Tests:** tests/test_manipulate_worker.py, tests/test_widgets.py, tests/test_build_script.py, and affected MainWindow/generation/template tests.

**Interfaces:** Keep constructors, signals, creation routes, and ManipulationError imports. MainWindow._on_save_requested and ManipulateWorker.run must return disabled/failed before extraction, backup, inference, or writes. Disable visible Edit in this patch; Task 4 removes it from the extraction shell. Build product version is 1.2.1.0.

- [x] Add test_legacy_edit_disabled_before_io for both entry points: assert zero extractor/model/backup/writer calls, no completed signal, and unchanged source bytes. Confirm the current source fails.
- [x] Add unconditional guards and one shared message; preserve the legacy module needed by template exception imports. Update version expectations and release notes.
- [x] Run focused safety/build/generation/template/teardown regressions in an isolated home.
- [x] Build the patch using the existing release route; no new installer is required. Verify source safety, Create/template regressions, local startup, and patch version. Alex waived the clean-machine walkthrough for v1.2.1 under the [packaging exception](../../code-signing.md).
- [x] After Alex's explicit go, publish v1.2.1 through the existing tag route. Verify Latest, the public executable version, and its SHA-256; record the [release evidence](../../releases/v1.2.1.json).

Complete: [local build/startup evidence](../../releases/v1.2.1-local.json) and [verified public release](../../releases/v1.2.1.json). The clean-machine exception applies only to this patch; it does not qualify later extraction packages.

**Verify:** python -m pytest tests/test_manipulate_worker.py tests/test_widgets.py tests/test_build_script.py tests/test_generate_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_main_window_teardown.py -q with isolated home/base directory, then python build.py and the patch walkthrough. Required: safety/regressions/build pass. Task 0's final release outcome is the verified v1.2.1 asset after publication go; before go, report prepared and awaiting publication, not released.

### Task 1: Read actual fixtures and run the stop gate

**Create:** simplicitor/extraction/__init__.py, simplicitor/extraction/models.py, simplicitor/extraction/source_readers.py, simplicitor/extraction/grounding.py; scripts/evaluate_extraction.py; tests/extraction/test_source_readers.py, tests/extraction/test_grounding.py, tests/extraction/test_evaluation.py; tests/extraction/fixtures/manifest.json, profiles.json, English DOCX/PDF documents, and independently checked field labels.
**Modify:** simplicitor/app/config/defaults.py for accepted reader/request settings. Do not modify OllamaClient or build sectioning/UI in this task.

**Interfaces:**
- SourceUnit(anchor, text, kind, order, structural_group); SourceDocument(source_id, original_path, label, units, page_cost, issues); ColumnSpec(id, label, description, kind, thousands_separator, decimal_separator, date_order).
- FieldProposal(value: str | None, quote: str, anchor: str); FieldResult(proposal, typed_value, flagged, issues), with data_value returning the converted value when valid or literal proposal/None when flagged. Issue contains code, source_id, anchor, and safe message.
- read_source(path: Path, source_id: str) -> SourceDocument; build_response_schema(columns: tuple[ColumnSpec, ...], record_ids: tuple[str, ...]) -> dict; validate_field(proposal: FieldProposal, column: ColumnSpec, units: Mapping[str, SourceUnit]) -> FieldResult.
- In the CLI, ScoredField(value, flagged) and ExpectedField(expected_value, expected_type) feed score_results(actual: Mapping[tuple[str, str], ScoredField], labels: Mapping[tuple[str, str], ExpectedField]) -> EvaluationReport. Keys are (source_id, column_id). Report counts correct/wrong/unflagged slots, flags on correct/missing values, failures, and optional timings.
- passes_quality_gate(correct: int, unflagged_wrong: int, total: int) -> bool compares the PRD fractions without percentage rounding. call_ollama(url: str, model: str, source: SourceDocument, columns: tuple[ColumnSpec, ...], settings: dict) -> str sends one whole fixture's anchored text directly to /api/generate.

- [x] Add reader tests for complete DOCX paragraphs/tables beyond legacy truncation, stable anchors, physical-cell aliases, same-named files, PDF page text, and zero/near-zero pages. Add per-file size and aggregate page-boundary checks; assert sources stay unchanged.
- [x] Implement the small readers from existing _extract_docx/_extract_pdf logic, without modifying legacy Edit. Close source handles and keep structured units.
- [x] Add grounding tests: source/anchor mismatch, missing quote/value, literal value present/absent, English date/number conversion, text IDs, and missing proposals. For "Total: USD 12,500.00", assert "12,500.00" passes and becomes 12500.00, while "12500.00" fails. Also cover "$12,500.00 (tax included)", "Balance due: £12,500.00", and "Total: EUR 12,500.00", with the value taken verbatim from the quote.
- [x] Implement one literal value-in-quote check for every type, followed by code conversion. Conversion failures retain the proposal, flagged. Build schema from fixture columns.
- [x] Add test_wrong_column_counts_unflagged: validate a real invoice-date span proposed for due_date, then score it against the different labelled due date. Assert not field.flagged, report.correct == 0, and report.unflagged_wrong == 1. Keep review burden separate. Pin these boundaries:

~~~python
def test_quality_boundaries():
    assert passes_quality_gate(correct=199, unflagged_wrong=1, total=200)
    assert passes_quality_gate(correct=198, unflagged_wrong=2, total=200)
    assert not passes_quality_gate(correct=197, unflagged_wrong=3, total=200)
    assert passes_quality_gate(correct=190, unflagged_wrong=2, total=200)
    assert not passes_quality_gate(correct=189, unflagged_wrong=0, total=200)
~~~

- [x] Create the PRD-sized English contract/invoice corpus using python-docx and existing pypdf. Include table-contained fields, fields across pages, competing dates, missing values, currency context, and literal strings. Every whole fixture fits the request context; independently check field labels against the actual files.
- [x] Implement CLI --manifest, --profiles, --report. Read actual fixtures, query candidate parameter size through /api/show, then call Ollama directly with all units of each file, schema, and think=False. Test one inference call per fixture, whole-file coverage, loopback URL validation, and trust_env=False. No source sectioning is needed here.
- [x] Score FieldResult.data_value and independently generated flags. Count malformed/missing responses as failures rather than skipped fixtures. Labels are scorer-only. Report candidate/settings and optional timings.
- [x] Run both PRD candidates on B1 and optional separately marked larger references. **Stop gate:** if neither candidate passes, stop extraction/installer work and report, even if a reference passes. Otherwise select by accuracy and review burden. The safety release remains independent.

Revision complete: token boundaries are checked in both quote and source context; DOCX headers/footers and ordinal dates are supported. Generic prompt/column definitions and eight narrative documents expand the corpus to 28 files/280 fields. The [rerun report](../../evaluation/2026-10-08-task1-rerun.md) records Qwen passing and Llama failing accuracy, with subgroup limits disclosed. The earlier scores have been reported; this is a historical gate result.

Latest Task 1 result: after the two approved currency/null fixes, the [selected-Qwen rerun](../../evaluation/2026-10-08-task1-qwen-currency-null.md) passed with unchanged prompt, corpus, labels, settings, and thresholds. This is the prerequisite result for Task 2; the earlier reports remain historical.

**Verify:** python -m pytest tests/extraction/test_source_readers.py tests/extraction/test_grounding.py tests/extraction/test_evaluation.py -q, then python scripts/evaluate_extraction.py --manifest tests/extraction/fixtures/manifest.json --profiles tests/extraction/fixtures/profiles.json --report .venv/evaluation/actual-files.json. Required: focused tests pass and at least one candidate passes the PRD gate on actual fixture files.

### Task 2: Add production requests, column proposals, and sectioning

**Create:** simplicitor/extraction/sectioning.py, simplicitor/extraction/pipeline.py; tests/extraction/test_sectioning.py, tests/extraction/test_pipeline.py.
**Modify:** simplicitor/extraction/models.py, simplicitor/app/services/ollama_client.py, tests/test_ollama_client.py.

**Interfaces:** ExtractionProfile(model, options, timeout) merges shared defaults with explicit options; Section(section_id, source_id, unit_ids, excluded=False); ExtractionResult(ordered_source_ids, fields, source_paths, issues, coverage), where coverage maps each anchor to processed, excluded, or failed. FieldResult.alternatives retains additional proposals with their quotes/anchors. make_sections(documents, profile, *, columns=(), request="", carried_fields=None) returns sections; production callers supply the confirmed request context so instructions/carry count against the input budget. propose_columns(request, first_source, profile, client, cancel) returns ColumnSpecs. extract(documents, columns, request, profile, client, cancel, progress=None) returns ExtractionResult; progress receives source_id, section_id, completed units, total units. ExtractionCancelled discards cancelled/late results. OllamaClient.generate adds keyword-only options, think, and local_only, preserving old defaults and string return; OllamaOutputLimitError retains response_text separately from its safe message.

OllamaContextLimitError retains response_text for truncated local requests. Extraction flags their fields and records failed coverage. Column-suggestion failures expose sampled-unit coverage through ExtractionError.issues.

**Shared helpers:** request_format.py owns the unchanged extraction SYSTEM_PROMPT and serialized request, used by both the direct gate and production. Grounding owns parse_fields and failed_fields. The conservative context estimate is defined in architecture; no tokenizer dependency is added.

- [x] Test the added client arguments, JSON schema in format, loopback check, trust_env=False, and unchanged old caller payloads. Every new extraction and column-proposal call sends think=False.
- [x] Test first-source column suggestions, text fallback, English defaults/overrides, invalid output/manual recovery, and conditional ambiguous-date order. Implement the proposal call using the shared client.
- [x] Test a whole-file request when it fits, boundary cases after prompt/output accounting (schema excluded), and context-derived non-overlapping sections only when necessary. Test oversized units and file-field accumulation. Implement conditional sections and calls without a fixed byte budget, truncation, or silently excluded units.
- [x] Test missing/unknown IDs, missing fields, invalid JSON, wrong evidence, conflicts, and output exhaustion. Keep the complete file/column roster, literal proposals, and issues.
- [x] Test timeout and cooperative cancellation, including a late response. Implement actionable errors, retained setup, and coverage accounting.

Result: the final isolated source suite passed 805 tests. Fake HTTP responses cover actual prompt-usage truncation for extraction and column suggestions, including the exact reserved-output boundary. Failed grounding alternatives preserve verified values; verified conflicts and schema/request failures remain flagged. All original gate fixtures still plan as whole-file requests under the production budget. No new live-model Task 2 gate was run; full saved-output evaluation remains Task 6. Task 3 has not started.

**Verify:** python -m pytest tests/test_ollama_client.py tests/extraction/test_sectioning.py tests/extraction/test_pipeline.py -q. Required: unit checks pass. No additional model gate runs here; the full-pipeline evaluation belongs to Task 6.

### Task 3: Write the saved candidate and implement standard Save As copying

**Create:** simplicitor/extraction/xlsx_writer.py, simplicitor/extraction/jobs.py; tests/extraction/test_xlsx_writer.py, tests/extraction/test_jobs.py.
**Modify:** simplicitor/extraction/models.py for Candidate(job_id, path, source_paths, issues) and ReviewCell(row, column, value, data_type, evidence).

**Interfaces:** write_candidate(result: ExtractionResult, columns: tuple[ColumnSpec, ...], path: Path) -> Candidate; read_candidate(candidate: Candidate) -> tuple[ReviewCell, ...]. create_job(app_data: Path) -> Path; save_candidate(candidate: Candidate, destination: Path, acknowledge_issues: bool) -> Path; discard_job(job_dir: Path) -> None; cleanup_old_jobs(app_data: Path, now: datetime) -> int. Call save_candidate only after the native Save As dialog accepts the destination with normal overwrite confirmation enabled; dialog cancellation makes no core call.

- [ ] Add saved-file tests for typed valid values with verbatim spans retained in Evidence, highlighted literal flagged proposals, highlighted missing proposals, leading-zero IDs, NaN/inf/1_000 text, =1+1 and =HYPERLINK(...) strings in both sheets, English dates, issues, and cell selection mapping. Assert flagged text is retained rather than blanked or coerced.
- [ ] Test invalid controls, excessive cell text, and unsafe numeric precision. Unrepresentable workbook content fails visibly; values/evidence are never silently clipped or rounded.
- [ ] Implement the dedicated writer using FieldResult.data_value, literal string typing, confirmed date/number formats, and shared styling. Reopen the candidate to verify its saved values/types, records, Evidence, and flags; build review from that file.
- [ ] Keep one candidate.xlsx in each owned app-data job. Rerunning replaces it and clears old review; failed/cancelled runs cannot offer the previous file as their new result.
- [ ] Add test_save_as_refuses_source_path for each source and normalized path variants. Test new destinations, replacing the destination chosen through Save As, and temporary write/rename failure. Assert sources and previous destination remain intact on failure and no success is emitted. Task 4 tests native confirmation/cancellation before the core call.
- [ ] Implement destination-folder temporary copying followed by rename/replace only after the copy closes successfully. Keep review available after failure; normal Windows overwrite confirmation remains the user's choice.
- [ ] Test normal-close cleanup after handles finish and startup age boundaries from PRD retention. Remove only owned app-data job folders; leave newer jobs and unrelated files.

**Verify:** python -m pytest tests/extraction/test_xlsx_writer.py tests/extraction/test_jobs.py -q. Required: saved-grid values/Evidence agree, flagged proposals remain literal, confirmed overwrite succeeds, source refusal/failed writes preserve existing bytes, and cleanup respects ownership/age.

### Task 4: Build the Create workspace, column editor, and grid review

**Create:** simplicitor/app/widgets/create_workspace.py, simplicitor/app/widgets/extraction_panel.py; simplicitor/app/workers/extraction_worker.py; tests/test_extraction_panel.py, tests/test_extraction_worker.py.
**Modify:** simplicitor/app/main_window.py, simplicitor/app/widgets/capability_banner.py, simplicitor/app/workers/ollama_worker.py for selected-model metadata lookup, simplicitor/app/config/defaults.py for warning copy/threshold, and affected tests/test_widgets.py, tests/test_ollama_worker.py, teardown tests.

**Interfaces:** CreateWorkspace hosts existing CreatePanel and ExtractionPanel. ExtractionPanel emits inspect_requested, propose_requested, extract_requested, cancel_requested, and save_requested with frozen settings. ExtractionWorker emits progress, inspection_ready, columns_ready, candidate_ready, failed, and cancelled; no widget access. Add OllamaWorker.request_model_params(model_name: str) -> None as a queued Qt slot, reusing metadata parsing and model_params_ready. MainWindow._on_model_changed queues the selected-model lookup; _on_model_params_ready ignores stale names. Loaded-model polling must not replace an explicit selection or its warning state.

- [ ] Add Qt tests for the default shell, hidden Edit, no record-mode/header-mapping controls, and retained prompt/template routing.
- [ ] Add test_selected_model_warning for below-threshold, exact-threshold, above-threshold, and unknown sizes. Assert PRD copy, no blocked action, updates when the selected model differs from the loaded model, and stale metadata cannot change the selection/banner. Keep dismiss behavior per selection.
- [ ] Add proposal/editor tests for first-source suggestions, edit/add/remove, proposed/fallback types, English defaults/overrides, conditional numeric-date prompts, failure/manual recovery, and confirmation required before extraction.
- [ ] Implement the multi-file source picker/drop handler, column proposal action, confirmation, worker, and saved-grid/Evidence view. Do not reuse legacy upload copying. Existing Create keeps its generation prompts/workers/retries.
- [ ] Test duplicate submission, disconnect, late cancellation, rerun review reset, partial coverage, and flagged proposed values shown in the saved grid. Require flagged/incomplete acknowledgement before Save As.
- [ ] Test native Save As delegation with overwrite confirmation enabled, source-path refusal, cancellation, successful confirmed overwrite, and failure keeping review without a success banner. Normal close waits/cooperates, then discards owned files; startup cleanup has no recovery UI.
- [ ] Run affected Qt/generation/template tests and a native walkthrough with English synthetic sources and the passing evaluation candidate. **Proof:** users can request columns, edit/confirm, inspect every cell's evidence, and save a new or explicitly replaced output.

**Verify:** python -m pytest tests/test_extraction_panel.py tests/test_extraction_worker.py tests/test_widgets.py tests/test_ollama_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_generate_worker.py tests/test_main_window_teardown.py -q with isolated homes, followed by the native walkthrough. Required: focused regressions and the observed Save As/column-review flow pass.

### Task 5: Prepare installer in parallel and qualify after integration

**Modify:** build.py, build.bat, .github/workflows/build.yml, requirements-build.txt only as needed for a tested build version, tests/test_build_script.py, and docs/code-signing.md.
**Reference:** [packaging procedure](../../code-signing.md) and [PRD packaging contract](../../../PRD.md#packaging).

**Interfaces:** Keep the entry point and same standalone payload/resources for installer and ZIP. This is extraction packaging, independent of Task 0's existing-route patch release.

- [ ] Prepare standalone build/resource tests alongside model work; stop this work if the extraction gate fails. Verify prompts, icons, templates, and libraries from outside the checkout.
- [ ] Evaluate Nuitka's built-in NSIS installer support with a pinned tested version before adding a custom script. Test current-user install, shortcuts, upgrade/uninstall, and user-data preservation.
- [ ] After Task 4, qualify the integrated artifacts on clean Windows under PRD prerequisites, without developer Python or Office. Test missing model/runtime, non-blocking model warnings, file extraction/columns/review, Save As, cancellation, and cleanup.
- [ ] Compare installer/ZIP payload inventories and hashes; record default-security results without weakening protection. Actual launch blocks remain failures requiring a decision. Do not publish during preparation.

**Verify:** python -m pytest tests/test_build_script.py -q, then python build.py with the tested environment and manual clean-machine checks. Required: build/artifacts pass their inventory, launch, workflow, and user-data checks.

### Task 6: Qualify the full pipeline and release

**Tests:** full isolated suite, actual-file corpus, tests/test_gen_repo_map.py, and clean-machine/native UI checks.
**Modify:** scripts/evaluate_extraction.py and tests/extraction/test_evaluation.py for --full-pipeline; docs/PROJECT_STATUS.md for current state.

- [ ] Add --full-pipeline to the same CLI. It always reads actual fixture files, runs production sectioning/extraction, writes/reopens the XLSX candidate, and scores saved Data values plus their flags with the Task 1 scorer.
- [ ] Run the full suite in isolated user folders. Run the fixed English corpus through --full-pipeline with the selected candidate and settings; check PRD accuracy/error fractions, coverage, and review burden.
- [ ] Extend the labelled corpus with files too large for one request and score the sectioned path as well as whole-file extraction. Exercise a job at the page limit and a just-over-limit rejection. Complete the UI/package walkthrough: suggested columns, all-cell evidence, highlighted proposals, incomplete-output acknowledgement, cancellation/rerun, overwrite, source-path refusal, and cleanup.
- [ ] Regenerate the map, update status, and check dependency notices. Leave LICENSE unchanged and Alex's business-use decision open.
- [ ] Release only after the full-pipeline quality, coverage/type, Windows launch, and license decisions are resolved. Commit/push/tag/publication require explicit authorization.

**Verify:** python -m pytest -q in isolated homes/base directory, then the Task 1 CLI command with --full-pipeline --report .venv/evaluation/release.json and the manual UI/package checks. Required: the full production output passes release checks; timings decide nothing.

## Plan self-review

Task 1 contains fixtures/labels, actual readers, grounding/scoring, and direct whole-file evaluation. Task 2 adds shared-client requests and whole-file-first extraction, sectioning only oversized files. Task 6 checks the complete saved output. Removed mechanisms do not reappear as tests; remaining checks cover accuracy, literal Excel values, normal workflow failures, and the independent legacy safety patch.
