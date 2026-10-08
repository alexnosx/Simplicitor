# Simplicitor agent instructions

Keep this file and the root `AGENTS.md` byte-identical when updating shared project guidance. Both contain the same policy; neither is a second requirements source.

## Project overview

Simplicitor is a free Windows desktop application using local Ollama for Office document work. The agreed workflows are creation from a prompt, creation from a prompt and read-only source files, and selective editing of approved parts of an existing document. Keep the two UI modes, Create new and Edit document. All workflows must validate and preview a separate candidate, then obtain approval before saving a new output. The audience is nontechnical users with local Ollama and a usable model.

The first product in this direction requires locally installed Microsoft Word, Excel, and PowerPoint desktop applications as well as Ollama and a usable local model. Alex confirmed the Office prerequisite on 2026-10-08. The Office integration and preview architecture remain proposals until reviewed and tested.

Current v1.2 source has Create and Edit panels, prompt-only Office generators, and a manifest-driven PowerPoint template engine. Source-based creation is not implemented. Legacy editing reconstructs files from extracted text and does not implement the preservation, preview, or approval contract. The current build is an unsigned Nuitka onefile executable. Standalone builds, an NSIS installer, and a portable ZIP are approved requirements, not implemented capabilities. Do not claim that double-click launch or Windows trust is verified.

Read these before planning changes:

- `PRD.md`: active product requirements and unresolved decisions.
- `docs/superpowers/specs/2026-10-08-document-architecture-design.md`: architecture proposal for review, including source-based creation; not evidence of implementation.
- `docs/PROJECT_STATUS.md`: current implementation, verification, blockers, and next step.
- `docs/code-signing.md`: approved zero-cost direct-download packaging route and trust limits.
- `REPO_MAP.md`: current structure and module responsibilities.

`docs/archive/PRD_v1.2.md`, `docs/Simplicitor_PRD_v1.2.docx`, `docs/Simplicitor_Implementation_Guide.md`, and `BUILD_STORY.md` are historical references. Their v1 scope and phase order do not override the active PRD or current user decisions.

## Ways of working

- Complete the authorized task and its verification. Keep a short plan for substantial tasks and do not chain into unrelated work.
- Make routine implementation decisions independently using the existing patterns and session decisions. Ask one focused question when an unresolved ambiguity materially changes scope, feasibility, risk, or outcome.
- Preserve existing user changes. Keep changes small and reviewable; avoid unrequested refactors and speculative features.
- Never commit, push, amend, switch branches, rewrite history, tag a release, or publish unless Alex explicitly authorizes that action. Approval for one action does not authorize another.
- Do not add a new third-party dependency without specific user authorization. Existing session authorization remains valid; do not repeatedly ask for an agreed dependency.
- Scope is governed by the active PRD and direct user decisions. Historical exclusions are not grounds to reject the approved installer or selective-editing work.
- Use project files for decisions, resource details, verification, and blockers. Update `docs/PROJECT_STATUS.md` for work spanning sessions.
- Closeout reports state what changed, checks and counts when run, remaining limitations, and whether changes were committed. Give the actual baseline or commit hash; say "not committed" and "tests not run" when applicable.

## Requirements and behavior evidence

For intended scope, direct user instructions and approved session decisions take precedence, followed by `PRD.md`, then the relevant design/reference notes. When an implementation design is needed, resolve the open decisions rather than inventing them.

For actual behavior, use runtime reproductions, inspected code, and relevant tests. Runtime failures remain defects even when the existing suite passes. Code describes implementation; it does not redefine the user's requirements. Distinguish requirements, implemented behavior, locally checked behavior, integration-tested behavior, and deployed releases.

Engine notes are design references where the PRD is silent, not a substitute for current code or runtime evidence. Historical AI summaries are leads to verify, not proof. Cite file and line for code behavior, and label unverified claims.

## Verification

- Define the observable acceptance check before implementation and run it before claiming success.
- Test realistic failure cases and preservation behavior. Existing tests that only produce a valid file do not establish selective-edit safety.
- Check the resulting external or packaged state when access permits. Passing source tests does not prove a clean Windows install or Office fidelity.
- Report failures, skipped checks, and environmental limitations plainly. Never disable a test or linter to make a check pass.
- For documentation-only changes, check consistency, links, mirrored instructions, and generated references. Do not run unrelated application tests merely to report a larger count.
- Keep test files and profiles in temporary or workspace directories; do not write into real user document folders. Use synthetic or suitably sanitized documents.

