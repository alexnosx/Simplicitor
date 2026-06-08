# Simplicitor

## Project Overview

Simplicitor is a native Windows desktop application that connects to a locally running Ollama instance and lets non-technical users generate and manipulate Office documents (Word, Excel, PowerPoint) through natural language prompts. Two-panel UI: Create (generate new files) and Edit (manipulate existing files). No cloud, no browser, no terminal. Double-click .exe, it works.

v1.2 adds a PPTX template engine: instead of building slides from scratch, it fills the layout placeholders of a real PowerPoint design (a built-in template or one the user uploads), so the output keeps that deck's branding. Built across Phases A through M; functional, with ongoing prompt-engineering iteration as new models surface new biases. See the `Template Engine (PPTX)` section below; the authoritative notes are in `simplicitor/templates_engine/NOTES.md`.

Full requirements: `docs/Simplicitor_PRD_v1.2.docx`
Build phases: `docs/Simplicitor_Implementation_Guide.md`

The PRD is the source of truth. If something is ambiguous, ask rather than guess.

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

```
simplicitor/
    main.py
    cli.py
    app/
        __init__.py
        main_window.py
        widgets/
            __init__.py
            create_panel.py
            edit_panel.py
            settings_dialog.py
            status_bar.py
            file_list.py
            drop_zone.py
            template_dialog.py
            hard_stop_dialog.py
        workers/
            __init__.py
            ollama_worker.py
            generate_worker.py
            manipulate_worker.py
            template_worker.py
        services/
            __init__.py
            ollama_client.py
            file_generator.py
            file_manipulator.py
            backup_service.py
        generators/
            __init__.py
            word_generator.py
            excel_generator.py
            pptx_generator.py
        parsers/
            __init__.py
            llm_response_parser.py
        config/
            __init__.py
            settings.py
            defaults.py
        utils/
            __init__.py
            logging_setup.py
            file_utils.py
    templates_engine/
        __init__.py
        manifest.py
        validation.py
        breakdown.py
        render_pptx.py
        prompt_builder.py
        llm.py
        pipeline.py
        config.py
        NOTES.md
        HOWTO_ADD_TEMPLATE.md
        builtin/
            business_pitch/
                template.pptx
                manifest.yaml
            technical_overview/
                template.pptx
                manifest.yaml
    prompts/
        system_word.txt
        system_excel.txt
        system_pptx.txt
        system_manipulate.txt
    tests/
    docs/
        Simplicitor_PRD_v1.2.docx
        Simplicitor_Implementation_Guide.md
    requirements.txt
    README.md
```

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

A second PowerPoint path built across Phases A through M, with full test coverage in `tests/templates_engine/` and a CLI test in `simplicitor/tests/test_cli.py`. The v1 PPTX path generates slides from scratch and Python controls all styling. The template engine instead fills the layout placeholders of a real, professionally designed `.pptx`, so output keeps the template's branding. The user picks a built-in template or uploads a deck; the LLM produces content JSON keyed to named placeholder fields; Python renders it into the template.

**Read before changing the engine:** `simplicitor/templates_engine/NOTES.md` holds the Phase A repo orientation, the error-handling contract every module conforms to, and the list of deferred follow-ups (each marked ACCEPTED, FIXED, CLOSED, or Open). To add a template: `simplicitor/templates_engine/HOWTO_ADD_TEMPLATE.md`.

### What a template is

A folder with exactly two files:
- `template.pptx`: design only, zero slides. Masters, layouts, and theme are kept; every slide is stripped.
- `manifest.yaml`: declares the fillable structure.

Manifest shape: `name`, `type` (`pptx`), `template_file`, `description`, and `slide_types`. Each slide type has a `layout_index` and a list of `fields`. Each field has `name`, `placeholder_idx`, `kind` (`text` | `bullets` | `image`), `required`, and optional `max_chars` (text only) / `max_items` (bullets only). Field names become the JSON keys the LLM fills.

### Two template directories

