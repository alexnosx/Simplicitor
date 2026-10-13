# Changelog

## v2.3.0, 2026-10-13

Published as [v2.3.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.3.0) and verified as Latest with MSI, portable ZIP, checksums and the tagged release notes as its body. Verification: [docs/releases/v2.3.0.json](docs/releases/v2.3.0.json).

- Add selective Word editing: open a standard .docx, select continuous whole body paragraphs, describe a change, review Before/After with light green highlights, and save one change as a new file. Preserve all bytes outside the selection and all other package parts. The original is never overwritten.
- Show paragraphs, headings, bold/italic, lists, tables and picture placeholders in a virtualized plain-text reading view. Keep tables, headers, footers and paragraphs with unsupported constructs read-only with reasons. Enforce the 50 MiB/300-page-equivalent input, 6,000-character selection and 2,000-character description limits; refuse protected, signed and unsupported documents.
- Keep the selected-model, discard, cancellation and stale-result gates. Ask to discard only after a replacement file is picked. Wait for an accepted save on close, show that wait on Edit, and keep a failed save visible on Save with the window open. Match the approved mockup wording and show the original folder.
- Keep the independent editing engine's byte-map/splice verification, formatting and bookmark rules, worker-side destination fingerprinting, staged read-back and commit-point checks. Track Changes documents are allowed, with a notice that new revision marks are not written. Legacy manipulation stays disabled.
- Pass the one-shot model gate: both Q4_K_M candidates scored 11/12 with zero verification failures; [report](docs/evaluation/2.3.0-edit-model-check.json). All six patched samples opened read-only in Word 16.0 build 16.0.20326; [Word check](docs/builds/2.3.0-word-check.json).
- Correct the Edit test fixture's queued first discovery poll and collect cyclic garbage only on the main thread between source tests. The 2.3.0 version-change isolated suite passed 1,290 tests. Update requirements, architecture/UI specs, the implemented design status, README, map and release notes.
- Set product/MSI version 2.3.0, executable 2.3.0.0 and the derived hosted upgrade probe 2.3.1. Keep the existing MSI/portable route, extraction and generation behavior, dependencies and LICENSE. D1 qualified the prepared source on GitHub; D2 rebuilt, qualified and published Alex's approved tagged commit.

## v2.2.0, 2026-10-13

Published as [v2.2.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.2.0) and verified as Latest with MSI, portable ZIP, checksums and the tagged release notes as its body. Verification: [docs/releases/v2.2.0.json](docs/releases/v2.2.0.json).

- Offer two explicit Create options: Write a new document and Pull information from documents into Excel. Retain each option's inputs; writing never sends attached sources and pulling always produces Excel. Leaving Pull clears derived columns/review and discards its temporary job. Busy and late-result gates remain.
- Use numbered cards, 11 pt body text, darker borders, blue dropdown/focus and template-button states, and a chosen template label with Clear. Show per-file reading states and progress on file rows and main actions; keep four column rows visible while extracting with a light disabled selection.
- Offer built-in PowerPoint templates only after the B3 drop. Remove the app's deck upload, preparation/rejection UI and B1-B3 capture code; retain the generation engine and developer CLI tools.
- Name detected Word reading problems, including unread tracked moves. Distinguish tracked formatting/row changes that need review while retaining their text. Present incomplete-reading problems under the general check-before-use heading and preserve acknowledgement gates.
- Clear finished progress messages, use an extraction-specific request hint and point model selection to Settings. Show one shared version in the window title, top bar, Settings and build outputs.
- Set the product/MSI version to 2.2.0 and executable version to 2.2.0.0; the hosted upgrade probe is 2.2.1. Keep the MSI, portable ZIP, checksum inventory and license notices. Update scope/specs/status, the map and release notes; Word editing in 2.3.0 comes before table-row extraction.
- Extraction algorithms, evaluation fixtures/labels/settings, dependencies and LICENSE remain unchanged. E1 qualified its source commit on GitHub; E2 rebuilt, qualified and published the approved tagged commit.

## v2.1.0, 2026-10-12

Published as [v2.1.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.1.0) and verified as Latest with MSI, portable ZIP, checksums and the release notes as its body. Verification: [docs/releases/v2.1.0.json](docs/releases/v2.1.0.json).