## Tech stack

- UI: PySide6.
- LLM backend: Ollama HTTP API at `http://localhost:11434`.
- Documents: python-docx, openpyxl, python-pptx.
- Template engine: PyYAML and pydantic v2.
- PDF input: pdfplumber extraction; pypdf remains a declared dependency. No PDF write-back.
- Current packaging: Nuitka onefile. Planned packaging: standalone application plus free NSIS installer and portable ZIP.
- Language: Python 3.11+ in repository requirements. Verify actual dependency and build compatibility.
- Target: Windows desktop. Record supported versions and actual release tests; do not infer clean-machine compatibility from the development environment.

No Hermes integration, provider replacement, model download manager, or fixed Qwen deployment has been selected. Evaluate model/runtime combinations using representative document tasks instead of assuming parameter count proves quality.

## Project structure

`REPO_MAP.md` contains a generated directory tree and per-file API map. Edit only its MANUAL region by hand. After adding, moving, or removing files or changing top-level Python signatures, regenerate with `python scripts/gen_repo_map.py`. Its generated region must match the repository.

Before working on the PowerPoint engine, explicitly read `simplicitor/templates_engine/CLAUDE.md` and `simplicitor/templates_engine/NOTES.md`. Do not assume another harness automatically loads a Claude-specific file.

## Coding conventions

- Type hints on function signatures and docstrings on public methods.
- Pass dependencies explicitly and reuse existing patterns. Write the minimum maintainable code for the requirement.
- Use QObject workers moved to QThreads, signals and slots, and no UI calls from worker threads.
- Handle external-call, parsing, and file-I/O failures at the appropriate boundary. Emit actionable user messages and sanitized diagnostic metadata.
- Keep prompts, file content, model output, personal identifiers, and sensitive client details out of logs. Treat paths, filenames, exception text, and server error bodies as potentially sensitive.
- Privacy policy is a requirement, not a verified current guarantee. The existing parser and HTTP error paths can log model/server values; see project status before making privacy claims.
- Use `app/config/defaults.py` for shared constants, timeouts, colors, and limits.
- Standard-library imports first, third-party next, local imports last. Use absolute imports, snake_case for functions/variables, PascalCase for classes, and UPPER_SNAKE for constants.
- Match existing style and keep Python lines within the existing 100-character convention where practical.

## UI design

Keep the current Segoe UI, light theme, restrained borders, and dismissible status banners unless a task authorizes a change. `app/config/defaults.py` is authoritative for colors, font sizes, and border radius; do not maintain competing copied values.

Users choose documents, targets, instructions, and approval. Keep model and implementation details out of the main flow unless they explain a required user action. Show progress for long operations, disable the triggering action during processing, and retain instructions after a failure.

Target selection, saved-candidate preview, and approval are required future UI behavior. They are not present in the legacy Edit panel.

## Current Ollama integration

- Connectivity/model discovery: `GET /api/tags`, `GET /api/ps`, and `POST /api/show`.
- The polling QTimer runs continuously at `OLLAMA_POLL_INTERVAL_MS`, including while connected. Discovery calls use `OLLAMA_POLL_TIMEOUT_S`.
- Freeform generation and legacy manipulation call `/api/generate`. Their workers omit a format constraint; freeform prompts request JSON, while manipulation requests modified text.
- Templates call `/v1/chat/completions` and explicitly use `json_mode=False`. The client can support JSON mode, but current worker paths do not use it by default.
- Freeform generation retries once with a simplified user prompt after `FileGenerationError`; that exception can include write failures, not just parse failures.
- Template generation validates content and runs one error-informed repair attempt. Legacy manipulation has no automatic retry.
- Timeouts and token limits live in `app/config/defaults.py`. Verify the relevant caller and catch `OllamaTimeoutError` before `OllamaConnectionError` when messages differ.
- A localhost URL does not alone prove that Ollama is using local weights. Confirm the model and processing configuration for privacy acceptance.

## Historical model observations

Earlier gemma4-class tests recorded low-end-of-range bias, few-shot anchoring of slide count, degeneration on identical adjacent examples, and problems with grammar-constrained JSON mode. These explain the current prompts and JSON-mode opt-outs. They are observations about tested configurations, not guarantees for other models.

When changing slide prompts, check both `prompts/system_pptx.txt` and `templates_engine/prompt_builder.py`. Keep length guidance tied to user intent and evaluate it on the selected model/runtime. Do not assume that a stronger model fixes document preservation or file-safety defects.

