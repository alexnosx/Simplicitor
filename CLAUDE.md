# Simplicitor

## Project Overview

Simplicitor is a native Windows desktop application that connects to a locally running Ollama instance and lets non-technical users generate and manipulate Office documents (Word, Excel, PowerPoint) through natural language prompts. Two-panel UI: Create (generate new files) and Edit (manipulate existing files). No cloud, no browser, no terminal. Double-click .exe, it works.

v1.2 adds a PPTX template engine: instead of building slides from scratch, it fills the layout placeholders of a real PowerPoint design (a built-in template or one the user uploads), so the output keeps that deck's branding. Built across Phases A through M; functional, with ongoing prompt-engineering iteration as new models surface new biases. See simplicitor/templates_engine/CLAUDE.md for the engine reference; the primary design-intent notes for the engine are in `simplicitor/templates_engine/NOTES.md`.

Full requirements: `docs/Simplicitor_PRD_v1.2.docx`
Build phases: `docs/Simplicitor_Implementation_Guide.md`

Source-of-truth ordering is defined in the Source of Truth section. When anything is ambiguous, ask rather than guess.

## Ways of Working

How we collaborate on this repo. These govern every session by default.

- One task per session, one atomic reviewable commit per task. Stop after the task. Never chain into the next task without an explicit "Proceed" from Alex.
- Every closeout report states the commit hash and the test count (passed of total).
- Decisions are Alex's. When anything is ambiguous or a scope or approach fork appears, STOP and ask with concrete options and a recommendation. Do not pick silently. When Alex pushes back, treat it as signal and re-examine rather than defend.
- Never git commit, push, amend, switch branches, or open a PR unless Alex explicitly asks, per action. Approval for one action never implies another.
- Stay in scope. Do only what was asked. No "while I am here" edits or unrequested refactors. Anything not in the PRD is flagged as scope creep and confirmed before building (see What NOT to Build).
- No new third-party dependency without Alex's explicit, per-library approval. Prefer the standard library or a minimal hand-rolled solution, and propose the library with a no-library alternative rather than adding it.

## Source of Truth

When sources conflict, the higher rung wins, always.

1. Code and tests. The running code and its passing tests are ground truth. Read the code before asserting behavior and cite file and line. Never claim behavior you have not read.
2. Runtime behavior. Observed output of the running app over described behavior.
3. The PRD (docs/Simplicitor_PRD_v1.2.docx). Governs product scope and requirements. A lead to verify against the code, not an override of the code. If the PRD and the code disagree on what the code does, the code wins and the drift is flagged.
4. NOTES.md and this CLAUDE.md. Design intent and repo orientation. Leads to verify, may be stale. NOTES.md is authoritative for template-engine design intent only where the PRD is silent. It never overrides the PRD on scope or the code on behavior.
5. AI output, this agent's or an earlier one's. Lowest. Re-derive from a higher rung before trusting it.

Make no claim you cannot trace to rung 1 or rung 2. If you cannot verify, say "unverified" or "I do not know." Never fabricate.

## Verification

- Evidence over assertion. Show the command or test output. Never claim success without running it.
- No "probably" or "should work." Verify it, or label it explicitly as unverified.
- Report failures plainly: failed tests, skipped steps, dead ends.
- Never disable or skip a test or linter to make something pass. Fix the root cause.

## Tech Stack

- **UI:** PySide6
- **LLM Backend:** Ollama REST API (localhost:11434)
- **Documents:** python-docx, openpyxl, python-pptx
- **Template engine:** PyYAML (manifests), pydantic v2 (manifest schema + content validation)
- **PDF Reading:** pypdf, pdfplumber (read-only, no write-back)
- **Packaging:** Nuitka
- **Language:** Python 3.11+
- **Target OS:** Windows 10/11 only

## Project Structure

The directory tree and per-file API map are generated into REPO_MAP.md by scripts/gen_repo_map.py. Read REPO_MAP.md before exploring the codebase. After structural changes (files added, moved, or removed; top-level functions or classes changed), regenerate it: `python scripts/gen_repo_map.py`. Edit only its MANUAL region by hand; the rest is overwritten.

## Coding Conventions

- Type hints on all function signatures.
- Docstrings on all public methods.
- No global state. Pass dependencies explicitly.
- PySide6 threading: QThread with worker objects (moveToThread pattern), not subclassed QThread. Signals/slots only. Never touch UI from a worker thread.
- Every external call (Ollama API, file I/O, LLM parsing) wrapped in try/except. Errors produce user-friendly messages and log technical details. Never crash.
- Logging: Python logging module, daily rotation, never log file content or user prompts.
- Constants: all magic numbers, default paths, color hex values, timeouts go in `app/config/defaults.py`.
- Imports: standard library first, third-party second, local third. Absolute imports only.
- Line length: 100 characters max.
- Naming: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants.