- Add PDF output from a prompt through the existing Word response structure and Qt writer, with validation before replacing the destination. No Office or external converter is needed.
- Replace Create tabs with one screen: Describe, optional source files, Choose columns, Review and save, and Saved. Keep prompt generation and PowerPoint templates. Edit document explains deferred selective editing; legacy Edit stays disabled.
- Present source anchors, reading problems and evidence in plain language. Require acknowledgement for highlighted values, reading problems, or both. Keep saved Excel number formats and the sectioned-source review policy.
- Replace setup.exe with the fixed-folder per-user `Simplicitor-2.1.0.msi`, retaining the matching portable ZIP, checksum inventory and license notices. Refuse an existing 2.0.0 NSIS installation until it is uninstalled. Qualify install, repair, major upgrade and settings-preserving uninstall only on the hosted Windows runner.
- Use executable version 2.1.0.0 and MSI version 2.1.0. Run source tests on each push; full hosted builds only at approved milestones and tags. Add a 15-minute tests-job limit, verbose test names and stack diagnostics.
- Remove prompt-derived filenames, output paths, slide content and exception text from the specified generation logs. Keep template-dialog ownership until thread completion and avoid blocking GUI teardown joins.
- Scope the central background so labels inside cards stay white; render source filenames once with their accessible names retained.
- Update the PRD, architecture/UI specs, source-launch guide, repository map and release notes. Extraction settings, fixtures, labels, gates and LICENSE are unchanged.

## v1.2.1 safety patch, 2026-10-08

- Disable legacy Edit and reject direct save/worker calls before reading, backing up, inferring, or writing. Preserve existing Create and PowerPoint template routes.
- Publish the existing unsigned executable as version 1.2.1.0 through the tag workflow. Latest status, public asset version, and SHA-256 are verified in docs/releases/v1.2.1.json. Local startup was smoke checked; Alex waived the clean-machine walkthrough for this patch.

## v2.0.0, 2026-10-09

