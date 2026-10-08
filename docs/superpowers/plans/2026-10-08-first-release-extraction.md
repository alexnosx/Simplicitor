# First-release extraction implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution or superpowers:subagent-driven-development if Alex selects delegation. Track steps with checkboxes. Do not execute before Alex approves the revised plan.

**Goal:** Deliver the new [PRD extraction workflow](../../../PRD.md#workflow-scope), preserve existing creation, and ship the independent safety patch first.

**Architecture:** Reuse the existing Ollama client and document libraries through the plain-Python [extraction components](../specs/2026-10-08-document-architecture-design.md#module-responsibilities), with a thin Qt adapter. Evaluate eligible models on canonical units first, then actual readers/sections before writer/UI work.

**Tech stack:** Existing Python, PySide6, python-docx, pdfplumber, pypdf, openpyxl, requests, pydantic, and Nuitka/NSIS. No new runtime dependency is proposed.

**Spec:** [PRD.md](../../../PRD.md) owns requirements/acceptance values; [architecture](../specs/2026-10-08-document-architecture-design.md) owns anchors, allocation/request limits, model profiles, and fit protocol. [UI design](../specs/2026-10-08-document-workspace-ui-design.md) owns presentation; [status](../../PROJECT_STATUS.md) owns B1 and open decisions.

## Global constraints

- This is the only first-release execution plan. Implement file-record extraction and the separate safety release; later increments have no execution tasks here.
- Application, harness, fixture, and build code start only after plan approval. Commit, push, release publication, and dependencies retain their explicit authorization gates.
- Use PRD acceptance values and architecture settings by reference. Store accepted implementation settings once in defaults.py and reference them from the fixture/profile manifest.
- English-only fixtures. Independent labels never enter proposal/extraction prompts or determine flags. Track complete file/field denominators.
- The GPU fit check is mandatory for evaluation eligibility. The product's small/unknown-model warning is non-blocking; do not turn it into a runtime prohibition.
- Diagnostics/reports contain aggregate metadata, not contents, raw model/server exceptions, or sensitive paths. Timings are optional information, never a gate, selection criterion, or performance claim.
- For pytest, use .venv/Scripts/python.exe and a fresh --basetemp below .venv. Redirect USERPROFILE/APPDATA/LOCALAPPDATA into a fresh test home for widget/full-suite runs. Do not write into real user folders.

Each task starts with focused failing tests, implements the smallest contract, then reruns the same tests. Existing tests change only where the new contract supersedes their expectation; do not remove failure coverage.

## Review focus

- A real quote assigned to the wrong column must count as an unflagged semantic error; Task 1 tests both sides of the PRD error budget.
- A small weight download can still exceed the target with KV cache; Task 1 tests context, full GPU residency, and running memory eligibility.
- Same-named files and fields spread over pages must retain one complete row per attachment; Tasks 2 and 3 test identity and carry state.
- Flagged proposed values, leading-zero IDs, and formula-like strings must survive saved-file review; Tasks 1 and 4 test data projection and literal typing.
- Cancelled/rerun jobs and Save As failures must not save stale or partial results or change sources; Tasks 3 through 5 test review reset, source-path refusal, overwrite, and failures.

## Work order

Task 0 independently prepares and, with Alex's go, publishes v1.2.1 as soon as its own checks pass. It does not wait for extraction, model gates, or the installer. Task 1 gates extraction. Tasks 2 through 5 are sequential. Task 6 installer preparation may run alongside Tasks 1 through 4, stops on an extraction gate failure, and qualifies the integrated feature after Task 5. Task 7 qualifies the new direction. Parallel scheduling is not authorization to dispatch agents or publish.

### Task 0: Disable legacy Edit and release v1.2.1 independently

**Modify:** simplicitor/app/main_window.py, simplicitor/app/workers/manipulate_worker.py, simplicitor/app/config/defaults.py, build.py for patch version, CHANGELOG.md, and docs/PROJECT_STATUS.md. Inspect .github/workflows/build.yml's tag-triggered publication before any release action.
**Tests:** tests/test_manipulate_worker.py, tests/test_widgets.py, tests/test_build_script.py, and affected MainWindow/generation/template tests.

**Interfaces:** Keep constructors, signals, creation routes, and ManipulationError imports. MainWindow._on_save_requested and ManipulateWorker.run must return disabled/failed before extraction, backup, inference, or writes. Disable visible Edit in this patch; Task 5 removes it from the extraction shell. Build product version is 1.2.1.0.

- [ ] Add test_legacy_edit_disabled_before_io for both entry points with empty, echoed, and formerly truncating scenarios: assert zero extractor/model/backup/writer calls, no completed signal, and unchanged source bytes. Confirm the current source fails.
- [ ] Add unconditional guards and one shared message; preserve the legacy module needed by template exception imports. Update version expectations and release notes.
- [ ] Run focused safety/build/generation/template/teardown regressions in an isolated home.
- [ ] Build the patch using the existing release route; no new installer is required for this patch. On clean Windows/default protection, verify disabled Edit cannot write sources, existing Create/templates work, and the artifact has the patch version. Record the exact artifact/hash and any launch block.
- [ ] Prepare release notes and the concrete artifact, then request Alex's explicit publication go. On authorization, publish v1.2.1 through the reviewed release route immediately after its own checks pass. Check the published asset/version and safety behavior; do not make extraction progress a prerequisite.

**Verify:** python -m pytest tests/test_manipulate_worker.py tests/test_widgets.py tests/test_build_script.py tests/test_generate_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_main_window_teardown.py -q with isolated home/base directory, then python build.py and the patch walkthrough. Required: safety/regressions/build pass. Task 0's final release outcome is the verified v1.2.1 asset after publication go; before go, report prepared and awaiting publication, not released.

### Task 1: Establish contracts and evaluate eligible models before UI

**Create:** simplicitor/extraction/__init__.py, simplicitor/extraction/models.py, simplicitor/extraction/grounding.py; scripts/evaluate_extraction.py; tests/extraction/test_grounding.py, tests/extraction/test_evaluation.py; tests/extraction/fixtures/manifest.json, profiles.json, English documents, canonical units, and independently checked labels.
**Modify:** simplicitor/app/services/ollama_client.py for optional extraction profile arguments and running metadata; simplicitor/app/config/defaults.py for accepted settings; tests/test_ollama_client.py.

**Interfaces:**
- ColumnSpec(id, label, description, kind, thousands_separator, decimal_separator, date_order); kind is text/integer/decimal/date and date_order can remain unresolved until ambiguity exists.
- SourceUnit(anchor, text, kind, order, structural_group); RecordInput(record_id, source_id, units) represents one file. SourceDocument later adds original path, label, bytes, page cost, and issues.
- FieldProposal(value: str | None, quote: str, anchor: str); FieldResult(proposal, typed_value, flagged, issues). Its data_value property returns typed_value when valid, otherwise the proposed literal string or None. Writer and scorer consume that same projection.
- Issue(code, source_id, anchor, safe_message); ExtractionProfile(model, context/output/settings). build_response_schema(columns: tuple[ColumnSpec, ...], record_ids: tuple[str, ...]) -> dict and validate_field(proposal: FieldProposal, column: ColumnSpec, units: Mapping[str, SourceUnit]) -> FieldResult live in models.py/grounding.py respectively.
- In scripts/evaluate_extraction.py, ExpectedField(expected_value, expected_type) is a label-only contract. score_results(actual: Mapping[tuple[str, str], FieldResult], labels: Mapping[tuple[str, str], ExpectedField]) -> EvaluationReport owns correct/incorrect/unflagged counts, denominator, flag rates, eligibility, errors, and optional timings; keys are (record_id, column_id). passes_quality_gate(correct: int, unflagged_wrong: int, total: int) -> bool implements PRD fractions without percentage rounding. eligible_fit(info: Mapping, loaded: Mapping, profile: ExtractionProfile) -> tuple[bool, str] implements the architecture protocol.
- Extend OllamaClient.generate with keyword-only options: dict | None, think: bool | str | None, local_only: bool = False, preserving old defaults/string return. Add get_running_models(timeout: int) -> list[dict] for full /api/ps records without changing get_running_model's existing contract. Extraction-only transport requires loopback, disabled environment proxies, and refused redirects; separately preflight local-only runtime/model use.

- [ ] Add grounding/scorer tests for normalized quotes, wrong source/anchor, leading-zero text, finite numeric grammar, English separator defaults/overrides, all PRD month-name date forms, ambiguous numeric dates, missing proposals, conflicts, and changed column schemas. Confirm failures before implementation.
- [ ] Add test_real_quote_in_wrong_column_is_unflagged. Its grounded_invoice_date fixture comes from validate_field using a real invoice-date quote; expected_due_date is the independent different due date. Prove the scorer counts the semantic error, then pin the acceptance boundaries in test_semantic_error_budget:

~~~python
def test_real_quote_in_wrong_column_is_unflagged(grounded_invoice_date, expected_due_date):
    assert not grounded_invoice_date.flagged
    report = score_results(
        {("invoice", "due_date"): grounded_invoice_date},
        {("invoice", "due_date"): expected_due_date},
    )
    assert report.correct == 0
    assert report.unflagged_wrong == 1


def test_semantic_error_budget():
    assert passes_quality_gate(correct=199, unflagged_wrong=1, total=200)
    assert passes_quality_gate(correct=198, unflagged_wrong=2, total=200)
    assert not passes_quality_gate(correct=197, unflagged_wrong=3, total=200)
    assert passes_quality_gate(correct=190, unflagged_wrong=2, total=200)
    assert not passes_quality_gate(correct=189, unflagged_wrong=0, total=200)
~~~

- [ ] Add tests that an all-flagged run reports review burden, flags never come from labels, and a flagged proposal is scored as the value actually destined for Data rather than an automatic blank.
- [ ] Add test_fit_requires_context_and_full_gpu_allocation for matching/mismatched context, CPU offload, over-budget memory, unknown fields, and unknown/undersized model metadata. Reference-only runs never become selectable, even with a higher score.
- [ ] Implement schema construction, deterministic derivation, and scoring; never use ExcelGenerator._coerce_value. Assert the actual HTTP format contains the generated schema. Test optional settings preserve old requests, loopback/proxy/redirect rules, and a synthetic secret in exceptions never reaches diagnostic output.
- [ ] Build the PRD-sized English contract/invoice corpus with python-docx and existing pypdf. Include file-level fields inside DOCX tables and across PDF pages, missing/competing dates, English date forms, separators, leading zeros, and literal formula-like text. No line-item/table-register fixture or continuation matching. Confirm independent labels/canonical units and keep labels outside prompts.
- [ ] Implement CLI --manifest, --profiles, --input-mode canonical|files, --report. Canonical mode calls the existing client with confirmed columns/known file records and uses production grounding/data projection. Freeze digest, quantization, context, KV-cache/parallelism/thinking settings before scoring; no hidden retries or per-fixture tuning.
- [ ] On B1, verify at least two eligible configurations using the architecture fit protocol, including near-budget requests and running API/allocation evidence. If fewer fit, report the setup blocker. Score eligible models and optional separately marked references; malformed/missing outputs remain failures in the denominator.
- [ ] Select a passing eligible configuration by accuracy and review burden, repeat its full run, and record reproducibility. Optional timings gate nothing.
- [ ] **Stop gate:** if no eligible configuration passes, including when only a larger reference passes, stop extraction and its installer work and report. Alex decides any change. This does not block the independent safety release.

**Verify:** python -m pytest tests/extraction/test_grounding.py tests/extraction/test_evaluation.py tests/test_ollama_client.py -q. Then python scripts/evaluate_extraction.py --manifest tests/extraction/fixtures/manifest.json --profiles tests/extraction/fixtures/profiles.json --input-mode canonical --report .venv/evaluation/model-only.json. Required: unit checks pass, at least two fits verified, and at least one eligible model passes the PRD gates. Canonical results do not establish production reading.

### Task 2: Read anchored file sources and expose PDF coverage

**Create:** simplicitor/extraction/source_readers.py; tests/extraction/test_source_readers.py.
**Modify:** simplicitor/extraction/models.py for SourceDocument. Read legacy _extract_docx/_extract_pdf as starting points without changing legacy Edit.

**Interfaces:** read_source(path: Path, source_id: str) -> SourceDocument dispatches to read_docx/read_pdf. SourceDocument carries source_id, original path, label, immutable bytes/units, page-budget cost, and issues; record_id equals source_id. Use architecture anchors/limits from shared configuration.

- [ ] Add test_docx_reads_complete_paragraphs_and_cells beyond the legacy truncation limit, including table-based invoice fields, document order, empty units, physical-cell aliases, unsupported structures, and stable anchors. Assert full supported text and unchanged source bytes; no record continuation logic.
- [ ] Add PDF tests for text, zero/near-zero pages, malformed/password-protected input, and fields across pages. Assert page anchors/counts and visible incomplete coverage; no table extractor is called.
- [ ] Test exact/over-limit job/file allocations and page-equivalent accounting using shared settings. Preserve separate IDs/order for same-named or identical-content sources.
- [ ] Implement readers over immutable bytes with python-docx/pdfplumber; reject unsupported input. Never call _truncate, join away unit boundaries, or alter sources.
- [ ] Compare actual fixture units/anchors independently against canonical units. **Proof:** file fields and supported tables/pages are complete, anchored, bounded, and accounted for.

**Verify:** python -m pytest tests/extraction/test_source_readers.py tests/test_file_manipulator.py -q. Required: new readers pass and untouched legacy reader tests retain their existing behavior.

### Task 3: Propose columns and extract sectioned file records

**Create:** simplicitor/extraction/sectioning.py, simplicitor/extraction/pipeline.py; tests/extraction/test_sectioning.py, tests/extraction/test_pipeline.py.
**Modify:** simplicitor/extraction/models.py and scripts/evaluate_extraction.py for production-reader evaluation.

**Interfaces:** make_sections(records: tuple[RecordInput, ...], profile: ExtractionProfile) -> tuple[Section, ...]. Section contains ID, record inputs, and covered-unit IDs; extract maintains pending file-field state between calls. propose_columns(request: str, first_source: SourceDocument, profile: ExtractionProfile, client: OllamaClient, cancel: Event) -> tuple[ColumnSpec, ...]. extract(documents: tuple[SourceDocument, ...], columns: tuple[ColumnSpec, ...], request: str, profile: ExtractionProfile, client: OllamaClient, cancel: Event, progress: Callable) -> ExtractionResult returns file/field roster, results, source paths, issues, and coverage. ExtractionCancelled distinguishes cancellation.

- [ ] Add tests proving no source-unit overlap, DOCX table-row grouping, page-boundary splitting, open file-field carry, oversized-unit issues, and one output record per attachment. No mode enum or table/header mapping is introduced.
- [ ] Add column-proposal tests: request plus the first-source sample only, schema-constrained names/descriptions/types, invalid-type text fallback, English defaults, empty/invalid output, editable retry/manual fallback, and no label leakage. Proposal sampling is disclosed; extraction still covers all selected source units.
- [ ] Add date-inspection tests: all supported month-name/unambiguous numeric forms need no order prompt; genuinely ambiguous numeric dates require an order decision only for affected date columns. Confirmed separator overrides drive derivation.
- [ ] Test missing/duplicate/unknown file IDs, fields, invalid JSON, wrong anchors/quotes, output exhaustion, and contradictory observations. Retain every requested file/column and proposal/issue instead of omitting failed values.
- [ ] Implement bounded schema calls, file-state accumulation, and coverage tracking. Keep agreeing evidence; flag conflicts. Source content is evidence, not executable instructions. Failed sections remain visible; no unconstrained fallback or hidden retry.
- [ ] Test timeout, cancellation before/after a late response, source changes followed by rerun, and partial text coverage. Cancelled work never yields a saveable result, and setup remains available.
- [ ] Run unit checks and selected-model evaluation on actual readers/production sections. **Gate:** the eligible frozen configuration must pass the same PRD fractions with full file accounting. On failure stop writer/UI and report; the canonical result cannot override it.

**Verify:** python -m pytest tests/extraction/test_sectioning.py tests/extraction/test_pipeline.py -q, then the Task 1 CLI with --input-mode files --report .venv/evaluation/actual-files.json. Required: production-reader gate passes before downstream work.

### Task 4: Write the saved candidate and implement standard Save As copying

**Create:** simplicitor/extraction/xlsx_writer.py, simplicitor/extraction/jobs.py; tests/extraction/test_xlsx_writer.py, tests/extraction/test_jobs.py.
**Modify:** simplicitor/extraction/models.py for Candidate(job_id, path, source_paths, issues) and ReviewCell(row, column, value, data_type, evidence).

**Interfaces:** write_candidate(result: ExtractionResult, columns: tuple[ColumnSpec, ...], path: Path) -> Candidate; read_candidate(candidate: Candidate) -> tuple[ReviewCell, ...]. create_job(app_data: Path) -> Path; save_candidate(candidate: Candidate, destination: Path, acknowledge_issues: bool) -> Path; discard_job(job_dir: Path) -> None; cleanup_old_jobs(app_data: Path, now: datetime) -> int. Call save_candidate only after the native Save As dialog accepts the destination with normal overwrite confirmation enabled; dialog cancellation makes no core call.

- [ ] Add saved-file tests for typed valid values, highlighted literal flagged proposals, highlighted missing proposals, leading-zero IDs, NaN/inf/1_000 text, =1+1 and =HYPERLINK(...) strings in both sheets, English dates, Evidence issues, and cell selection mapping. Assert flagged text is retained rather than blanked or coerced.
- [ ] Test invalid controls, excessive cell text, and unsafe numeric precision. Unrepresentable workbook content fails visibly; values/evidence are never silently clipped or rounded.
- [ ] Implement the dedicated writer using FieldResult.data_value, literal string typing, confirmed date/number formats, and shared styling. Reopen the candidate to verify its saved values/types, records, Evidence, and flags; build review from that file.
- [ ] Keep one candidate.xlsx in each owned app-data job. Rerunning replaces it and clears old review; failed/cancelled runs cannot offer the previous file as their new result.
- [ ] Add test_save_as_refuses_source_path for each source, case/normalized variants, and existing aliases. Test new destinations, replacing the destination chosen through Save As, and temporary write/rename failure. Assert sources and previous destination remain intact on failure and no success is emitted. Task 5 tests native confirmation/cancellation before the core call.
- [ ] Implement destination-folder temporary copying followed by rename/replace only after the copy closes successfully. Keep review available after failure; normal Windows overwrite confirmation remains the user's choice.
- [ ] Test normal-close cleanup after handles finish and startup age boundaries from PRD retention. Remove only owned app-data job folders; leave newer jobs and unrelated files. No crash-recovery screen or hash-bound candidate token.

**Verify:** python -m pytest tests/extraction/test_xlsx_writer.py tests/extraction/test_jobs.py -q. Required: saved-grid values/Evidence agree, flagged proposals remain literal, confirmed overwrite succeeds, source refusal/failed writes preserve existing bytes, and cleanup respects ownership/age.

### Task 5: Build the Create workspace, column editor, and grid review

**Create:** simplicitor/app/widgets/create_workspace.py, simplicitor/app/widgets/extraction_panel.py; simplicitor/app/workers/extraction_worker.py; tests/test_extraction_panel.py, tests/test_extraction_worker.py.
**Modify:** simplicitor/app/main_window.py, simplicitor/app/widgets/capability_banner.py, simplicitor/app/workers/ollama_worker.py for selected-model metadata lookup, simplicitor/app/config/defaults.py for warning copy/threshold, and affected tests/test_widgets.py, tests/test_ollama_worker.py, teardown tests.

**Interfaces:** CreateWorkspace hosts existing CreatePanel and ExtractionPanel. ExtractionPanel emits inspect_requested, propose_requested, extract_requested, cancel_requested, and save_requested with frozen settings. ExtractionWorker emits progress, inspection_ready, columns_ready, candidate_ready, failed, and cancelled; no widget access. Add OllamaWorker.request_model_params(model_name: str) -> None as a queued Qt slot, reusing metadata parsing and model_params_ready. MainWindow._on_model_changed queues the selected-model lookup; _on_model_params_ready ignores stale names. Loaded-model polling must not replace an explicit selection or its warning state.

- [ ] Add Qt tests for the default shell, hidden Edit, no record-mode/header-mapping controls, and retained prompt/template routing.
- [ ] Add test_selected_model_warning for below-minimum, exact-minimum, above-minimum, and unknown sizes. Assert PRD copy, no blocked action, updates when the selected model differs from the loaded model, and stale metadata cannot change the selection/banner. Keep dismiss behavior per selection.
- [ ] Add proposal/editor tests for first-source suggestions, edit/add/remove, proposed/fallback types, English defaults/overrides, conditional numeric-date prompts, failure/manual recovery, and confirmation required before extraction.
- [ ] Implement the multi-file source picker/drop handler, column proposal action, confirmation, worker, and saved-grid/Evidence view. Do not reuse legacy upload copying. Existing Create keeps its generation prompts/workers/retries.
- [ ] Test duplicate submission, disconnect, late cancellation, rerun review reset, partial coverage, and flagged proposed values shown in the saved grid. Require flagged/incomplete acknowledgement before Save As.
- [ ] Test native Save As delegation with overwrite confirmation enabled, source-path refusal, cancellation, successful confirmed overwrite, and failure keeping review without a success banner. Normal close waits/cooperates, then discards owned files; startup cleanup has no recovery UI.
- [ ] Run affected Qt/generation/template tests and a native walkthrough with English synthetic sources and the passing eligible model. **Proof:** users can request columns, edit/confirm, inspect every cell's evidence, and save a new or explicitly replaced output.

**Verify:** python -m pytest tests/test_extraction_panel.py tests/test_extraction_worker.py tests/test_widgets.py tests/test_ollama_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_generate_worker.py tests/test_main_window_teardown.py -q with isolated homes, followed by the native walkthrough. Required: focused regressions and the observed Save As/column-review flow pass.

### Task 6: Prepare installer in parallel and qualify after integration

**Modify:** build.py, build.bat, .github/workflows/build.yml, requirements-build.txt only as needed for a tested build version, tests/test_build_script.py, and docs/code-signing.md.
**Reference:** [packaging procedure](../../code-signing.md) and [PRD packaging contract](../../../PRD.md#packaging).

**Interfaces:** Keep the entry point and same standalone payload/resources for installer and ZIP. This is extraction packaging, independent of Task 0's existing-route patch release.

- [ ] Prepare standalone build/resource tests alongside model work; stop this work if the extraction gate fails. Verify prompts, icons, templates, and libraries from outside the checkout.
- [ ] Evaluate Nuitka's built-in NSIS installer support with a pinned tested version before adding a custom script. Test current-user install, shortcuts, upgrade/uninstall, and user-data preservation.
- [ ] After Task 5, qualify the integrated artifacts on clean Windows under PRD prerequisites, without developer Python or Office. Test missing model/runtime, non-blocking model warnings, file extraction/columns/review, Save As, cancellation, and cleanup.
- [ ] Compare installer/ZIP payload inventories and hashes; record default-security results without weakening protection. Actual launch blocks remain failures requiring a decision. Do not publish during preparation.

**Verify:** python -m pytest tests/test_build_script.py -q, then python build.py with the tested environment and manual clean-machine checks. Required: build/artifacts pass their inventory, launch, workflow, and user-data checks.

### Task 7: Qualify the first release

**Tests:** full isolated source suite, actual-file evaluation, tests/test_gen_repo_map.py, and clean-machine/native UI records.
**Documentation:** docs/PROJECT_STATUS.md owns current state; evaluation reports own measurements; PRD.md owns targets.

- [ ] Run the full suite with fresh isolated user folders/base directory. Do not interpret legacy reconstruction tests as preservation guarantees.
- [ ] Repeat the final selected eligible profile on the fixed English actual-file corpus. Verify allocation/context, accuracy, unflagged-error fraction, coverage, proposal handling, review burden, and privacy diagnostics. No speed gate or timing approval.
- [ ] Exercise a job at the aggregate page limit and a just-over-limit rejection, with synthetic inputs and fields across sections. Verify complete file/column accounting and no silent truncation.
- [ ] Complete nontechnical-user and clean-machine checks: suggestions/edits, evidence for valid/flagged values, unreadable pages, partial acknowledgement, cancellation/rerun, normal overwrite, source refusal, and cleanup.
- [ ] Regenerate the map and update status/open decisions. Check packaged dependency notices. Leave LICENSE unchanged and Alex's business-use decision open until resolved.
- [ ] **Release decision:** do not call the new product ready while model eligibility, either quality fraction, source coverage/type behavior, Windows launch, or the business-use license remains unresolved. Commit/push/tag/publication require explicit authorization.

**Verify:** python -m pytest -q in isolated homes/base directory, final actual-file CLI scoring/fit report, and manual packaging/UI records. Required: the defined release gates pass; optional timing observations change no gate.

## Plan self-review

All nine review items have owners: hardware/model/language/gates in Task 1, file-only readers/sections and column suggestions in Tasks 2/3, flagged values and simplified Save As/cleanup in Task 4, selected-model warnings and column editor in Task 5, and the independent patch release in Task 0. Architecture now owns technical limits/anchors/profile settings. Later row extraction/editing/reporting/recognition have no implementation tasks. Shared contracts precede their consumers; this revision writes documentation only.