| Source | Location | Writable |
|--------|----------|----------|
| Built-in | `simplicitor/templates_engine/builtin/<name>/` | No, ships with the app |
| User | `%APPDATA%\Simplicitor\templates\<name>\` (fallback `~/.simplicitor/templates`) | Yes, created on first run |

Override the user root via `simplicitor.toml` under `[templates] user_dir`. Built-ins shipped: `business_pitch` and `technical_overview`. A folder missing either required file is silently skipped. Rebuilding a built-in `.pptx` means re-verifying its indices: `python simplicitor/cli.py inspect` or `scripts/inspect_template.py` both print them.

### Modules (`simplicitor/templates_engine/`)

| Module | Responsibility |
|--------|----------------|
| `manifest.py` | Frozen pydantic schema (`Manifest` / `SlideTypeDef` / `FieldDef`); `load_manifest` (YAML to validated, names the failing field on a bad manifest); `lint_manifest` (non-fatal warnings) |
| `validation.py` | `build_content_model`; `validate_content` (collects every error in one pass, each names the offending field); `format_validation_errors` (feeds the repair loop) |
| `breakdown.py` | `inspect_pptx` (read-only layout/placeholder map), `format_inspection`, `strip_to_template`, `score_layouts` (usable = has a non-title, non-decorative content placeholder), `generate_draft_manifest` (auto-labels idx 0 to title, PICTURE to image, same-type duplicates to `NEEDS_LABEL_<idx>`), `detection_report`, `hard_stop_result` |
| `render_pptx.py` | `render(manifest, content, out_path, template_dir)`: iterates the content's `slides` array, creating each slide from the layout named by its `type` and populating placeholders by idx (text sets `.text`; bullets clear the frame then one paragraph each; image `insert_picture` and capture the returned placeholder). Writes to a temp file then renames, so no partial file is left on failure. |
| `prompt_builder.py` | `build_prompt` (4 messages: JSON-only system schema, one worked example, then request plus optional source); `build_repair_prompt` (distinct parse-error vs validation-error variants) |
| `llm.py` | Facade over `OllamaClient`: `preflight` (Ollama reachable and the model present, with tag-aware name matching) and `generate` (chat completions, temperature 0.3, optional `max_tokens`) |
| `pipeline.py` | `generate_content` (generate, parse, validate, one repair, else fail) and `run` (the same, then render) |
| `config.py` | `get_builtin_root` / `get_user_root`, `list_templates` (merge and tag both roots), `import_template` |

### CLI

Run as `python simplicitor/cli.py <command>` (no installed console script):

| Command | Purpose |
|---------|---------|
| `inspect <file.pptx>` | Print the layout/placeholder map (idx, type, position). Use it to fill indices into a hand-written manifest. |
| `list-templates` | List built-in and user templates, tagged by source |
| `import <file.pptx>` | Import a deck as a user template, or return the hard stop |
| `render --template <name> --spec <json> --out <deck.pptx>` | Render hand-written content JSON, no LLM |
| `generate --template <name> --request <text> [--source <f>] [--model <m>] [--dry-run] [--out <deck.pptx>]` | Full LLM pipeline. `--dry-run` prints the assembled prompt without calling the model; `--out` is required otherwise. |

### Generate pipeline

preflight -> build prompt -> call model -> strip code fences and parse JSON -> validate against the manifest -> on failure run ONE repair attempt with the specific errors fed back -> success renders; an exhausted retry fails with a conventional error and writes no file. A parse failure that looks truncated raises the repair `max_tokens` to the `OLLAMA_REPAIR_MAX_TOKENS` floor (4096 in `app/config/defaults.py`). A `--source` file, when given, is included in the prompt verbatim. There is no summarization or retrieval step (both were descoped).

### Error handling

The engine conforms to Simplicitor's existing conventions (the NOTES.md contract). No new exception taxonomy, no second logger.

- Bad argument or bad structured input: `ValueError` (bad arg) or `ParseError` (bad LLM output).
- Missing file at a known path: `ManipulationError`. Wrong extension or corrupt file: `ValueError`.
- Model faults: `OllamaTimeoutError` (a subclass of `OllamaConnectionError`, so catch it FIRST), `OllamaConnectionError`, `OllamaGenerationError`, each carrying a remediation hint.
- Every module uses `logging.getLogger(__name__)`. Never log file content or prompt text.
- No-partial-file discipline throughout: render writes a temp file then renames; a failed import deletes the half-written folder.

**Degrade vs fail (render).** Data and template-content faults degrade: a warning is logged and collected into a per-slide `issues` list returned with the result. Missing optional field skipped, text over `max_chars` warned, bullets over `max_items` warned, missing image skipped. Genuine faults fail conventionally with no output file: template unopenable, a manifest `layout_index` or `placeholder_idx` absent in the `.pptx`, or an unwritable output path.

**Hard stop.** A deck whose slides are manual text boxes (no layout placeholders) cannot be templated. This is a normal returned result (`status: "hard_stop"` plus a verbatim user-facing message), not an exception. In practice, most real-world decks built by humans use manual text boxes rather than layout placeholders, so this status is common rather than rare. The templated path covers a narrow input shape (decks authored against PowerPoint's layout placeholder system, which is uncommon in the wild). Broader real-world coverage is a v2 concern, not a v1 fault.

### GUI integration

The "From template..." button in the Create panel is enabled only when Ollama is connected and the file type is PowerPoint (the engine is pptx-only). It opens `TemplateDialog`, a modal picker: a `QStackedWidget` over SELECTION -> CONFIRM, with a `HardStopDialog` branch off the upload path. SELECTION lists and uploads templates; CONFIRM shows the manifest summary plus the detection report for uploads, with no prompt box. Clicking CONFIRM's "Next" emits `template_selected(manifest, template_dir, name)` and closes; MainWindow stores the loaded template and relabels the button to "From Template: selected". Re-clicking the button always reopens the picker.

Generation runs from the main Generate button, not the dialog. When a template is loaded and PowerPoint is selected, `_on_generate_requested` routes to a MainWindow-owned `TemplateGenerateWorker` (moveToThread) that runs the full `pipeline.run` (generate + render) off the UI thread and emits `completed(path, issues)` / `failed(msg)`; otherwise the from-scratch path handles all file types. The deck is written to the panel's "Save to" folder and the result surfaces through the existing status banner + Open file button (no JSON preview step). The loaded template clears, and the button reverts, after a successful generate or when the file type leaves PowerPoint; a failed generate keeps it loaded for retry. Every failure surfaces through the existing inline status pattern, never a raw traceback.

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