## UI Design Rules

- Colors (light theme only, dark mode is v2):
  - Background: #FAFAFA
  - Panel backgrounds: #F5F5F5
  - Primary accent (buttons, active): #2563EB
  - Body text: #1E1E1E
  - Success: #16A34A
  - Error: #DC2626
  - Disabled: #9CA3AF
  - Borders: #E5E7EB
  - Info banner background: #EFF6FF
- Font: Segoe UI. Regular for body, semibold for headings/buttons.
- No gradients, no deep shadows, max 4px border radius.
- Dismissible banners for errors and info (colored strip + text + X button).
- All long-running operations show a spinner and disable the triggering button.

## Ollama Integration

- Base URL: `http://localhost:11434`
- Model list: `GET /api/tags`
- Running model: `GET /api/ps`
- Model metadata: `POST /api/show` with `{"name": "model_name"}`
- Generate: `POST /api/generate` or `POST /api/chat`
- Connection polling: every 5 seconds when disconnected
- Timeout: 60s default; 120s on manipulation calls (file content payload); 180s on templated generation (heavier prompts on slow local models)
- Use Ollama's `format` / OpenAI-compat `response_format` for structured JSON output by default. The templated path opts out (`json_mode=False`) because grammar-constrained decoding degenerated gemma4-class models in testing; the prompt's "Return ONLY valid JSON" instruction plus the parse-and-clean path is sufficient there.
- Connection drop mid-operation: abort, show error, preserve prompt in text area

## Known small-model behaviors

Empirical lessons from debugging Simplicitor against gemma4-class local models. Apply when changing prompts in `prompts/` or `templates_engine/prompt_builder.py`.

- **Low-end-of-range bias.** Small local models pick the low end of stated ranges. "7 to 12 slides" lands at 7. Pair every range with explicit "target the upper end" or with a substantive default that biases toward fuller output.
- **Few-shot examples anchor output structure.** A one-shot demonstrating N slides causes the model to produce N. Make one-shot examples representative of natural variety, not of minimum viable output.
- **Identical adjacent items dead-end small models.** When a one-shot contains two byte-for-byte identical adjacent slides, gemma4 treats it as "repeat verbatim" and degenerates into whitespace stalls. Vary synthetic content per slide type so duplicates are not identical.
- **Input length is not a proxy for desired output length.** A short prompt about a deep topic still wants a substantive deck. Length guidance should be intent-based (keywords like "brief" or "comprehensive", explicit slide counts) rather than tied to character-count thresholds.
- **Non-templated and templated paths share failure modes.** When one path needs a prompt fix, check whether the other carries the same gap. The system prompt in `prompts/system_pptx.txt` and the `_build_system_message` in `prompt_builder.py` should carry the same conceptual LENGTH guidance.

## LLM Contract Design (Critical)

The LLM produces content and basic structure. Python code handles all formatting, colors, and layout. DO NOT ask the LLM to produce complex styling JSON. Keep it simple.

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

**File manipulation** - LLM receives extracted text, returns modified text. Python handles file reading/writing.

If LLM response fails to parse, retry ONCE with simplified prompt, then fail gracefully.

## Template Engine (PPTX)

The PPTX template engine has its own engine-scoped reference in
simplicitor/templates_engine/CLAUDE.md, which auto-loads when working in that directory.
Design intent and deferred follow-ups are in simplicitor/templates_engine/NOTES.md.
Read both before changing the engine.

## Backup Rules

- One backup per file, created on first manipulation only.
- Stored in configured backup directory.
- Name: `originalname_backup.extension`
- Never overwrite existing backup. Never delete backups.
- Show backup path in success message.

## Build Phases

Read `docs/Simplicitor_Implementation_Guide.md` for detailed tasks. Build in order:

1. **Phase 1: Skeleton** - Main window, panels, settings, config
2. **Phase 2: Ollama** - Connection, status, model selector, polling
3. **Phase 3: Generate** - File generation (Word, Excel, PowerPoint)
4. **Phase 4: Edit** - Upload, manipulation, backup
5. **Phase 5: Polish** - Error UX, banners, edge cases
6. **Phase 6: Package** - Nuitka compilation

Complete each phase fully before the next. Each phase must produce a runnable app.

The PPTX template engine has a separate phase track (A through M) covering its design, build, and audit, documented in `simplicitor/templates_engine/NOTES.md`. That track is functionally complete; ongoing work is incremental prompt engineering, not new phases.

## What NOT to Build

No chat history, no RAG, no model management, no plugins, no cloud, no dark mode, no PDF write-back, no auto-update, no Mac/Linux. If I ask for something not in the PRD, flag it as scope creep and confirm before building.

## Assumptions

When you must assume something to keep moving, add a `# TODO: ASSUMPTION - [explanation]` comment. Prefer the simpler implementation. This is a v1 product.
