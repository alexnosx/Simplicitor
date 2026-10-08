# Changelog

## v1.2.1 safety patch, 2026-10-08

- Disable legacy Edit and reject direct save/worker calls before reading, backing up, inferring, or writing. Preserve existing Create and PowerPoint template routes.
- Publish the existing unsigned executable as version 1.2.1.0 through the tag workflow. Latest status, public asset version, and SHA-256 are verified in docs/releases/v1.2.1.json. Local startup was smoke checked; Alex waived the clean-machine walkthrough for this patch.

## Unreleased extraction development

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