## Current generation contracts

The model supplies content and basic structure. Python owns document formatting and layout. Preserve these existing generation contracts unless a task explicitly changes them:

**Word generation** - LLM returns:
```json
{
  "title": "string",
  "sections": [
    {
      "heading": "string",
      "content": "string (paragraphs separated by \\n\\n)",
      "type": "text|table|list"
    }
  ]
}
```

**Excel generation** - LLM returns:
```json
{
  "sheet_name": "string",
  "headers": ["string"],
  "rows": [["cell_value"]],
  "formulas": [{"cell": "B10", "formula": "=SUM(B2:B9)"}]
}
```

**PowerPoint generation** - LLM returns:
```json
{
  "title": "string",
  "slides": [
    {
      "title": "string",
      "bullets": ["string"],
      "type": "title|content|section"
    }
  ]
}
```

Templates use the fields declared by their manifest, validated before rendering. A generation-schema change requires corresponding parser, renderer, prompt, and regression checks.

## Selective editing contract

Follow `PRD.md` for the approved workflow: confirm exact targets, propose replacements, patch a separate candidate, validate and preview that saved candidate, obtain approval for its version, and save a new output.

The first slice concerns selected DOCX/PPTX text and literal XLSX values. Preserve identifiers and unselected content, formulas, styles, relationships, and assets within a defined support envelope. Reject ambiguous, stale, or unsupported targets. Do not implement selective edits by reconstructing the whole document from plain text. Define preview, feature support, versioning, and cancellation decisions before building the subsystem.

The old extracted-text/modified-text Edit contract and accepted v1 DOCX formatting loss are superseded requirements, but still describe current legacy behavior. Do not present their removal as already implemented.

## Creation from source files

Follow PRD.md for both prompt-only creation and creation using optional local source files. Keep attached sources read-only and separate from any editing target. The required cross-format example is an XLSX accounting workbook used to create a DOCX report. Inspect and confirm relevant scope, extract typed facts locally, compute supported measures deterministically, and retain source and calculation references for review. The model writes and organizes explanations; do not rely on model arithmetic or invent missing figures. Do not silently truncate relevant source records or claim partial coverage is complete. Source-based generation uses the same saved-candidate preview, approval, and new-output publication contract. It does not authorize persistent indexing, RAG, or editing the sources.

The reverse case is also required: large DOCX or PDF sources used to create an XLSX. Confirm columns, field types, and record boundaries; process the complete selected scope in bounded sections; preserve source references and field associations; and expose missing or uncertain values. Write extracted text as literal Excel values. PDF sources remain read-only. Scanned or mixed PDFs require a local OCR/vision path with a tested support envelope; the current PDF dependencies and legacy text extractor do not provide this. Unsupported or unreadable pages/regions must be reported rather than silently skipped. No OCR dependency or engine has been selected or installed.

## Backups and file identity

Current backups use `{stem}_backup{suffix}` in the configured directory and reuse any existing destination. Uploads also use the basename. Different source files can collide, so "one backup per distinct file" is not a verified current guarantee.

Preserve existing backups. For the new workflow, keep source files unchanged, distinguish same-named sources, stage separate candidates, and define version/retention rules. Do not silently replace another source, draft, output, or backup.

## Packaging and release scope

Follow `docs/code-signing.md`: zero-cost direct download, standalone Nuitka payload, NSIS installer as the primary artifact, and portable ZIP secondary. Evaluate Nuitka's built-in installer support and verify a suitable build version. Paid certificates, paid signing services, and Microsoft Store publication are outside the agreed route.

Do not claim that an unsigned installer resolves SmartScreen or antivirus blocks. Obtain the exact warning/detection and test artifacts on clean Windows environments with default protection. Keep release publishing separately authorized.

## Scope boundaries and assumptions

Creation and the PowerPoint template engine remain supported. General chat, RAG, persistent agent memory, model management, cloud processing, plugins, batch automation, automatic updates, PDF write-back, and Mac/Linux support are outside the first approved scope.

Treat the original six build phases and template Phases A through M as historical work. Start from current code and active requirements rather than restarting them.

Record material assumptions and unresolved choices in the relevant design or project status. Ask only when the answer affects the outcome and available context cannot resolve it; routine choices do not require a TODO comment or repeated permission. No license change is authorized by the packaging or documentation decisions.
