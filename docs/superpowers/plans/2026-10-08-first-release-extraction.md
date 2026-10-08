# First-release extraction implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution or superpowers:subagent-driven-development if Alex selects delegation. Steps use checkboxes for tracking. Do not execute this plan before Alex approves it.

**Goal:** Deliver the new extraction route defined by [PRD.md](../../../PRD.md#workflow-scope), preserving the existing creation routes.

**Architecture:** Add the small extraction package described by the [architecture](../specs/2026-10-08-document-architecture-design.md#module-responsibilities), with a thin Qt worker and a dedicated saved-candidate writer. Reuse the existing Ollama client and document libraries. Keep the model-only gate ahead of production readers/UI, then repeat the gate on real reader/sectioner output.

**Tech stack:** Existing Python, PySide6, python-docx, pdfplumber, pypdf, openpyxl, requests, pydantic, and Nuitka/NSIS. No new runtime dependency is proposed.

**Spec:** [PRD.md](../../../PRD.md) owns scope and every numerical acceptance value. [UI design](../specs/2026-10-08-document-workspace-ui-design.md) owns presentation. [Project status](../../PROJECT_STATUS.md) owns the benchmark environment and open decisions.

## Global constraints

- This is the only execution plan for the first release. Historical phase plans are references, not additional work queues.
- Implement only the PRD first-release scope and the separately reviewable safety patch. Do not build later editing, reporting, recognition, or a shared legacy Create approval flow.
- Read the PRD's proposed limits/evaluation gates before execution. Approval must settle the numerical proposals; copy approved values into one runtime configuration and the evaluation manifest with a PRD reference, not competing documentation tables.
- Application, harness, fixtures, and build code start only after plan approval. Commit/push/publication and new dependencies still require their own explicit authorization.
- Keep synthetic fixture labels separate from prompts. Diagnostics contain aggregate metadata, never client contents or raw model/server exceptions.
- Use a fresh test temp directory and redirect USERPROFILE/APPDATA/LOCALAPPDATA to a test home for widget/full-suite runs. Do not create test files in real user folders.

Use .venv/Scripts/python.exe for the verification commands below. Add --basetemp pointing to a fresh directory under .venv for every pytest invocation; if a proposed directory already exists, choose another rather than deleting unknown content. Red tests and green tests use the same focused test modules. Live evaluation commands run only after unit checks and plan approval.

## Review focus

- A correct-looking quote can support the wrong semantic field. Task 1 must fail the gate on an unflagged invoice-date/due-date substitution.
- Same-named or identical-content attachments still represent separate file records. Tasks 2 and 3 preserve identities and row order.
- A text-bearing PDF may contain unreadable pages and continued tables. Tasks 2 and 3 expose coverage and continuation uncertainty instead of losing records.
- Formula-like strings and finite-looking text can be reinterpreted by Excel/Python. Tasks 1 and 4 pin typed derivation and literal saved-cell behavior.
- A late model response, stale review, or destination race can publish the wrong file. Tasks 3, 4, and 5 exercise cancellation, approval invalidation, and no-replacement publication.

## Work order

Task 0 is a separate v1.2 safety patch. Task 1 is the first extraction feature work and stops dependent development if no configuration passes. Tasks 2 through 5 are sequential. Task 6 packaging may prepare the existing standalone build alongside Tasks 1 through 4; it must stop on a failed quality gate and cannot qualify the final feature before Task 5. Task 7 qualifies the combined result. This is parallel work scheduling, not authorization to dispatch agents or publish releases.

### Task 0: Disable legacy Edit as a separate v1.2 patch

**Modify:** simplicitor/app/main_window.py, simplicitor/app/workers/manipulate_worker.py, and simplicitor/app/config/defaults.py. **Tests:** tests/test_manipulate_worker.py, tests/test_widgets.py, and affected MainWindow tests.

**Interfaces:** Keep existing constructors, signals, generator routes, template imports, and ManipulationError. Add one shared disabled-message constant. MainWindow._on_save_requested and ManipulateWorker.run must fail safely before extraction, backup, model calls, or writes. Disable the visible Edit panel for this patch; Task 5 removes it from the first-release shell.

- [ ] Add tests invoking both entry points with empty, echo, and formerly truncating response scenarios. Assert failed/disabled state, zero model/extractor/backup/writer calls, no completed signal, and unchanged source bytes. This tests the unconditional block, not detection heuristics.
- [ ] Run those tests and confirm the current implementation fails the new safeguards.
- [ ] Add the early guards and disabled UI/message without changing FileManipulator, its exception imports, or existing Create/template execution.
- [ ] Run the safety tests plus tests/test_generate_worker.py, tests/test_main_window_template.py, tests/test_template_worker.py, and tests/test_main_window_teardown.py in an isolated test home. Update affected legacy expectations to the new disabled contract, not by removing failure coverage.
- [ ] Review this as an independent patch. **Proof:** no source writes or model calls can originate from legacy Edit, and existing creation/template regressions pass. Do not combine unrelated fixes into it.

**Verify:** python -m pytest tests/test_manipulate_worker.py tests/test_widgets.py tests/test_generate_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_main_window_teardown.py -q, with the isolated test home and fresh base directory above. Required result: all focused checks pass.

### Task 1: Establish contracts and run the model gate before UI

**Create:** simplicitor/extraction/__init__.py, simplicitor/extraction/models.py, simplicitor/extraction/grounding.py; scripts/evaluate_extraction.py; tests/extraction/test_grounding.py, tests/extraction/test_evaluation.py; tests/extraction/fixtures/ with manifest.json, profiles.json, independently checked labels/canonical units, and the synthetic DOCX/PDF corpus. **Modify:** simplicitor/app/services/ollama_client.py only for optional profile arguments; tests/test_ollama_client.py.

**Interfaces:** Define immutable or frozen contracts in models.py:

- ColumnSpec: id, label, description, kind, decimal/group separators, and date order. ColumnType is text/integer/decimal/date.
- SourceUnit: anchor, text, structural kind, order, and row/group identity when applicable.
- RecordInput: record_id, source_id, units, and separate header/context units.
- RecordMode is file or table_row. TableMapping carries selected table IDs, header anchors/signature, and confirmed field-to-cell positions. SourceDocument later adds the source's original path/hash, immutable unit views, and issues.
- FieldProposal: nullable string value, quote, and anchor. FieldResult: proposal, typed value, status, and issues.
- Issue: code, source_id, anchor, and safe display information. ExtractionProfile: model and explicit request settings from the approved PRD profile.
- build_response_schema(columns: tuple[ColumnSpec, ...], record_ids: tuple[str, ...]) -> dict; validate_field(proposal: FieldProposal, column: ColumnSpec, units: Mapping[str, SourceUnit]) -> FieldResult.
- score_results(actual, labels) -> EvaluationReport; report stores accuracy, incorrect/unflagged counts, flag rates, failures, and cold/warm timings. Labels are never passed to extraction or grounding.
- Extend OllamaClient.generate with keyword-only options: dict | None, think: bool | str | None, and local_only: bool = False, preserving existing defaults and its string return. Omit new request properties when unset; existing workers keep their behavior. For extraction's local_only calls require a loopback endpoint and use a requests Session with environment proxies disabled and redirects refused. Preflight the supported local-only model/runtime configuration separately; loopback transport alone is not that proof.

- [ ] Write grounding/scorer/client tests first. Cases include whitespace-normalized quotes, wrong source/anchor, unsupported numeric grammar, non-finite decimals, leading-zero text, ambiguous dates, missing proposals, and schema shaped from changed columns. Confirm failures before adding implementation.
- [ ] Include the semantic counterexample: a syntactically valid due-date field cites a real invoice date, passes literal derivation, but is wrong against the labels. Assert an unflagged-error gate failure even when overall accuracy passes. Also assert that an all-flagged result exposes its review burden rather than receiving a usability pass.
- [ ] Implement strict parsing/derivation and schema construction. Use existing dependencies; do not reuse ExcelGenerator._coerce_value, add a calculator, or relax failed evidence. Test that the schema is actually sent in the HTTP format field, not just mentioned in the prompt.
- [ ] Test extraction transport refuses remote endpoints/redirects and does not use an injected proxy environment. Put a synthetic secret canary in fake model/server exceptions and verify it never reaches diagnostic output. Verify old callers omit the new settings and retain their request behavior.
- [ ] Create the PRD-sized synthetic corpus: balanced DOCX/text-PDF examples with single-file contracts/invoices and table-row registers, including continuation/repeated headers. Use python-docx and existing pypdf for fixture generation rather than adding a PDF-generation dependency. Store independently checked canonical units and labels; tests verify labels are absent from model inputs.
- [ ] Implement the CLI with --manifest, --profiles, --input-mode canonical|files, and --report arguments. The manifest/profile files store the approved PRD configuration for the run. Canonical mode consumes fixture units, confirmed columns, and known records, calls the existing client, and runs the production grounding checker. Write aggregate JSON/Markdown scores. A schema-compatibility preflight freezes supported thinking settings before scoring; no per-document tuning, hidden retries, or unconstrained fallback.
- [ ] Run unit tests with fake clients first. Then run the CLI on benchmark B1 using the candidate list in PRD.md. Record exact digests/versions, profile, request failures, field-slot denominators, and timings. Score malformed/missing outputs as failures, not skipped fixtures.
- [ ] Select a passing configuration by accuracy, then review burden and warm latency. Repeat its full model-only run to establish reproducibility. Bring the measured time-per-page target and selected profile to Alex for approval before locking release performance claims.
- [ ] **Stop gate:** if no configuration passes both PRD quality gates, stop the feature and parallel packaging work and report the scores. Do not build readers/UI around a failed model or lower the gate without Alex's decision.

The canonical-unit gate intentionally isolates model capability. It does not prove production reading. Task 3 repeats evaluation on actual files before downstream work.

**Verify:** python -m pytest tests/extraction/test_grounding.py tests/extraction/test_evaluation.py tests/test_ollama_client.py -q. Then python scripts/evaluate_extraction.py --manifest tests/extraction/fixtures/manifest.json --profiles tests/extraction/fixtures/profiles.json --input-mode canonical --report .venv/evaluation/model-only.json. Required result: unit checks pass and at least one configuration passes the PRD quality gates, with timings and flag counts reported.

### Task 2: Implement anchored source readers and PDF coverage

**Create:** simplicitor/extraction/source_readers.py; tests/extraction/test_source_readers.py. **Modify:** simplicitor/extraction/models.py for SourceDocument and its record views, and simplicitor/app/config/defaults.py for approved extraction limits. Read the legacy methods as a starting point; do not modify them.

**Interfaces:** read_source(path: Path, source_id: str) -> SourceDocument dispatches to read_docx and read_pdf. SourceDocument carries label, original path/hash, immutable file units, table records, page-budget cost, and issues. Readers take immutable bytes after size/package checks and return deterministic anchors. Runtime approved limits belong in one extraction configuration in app/config/defaults.py.

- [ ] Add failing tests for a DOCX exceeding the old truncation limit, body paragraph/table order, table-cell anchors, empty units, merged-cell aliases, and unsupported structures. Assert full supported text, unique stable anchors, and unchanged file hashes. Add exact-limit/over-limit allocation and DOCX page-equivalent cases using approved configuration values.
- [ ] Add PDF tests for normal text, zero/near-zero pages, page/table/row anchors, malformed/password-protected input, repeated headers, and table/text alternative views. Assert every page is accounted for and unreadable pages cannot become an empty-success result. Include the threshold boundary from runtime configuration rather than a second literal.
- [ ] Implement new readers using python-docx document-order traversal and pdfplumber page/table access. Retain DOCX cell coordinates; avoid alias duplication by reading physical cells. Detect unsupported body constructs instead of silently extending the support envelope.
- [ ] Keep PDF page units and table records as alternative views. Mode selection decides which is processed; do not submit both representations or introduce record deduplication. Reject unsupported extensions regardless of content or picker behavior.
- [ ] Run reader tests and independently compare actual fixture units/anchors with the authored canonical corpus. Verify same-named/identical-content files keep distinct source IDs. **Proof:** supported data is complete, anchored, bounded by explicit limits, and the legacy Edit implementation is unchanged.

**Verify:** python -m pytest tests/extraction/test_source_readers.py tests/test_file_manipulator.py -q. Required result: new reader checks pass and the untouched legacy reader tests retain their existing behavior.

### Task 3: Build sectioning and the grounded extraction pipeline

**Create:** simplicitor/extraction/sectioning.py, simplicitor/extraction/pipeline.py; tests/extraction/test_sectioning.py, tests/extraction/test_pipeline.py. **Modify:** simplicitor/extraction/models.py and scripts/evaluate_extraction.py to accept the production-reader mode.

**Interfaces:** records_for(document: SourceDocument, mode: RecordMode, mapping: TableMapping | None) -> tuple[RecordInput, ...]; make_sections(records, profile) -> tuple[Section, ...]. Section carries section_id, record inputs, context-unit IDs, covered-unit IDs, and pending record IDs. extract(documents, columns, mode, mapping, profile, client, cancel: Event, progress: Callable) -> ExtractionResult returns ordered record IDs, each record's field results, source identities, issues, and a per-unit processed/excluded/failed coverage map. ExtractionCancelled distinguishes cancellation from failure.

- [ ] Write failing tests that prove sections do not overlap, anchors remain stable, a table row is not split, open state is carried, and oversized units fail visibly. Table tests cover matching repeated headers and ambiguous continuations. File-mode tests preserve one known row per attachment across sections; do not implement multi-narrative-record discovery.
- [ ] Test missing/duplicate/unknown model record IDs, missing fields, contradictory field observations, invalid JSON, wrong anchors/quotes, and output exhaustion. Assert all known records/columns remain, failed fields are flagged, and failed sections create coverage issues. There is no record-deduplication test or subsystem.
- [ ] Implement mode-specific rosters and structural sections. Estimate request/schema/carry-state size conservatively; if it cannot fit the approved profile, return an issue instead of cutting content. Header context is separate from allowed field-evidence units.
- [ ] Implement strict schema calls and field checks. Merge verified partial fields into the known record; retain the first agreeing evidence and flag conflicts. Do not invent absent values or retry silently. Exclude raw prompts/responses/exception bodies from diagnostics.
- [ ] Test cancellation before a call and after a deliberately late response, timeout, malformed source, partial text coverage, and label leakage. Assert no cancelled job returns a publishable result and setup remains available to the caller. Partial/flagged data is explicit, never complete-success by omission.
- [ ] Run unit tests, then rerun the selected model through actual fixture readers and production sectioning. Compare final typed Data slots and independently generated flags to labels using the Task 1 scorer.
- [ ] **Proof/gate:** the actual-file pipeline passes the same PRD accuracy/visibility gates with complete record accounting. On failure stop writer/UI work and report; the earlier canonical result cannot override this failure.

**Verify:** python -m pytest tests/extraction/test_sectioning.py tests/extraction/test_pipeline.py -q. Then run the Task 1 CLI with --input-mode files and --report .venv/evaluation/actual-files.json. Required result: tests and the actual-file quality gates pass for the selected frozen profile.

### Task 4: Write and bind the saved XLSX candidate

**Create:** simplicitor/extraction/xlsx_writer.py, simplicitor/extraction/jobs.py; tests/extraction/test_xlsx_writer.py, tests/extraction/test_jobs.py. **Modify:** simplicitor/extraction/models.py for Candidate, SavedReview, and ApprovedCandidate.

**Interfaces:** write_candidate(result: ExtractionResult, columns, path: Path) -> Candidate; read_saved_review(candidate: Candidate) -> SavedReview. Candidate carries path/hash, source fingerprints, request/schema identity, ordered record IDs, and issue summary. SavedReview exposes actual saved cell values/types plus Evidence mappings. approve_candidate(candidate: Candidate, review: SavedReview, acknowledge_issues: bool) -> ApprovedCandidate binds the saved review/hash; publish_candidate(approval: ApprovedCandidate, destination: Path) -> Path accepts only that bound approval. invalidate_candidate and discard_job own lifecycle cleanup.

- [ ] Add failing saved-file round-trip tests for leading-zero IDs, text NaN/inf/1_000, literal =1+1 and =HYPERLINK(...) strings in both sheets, finite typed numbers/dates, flagged blanks, proposed values retained in Evidence, coverage entries, and cell-to-evidence selection mapping. Test invalid controls, excessive cell text, and numbers exceeding safe Excel precision as visible issues/errors rather than silent conversion or clipping.
- [ ] Implement the PRD workbook layout in a dedicated writer. Assign strings and force data_type to s, then verify after reload that they remain strings and have no formulas/hyperlinks. Date/number display formats follow the confirmed schema. Never route extraction through the existing Excel generator/coercion method.
- [ ] Create candidates only in owned private job directories. Verify the saved workbook and hash before returning Candidate. Data row order and Candidate's record roster bind the saved Evidence mapping; read review from the saved file, not a reconstructed in-memory sheet.
- [ ] Test changed candidate/source/schema hashes, same-named inputs, existing destination, a destination created during save, copy/rename failure, and cancellation before publication. Assert original sources and existing outputs are unchanged and no partial final output is published.
- [ ] Implement publication with an exclusive temporary file in the destination directory, byte/hash verification, then a Windows no-replacement rename. Do not use replacement semantics for final output. Emit success only after the final file exists and matches the reviewed hash.
- [ ] Test owned-directory cleanup, open-handle failure, and reparse-point escape refusal. Orphans are never auto-published. **Proof:** saved Data/Evidence matches validation, approval binds exact bytes, and failure cannot overwrite or silently publish.

**Verify:** python -m pytest tests/extraction/test_xlsx_writer.py tests/extraction/test_jobs.py -q. Required result: all round-trip, evidence, approval, and failure checks pass; source/destination sentinel hashes are unchanged on rejected publication.

### Task 5: Add the Create workspace and grid review

**Create:** simplicitor/app/widgets/create_workspace.py, simplicitor/app/widgets/extraction_panel.py; simplicitor/app/workers/extraction_worker.py; tests/test_extraction_panel.py, tests/test_extraction_worker.py. **Modify:** simplicitor/app/main_window.py and affected widget/teardown tests. Reuse CreatePanel, StatusBanner, styles, and existing signals.

**Interfaces:** CreateWorkspace hosts the existing CreatePanel and ExtractionPanel. ExtractionPanel emits inspect_requested, extract_requested, cancel_requested, and approve_requested with frozen job settings. ExtractionWorker emits started, progress, inspection_ready, candidate_ready, failed, and cancelled. It wraps core functions and never manipulates widgets. Review selection uses SavedReview's cell/Evidence mapping.

- [ ] Write Qt tests for the PRD default shell, absence of visible Edit, retained prompt/template routing, source-file filtering, same-name inputs, column confirmation/types, file-mode default, and table-header mapping. Reject unconfirmed schemas before starting extraction.
- [ ] Implement the local Create subviews. Use a multi-file picker/drop handler that accepts only the release sources; do not reuse legacy FileList's copying/identity behavior. The existing CreatePanel retains its workers, prompts, retry behavior, and output path behavior.
- [ ] Write worker/UI tests with a fake pipeline: duplicate submission, model disconnect, a late completion after cancellation, unreadable page list, flagged-cell selection showing saved evidence, and acknowledgement before partial export. Freeze sources/schema while busy and retain setup after failure.
- [ ] Implement the worker and saved-grid review using existing QObject/QThread patterns. Cancel cooperatively, show the pending request state honestly, and ignore stale worker results. A revised setup invalidates approval. Do not add PDF rendering, COM, or in-grid document editing.
- [ ] Test destination collisions and write failure keep the review available without a success banner. Test normal save/discard/close releases owned job files and crash leftovers offer removal without automatic publication.
- [ ] Run affected widget/worker/template/generation tests with isolated user folders. Perform a native UI walkthrough using synthetic files and the passing model. **Proof:** a nontechnical user can confirm columns, inspect flags/quotes, and save the exact reviewed workbook while existing creation still works.

**Verify:** python -m pytest tests/test_extraction_panel.py tests/test_extraction_worker.py tests/test_main_window_template.py tests/test_template_worker.py tests/test_generate_worker.py tests/test_main_window_teardown.py -q. Required result: focused Qt/regression checks pass, followed by the recorded native walkthrough.

### Task 6: Package in parallel, qualify after integration

**Modify:** build.py, build.bat, .github/workflows/build.yml, requirements-build.txt only as needed for the tested build version, tests/test_build_script.py, and docs/code-signing.md for procedural findings. **Reference:** [packaging procedure](../../code-signing.md) and [PRD packaging contract](../../../PRD.md#packaging).

**Interfaces:** Keep the application entry point. Build the same standalone payload for the installer and ZIP, including current resources plus extraction modules. No Office/recognition worker or runtime is bundled.

- [ ] Prepare build tests and the standalone build of existing functionality while model work runs. Verify data resources, declared document libraries, icons, prompts, and templates from outside the source checkout.
- [ ] Evaluate Nuitka's built-in NSIS installer support with a pinned tested build version before adding a custom script. Test current-user installation, shortcuts, uninstall, and preservation of user data. No paid signing or Store step is introduced.
- [ ] After Task 5, rebuild and test the actual feature on clean Windows with local Ollama/model and no developer Python or Microsoft Office. Record missing-prerequisite behavior, upgrade/uninstall, and default security results.
- [ ] Verify installer and ZIP contain the same payload/resources and publishable artifact hashes. Diagnose the reported Windows block without disabling protection. **Proof:** users can install, launch, extract/review/save, and uninstall without losing their documents. Any actual launch block remains a release failure requiring a decision.

**Verify:** python -m pytest tests/test_build_script.py -q, then python build.py using the tested build environment. Required result: tests/build pass, both artifacts share a verified payload inventory, and the clean-machine checklist is complete. A successful command is not a substitute for the manual launch/security checks.

### Task 7: Qualify the release and close the plan

**Tests:** new extraction suites, affected existing regressions, tests/test_gen_repo_map.py, the actual-file evaluation harness, and clean-machine/manual UI records. **Documentation:** docs/PROJECT_STATUS.md holds the final current state; evaluation reports hold measurements; PRD.md owns approved targets.

- [ ] Run the full suite with all user folders redirected into a fresh test home. Do not interpret old legacy reconstruction tests as preservation guarantees.
- [ ] Run the final selected model/profile on the fixed actual-file corpus. Verify both quality gates, denominator/flag counts, coverage, privacy diagnostics, and the approved timing target. Do not cherry-pick successful responses.
- [ ] Add an explicit long-job test at the approved aggregate limit and a just-over-limit rejection, without real client data. Confirm no omitted rows or silent content loss across section boundaries.
- [ ] Complete the clean-machine and nontechnical-user walkthroughs, including field evidence, unreadable pages, partial output, cancellations, collisions, and unchanged source hashes. Record observed usability/latency rather than inventing a pass target after seeing the result.
- [ ] Regenerate the repository map, update current status/open decisions, and verify dependency/license notices for the packaged libraries. Leave Alex's license decision open until resolved.
- [ ] **Release decision:** do not call the product ready while a model gate, extraction coverage/type test, default-security launch test, or business-use license decision remains unresolved. Commit/push/tag/publication occur only within their explicit authorizations.

**Verify:** python -m pytest -q with all test homes isolated and a fresh base directory; run the final actual-file CLI evaluation and the packaging/manual records above. Required result: no required test, model, coverage, timing, or installation gate is unresolved before a release decision.

## Plan self-review

The work covers the revised scope, both record modes, anchored untruncated readers, mandatory grounded/schema-constrained fields, typed Data/Evidence output, Qt saved-grid review, the separate safety patch, and parallel packaging. Later OOXML editing, reporting operations, and recognition are linked requirements with no execution tasks here. Task 1's canonical model check and Task 3's actual-file gate resolve the dependency between evaluating models first and building production readers later. Shared interfaces are defined before consumers; no production code, model benchmark, or new dependency is part of plan authoring.
