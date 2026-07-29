# Template Engine (PPTX): engine-scoped notes

Operational reference for the PPTX template engine. Auto-loads when working in
simplicitor/templates_engine/. The whole-repo rules (Ways of Working, Source of Truth,
Verification, scope) live in the root CLAUDE.md and still govern here. Design intent and
deferred follow-ups live in NOTES.md. Source-of-truth ordering from the root resolves any
conflict between this file, NOTES.md, and the code.

## Template Engine (PPTX)

A second PowerPoint path built across Phases A through M, with full test coverage in `tests/templates_engine/` and CLI tests in `tests/test_cli.py`. The canonical (and only) test tree is `tests/`. The v1 PPTX path generates slides from scratch and Python controls all styling. The template engine instead fills the layout placeholders of a real, professionally designed `.pptx`, so output keeps the template's branding. The user picks a built-in template or uploads a deck; the LLM produces content JSON keyed to named placeholder fields; Python renders it into the template.

**Read before changing the engine:** `simplicitor/templates_engine/NOTES.md` holds the Phase A repo orientation, the error-handling contract every module conforms to, and the list of deferred follow-ups (each marked ACCEPTED, FIXED, CLOSED, or Open). To add a template: `simplicitor/templates_engine/HOWTO_ADD_TEMPLATE.md`.

### What a template is

A folder with exactly two files:
- `template.pptx`: design only, zero slides. Masters, layouts, and theme are kept; every slide is stripped.
- `manifest.yaml`: declares the fillable structure.

Manifest shape: `name`, `type` (`pptx`), `template_file`, `description`, and `slide_types`. Each slide type has a `layout_index` and a list of `fields`. Each field has `name`, `placeholder_idx`, `kind` (`text` | `bullets` | `image`), `required`, and optional `max_chars` (text only) / `max_items` (bullets only). Field names become the JSON keys the LLM fills.

### Template directory (unified root)

All templates live in one folder: `Settings.templates_dir` (default `Documents\Simplicitor\Templates`, configurable in the app's Settings dialog). The curated defaults (`business_pitch`, `technical_overview`) are seeded into it from the bundled built-in source (`simplicitor/templates_engine/builtin/<name>/`, read-only, ships with the app); user imports land next to them, tagged "user" by `list_library`. The CLI resolves the same folder by reading the persisted `settings.json` in the per-user data dir (`get_app_data_dir()`), falling back to the documented default when no settings file exists, and prints a one-line notice if templates are still found in the retired legacy root `%APPDATA%\Simplicitor\templates` (nothing is auto-moved). The old `simplicitor.toml` override is gone with that root. A folder missing either required file is silently skipped. Rebuilding a built-in `.pptx` means re-verifying its indices: `python simplicitor/cli.py inspect` or `scripts/inspect_template.py` both print them.

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
| `config.py` | `get_builtin_root` / `get_app_data_dir`, `list_library` / `ensure_default_templates` (unified root), `list_templates` (explicit roots, test use), `import_template` (root passed in) |

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

preflight -> build prompt -> call model -> strip code fences and parse JSON -> validate against the manifest -> on failure run ONE repair attempt with the specific errors fed back -> success renders; an exhausted retry fails with a conventional error and writes no file. A parse failure that looks truncated raises the repair `max_tokens` to the `OLLAMA_REPAIR_MAX_TOKENS` floor (`app/config/defaults.py`). A `--source` file, when given, is included in the prompt verbatim. There is no summarization or retrieval step (both were descoped).

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