Published release: [v2.0.0](https://github.com/alexnosx/Simplicitor/releases/tag/v2.0.0). The implementation entries below preserve their historical checks; final release evidence is in docs/releases/v2.0.0.json.

- License Simplicitor 2.0.0 onward under MIT, copyright (c) 2026 Alexandru Pop. Releases through v1.2.1 remain under PolyForm Noncommercial 1.0.0. Bundle the application LICENSE beside third-party notices and reject missing, empty, or stale copies during packaging.

- Require review of every extracted cell from sectioned sources with sectioned_source, preserving verified values/types/formats. The sectioned evaluation criterion is zero unflagged values; accuracy is reported without gating it. The single full-corpus run passes both path criteria, with sectioned accuracy 33/40 and all 40 cells flagged; see docs/evaluation/2026-10-09-sectioned-review-policy.md.

- Make section requests independent, normalize literal "null" values, and select verified proposals symmetrically while retaining alternatives and conflicts. Apply separate whole-file/sectioned criteria to full-pipeline exit status. The revised saved-output run passes whole-file extraction but still fails sectioned zero-unflagged-wrong; see docs/evaluation/2026-10-09-sectioned-rerun.md.

- Add saved-XLSX full-pipeline evaluation, four large synthetic sources, and 300/301-page checks. Whole-file Qwen accuracy passes; sectioned accuracy fails. Scores are recorded in docs/evaluation/2026-10-08-task6-full-pipeline.md without changing prompts, existing labels, or model settings.
- Bundle runtime dependency notices, full Qt/PySide LGPL/GPL terms, Qt third-party attributions, Python and Nuitka runtime licenses. Validate notice presence/hashes before packaging; bundled libraries retain their original licenses.

- Set Windows product version to 2.0.0.0. Keep Nuitka's stock per-user installer/uninstaller and qualify installation, offscreen startup without Ollama, upgrade, and settings-preserving uninstall only on the GitHub Actions Windows runner. No tag or release.

- Show saved numeric formats in the review grid and omit its Record column, retaining Record in Evidence.
- Prepare standalone packaging with pinned Nuitka 4.2.2 built-in current-user NSIS support, portable ZIP from the same payload, and SHA-256 inventories. Correct compiled resource lookup and use the built-in uninstaller in the dedicated runtime folder. Local packaging evidence is historical; runner qualification is recorded separately in docs/builds/.

- Add the Task 4 Create workspace: source extraction first, editable/confirmed columns, background workers, saved grid/Evidence review, non-blocking selected-model guidance, and native XLSX Save As. Preserve existing prompt/template creation in From prompt; hide legacy Edit.
- Preserve numeric leading-zero proposals with leading_zero flags, save unrepresentable numbers as highlighted literals with excel_precision, and require a case-insensitive .xlsx Save As suffix.
- Add Task 3's typed/literal Data and Evidence writer, saved-file review mapping, owned temporary jobs, acknowledged Save As copying, source-path refusal, and age-based cleanup. Native dialogs and review UI remain Task 4.
- Correct context estimation to 2.5 UTF-8 bytes per token without counting output schema; reject actual prompt usage at the reserved-output boundary. Preserve verified values when later grounding fails, retaining failed alternatives and verified conflicts.
- Accept grounded currency-bearing numbers and normalize blank model values to null. The selected Qwen rerun passes at 277/280 with zero unflagged wrong values; see docs/evaluation/2026-10-08-task1-qwen-currency-null.md.
- Add Task 2 core transport, column suggestions, conservative context-based sections, retained proposals/coverage, and cooperative cancellation.
- Reject partial-token evidence in both quotes and their source context; accept ordinal English dates and read Word headers/footers with dedicated anchors.
- Replace fixture-specific prompt hints with generic rules and plain column definitions. Expand the gate to 28 files/280 fields with eight prose documents.
- Rerun both candidates: Qwen passes the overall gate at 97.14%; Llama fails accuracy at 93.57%. Narrative subgroup limitations and full counts are in docs/evaluation/2026-10-08-task1-rerun.md.
- Add independent anchored DOCX/text-layer PDF readers, verbatim grounding, deterministic type conversion, and a direct-Ollama evaluation CLI.
- Add 20 synthetic English fixtures with independent labels. Both candidate models passed the first gate; measured results are in docs/evaluation/2026-10-08-task1.md.
- Approve whole-file-first production extraction and renumber the plan tasks 0 to 6.

## Unreleased documentation

- Consolidate the revised first-release contract in PRD.md and add one implementation plan.
- Simplify the reviewed plan: file records, English support, parameter-size guidance, verbatim grounding, one actual-file stop gate, column proposals, standard Save As, and an independent safety release.
- Update architecture, UI guidance, document ownership, and CLAUDE's import of AGENTS.md.
- Preserve historical release notes below; current behavior and open decisions live in docs/PROJECT_STATUS.md.

## v1.2 — June 2026

**PowerPoint template engine.** A second PowerPoint generation path: instead of building slides from scratch, the LLM fills the layout placeholders of a real `.pptx` design. The output keeps the template's masters, layouts, and theme.

- **From template... button** in the Create panel (enabled when Ollama is connected and PowerPoint is selected). Opens a modal picker that lists every available template, lets you upload your own, and shows the manifest summary plus the detection report on upload.
- **Two bundled templates:**
  - `business_pitch` — charts 16x9 design with title / agenda / content / closing slide types. The agenda and content slides take real bullet lists.
  - `technical_overview` — title / architecture / bullets layout set for engineering documentation.
- **Configurable Templates folder** in Settings, defaulting to `Documents\Simplicitor\Templates`. Built-in defaults are seeded on first launch and restored if you delete them. Custom uploads land in the same folder and appear in the picker on next open.
- **Upload-your-own.pptx** flow: Simplicitor scores the uploaded deck's layouts, strips sample content, and writes a draft manifest. Decks built from hand-placed text boxes (no real placeholders) are rejected with a clear, user-facing explanation.
- **Generate runs from the main Generate button.** When a template is loaded, the Generate button routes through the template-aware pipeline (generate → validate → one repair attempt → render). The deck is written to the panel's Save-to folder. The status banner and Open file button work the same as the from-scratch path.

**Generation quality improvements (templated and non-templated):**

- **Scale-to-depth length guidance** on both paths. The LLM is told to default to 8-12 slides for typical requests, honor explicit length signals in the prompt ("brief", "comprehensive", "5-slide deck"), and target the upper end of any range. Short prompts about substantive topics still produce substantive decks.
- **Templated path opts out of grammar-constrained JSON mode.** Constrained decoding interacts badly with smaller / reasoning-style local models (gemma4-class), driving them into dead-end token streams. The templated prompt's "Return ONLY valid JSON" instruction plus the existing JSON-clean-and-parse path is sufficient on its own.
- **Validation error content is logged** when the repair attempt fails schema validation, so the next failure of this shape is debuggable from the log without re-instrumenting.
- **Bumped token budget and timeout for the templated path** (8192 max-tokens floor, 180s HTTP timeout) so heavier prompts on slow local models don't silently truncate or wall-time out.

## v1.0 — April 2026

- Generate Word, Excel, and PowerPoint files from natural language prompts
- Upload existing files and apply manipulation prompts, with automatic backup on first edit
- PDF read-only input with output to `.docx` or `.txt`
- Model capability detection: non-blocking info banner for sub-7B models
- Out-of-scope prompt rejection: styling/visual manipulation prompts detected and rejected before any file is touched, with a clear explanation
- Dismissible error banners with human-readable messages; all technical details written to log files only
- Native Windows feel: two-panel UI, custom geometric icon, Segoe UI typography
- Settings: configurable paths for generated files, uploads, backups, and logs
- Single `.exe` via Nuitka — runs on a clean Windows 10/11 machine with no Python or installer required
- No cloud, no telemetry, no network activity beyond localhost Ollama
