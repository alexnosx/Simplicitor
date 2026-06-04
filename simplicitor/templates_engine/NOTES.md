# templates_engine: Repo Orientation Notes (Phase A)

## Existing PPTX generation path

1. `app/widgets/create_panel.py` -- `CreatePanel` emits `generate_requested(file_type, save_path, prompt)` on Generate click.
2. `app/main_window.py` -- connects the signal, creates a `GenerateWorker` on a `QThread`.
3. `app/workers/generate_worker.py` -- `GenerateWorker.run()`:
   - Loads `prompts/system_pptx.txt`.
   - Calls `OllamaClient.generate(model, prompt, system_prompt)`.
   - Passes the response to `FileGenerator.generate(file_type, llm_response, output_path)`.
   - `FileGenerator` dispatches to `LlmResponseParser().parse_pptx_response()` then `PptxGenerator().generate(parsed, output_path)`.
4. `app/generators/pptx_generator.py` -- builds the presentation from parsed dict using python-pptx, writes to `output_path`.
5. Output directory: `Settings.generated_dir` (default `Documents/Simplicitor/Generated`).
6. On success: worker emits `completed(str(path))` -> panel `show_status()` + `show_open_file_btn()`.
7. On failure: worker emits `failed(user_friendly_str)` -> panel `show_status(is_error=True)` -> `StatusBanner`.

## GUI entry points

- `main.py` -- GUI entry, no CLI. Initialises `QApplication`, `Settings`, logging, then shows `MainWindow`.
- No `argparse` or `click`. All user interaction is via `MainWindow` and its panels.

## Where output files are written

- Generated files: `Settings.generated_dir` (configurable, JSON-persisted, defaults to `Documents/Simplicitor/Generated`).
- Uploaded files working copy: `Settings.uploads_dir`.
- Backups: `Settings.backups_dir`.
- Logs: `Settings.logs_dir`.
- `Settings` lives in `app/config/settings.py`, constants in `app/config/defaults.py`.

---

## Error-handling conventions to follow

**This section is the contract for all later phases. New modules must conform to these patterns.**

### Exception types (defined in service modules, not re-exported centrally)

| Type | Module | When to raise |
|------|--------|---------------|
| `OllamaConnectionError` | `app/services/ollama_client.py` | Network-level failure reaching Ollama |
| `OllamaTimeoutError(OllamaConnectionError)` | same | Request timeout |
| `OllamaGenerationError` | same | Non-200 response or missing `response` key |
| `ParseError(message, details="")` | `app/parsers/llm_response_parser.py` | LLM response cannot be parsed into expected structure; `details` holds technical context |
| `FileGenerationError` | `app/services/file_generator.py` | Full generate pipeline failure (wraps ParseError or OSError) |
| `ManipulationError` | `app/services/file_manipulator.py` | File read/write failures during manipulation |
| `ValueError` | (stdlib) | Programmer-supplied invalid argument (e.g. unknown file type in dispatcher) |

New modules should raise from this set where the semantics fit. For input faults from the new engine,
prefer `ValueError` (bad programmer arg) or `ParseError` (bad structured input). For genuine system/IO
faults, raise a new domain-specific exception following the same pattern (subclass of `Exception`, name
ends in `Error`, message is descriptive). **Do not reuse Ollama* exception types for non-Ollama failures.**
Missing or corrupt files at known paths are file read failures and raise `ManipulationError`. `ValueError`
is for malformed or semantically invalid arguments, not for path-target-missing.

### Logging convention

```python
import logging
logger = logging.getLogger(__name__)
```

- Every module gets its own `__name__`-keyed logger.
- Technical details and tracebacks go to the log: `logger.error("...", exc)`.
- Warnings for recoverable degradation: `logger.warning(...)`.
- **Never log file content or user prompt text** (privacy rule, enforced throughout).
- `setup_logging()` in `app/utils/logging_setup.py` configures the root logger once at startup.
  New modules do NOT call `setup_logging` -- they just call `logging.getLogger(__name__)`.

### User-facing error surface (GUI)

- Workers emit `failed(str)` with a **human-readable** message, no exception types or stack traces.
- Panels call `show_status(message, is_error=True)` -> `StatusBanner.show_message()`.
- `StatusBanner`: colored strip, primary label, X dismiss button. Never shows technical details.
- Message pattern: "[What happened] + [What you can do]".
- Example: `"The AI engine stopped responding. Please check Ollama is running."`

### No-partial-file discipline

- Generators write only after all content is ready. If `prs.save()` raises `OSError`, let it propagate.
- On any failure, delete partial output files before re-raising or emitting `failed`.
- Backups are never touched after a failure -- they always represent the original state.

### `check_connection()` exception contract

- `OllamaClient.check_connection()` **never raises** -- returns `bool`. Safe to call from polling loops.
- All other `OllamaClient` methods raise on network failure.

---

## Known follow-ups

Items deferred out of scope — persist here so they don't evaporate with session context.

1. **`breakdown.py` `_open_presentation()` raises `ValueError` for missing file** (Phase H regression).
   Should raise `ManipulationError` per the corrected convention (file read failure, not bad arg).
   Same fix applied to `render_pptx._open_template` in Phase H. See TODO comment in `breakdown.py:110`.
   Fix when next touching that file, or in Phase M hardening pass.

3. **`pipeline.run` floor semantics for `max_tokens` not yet wired** (Phase J).
   The spec describes `repair_max_tokens = max(original_budget or 0, OLLAMA_REPAIR_MAX_TOKENS)` as
   a floor, not a ceiling. Phase J omits the `original_budget` parameter from `pipeline.run` (no callers
   need it yet), so the floor is currently just `OLLAMA_REPAIR_MAX_TOKENS` directly. If a future caller
   wants a higher first-attempt budget, they cannot pass it through today. Fix when `pipeline.run`
   gains a `max_tokens` parameter: add `max_tokens: int | None = None` to the signature and compute
   `repair_max_tokens = max(max_tokens or 0, OLLAMA_REPAIR_MAX_TOKENS)` in the truncation-bump branch.

2. **`OllamaClient` discovery methods don't distinguish `Timeout` from `RequestException`** (Phase I).
   `get_models()`, `get_running_model()`, `get_model_info()` all map any `requests.RequestException`
   to `OllamaConnectionError`, including timeouts. Only `generate()` separates `Timeout` into
   `OllamaTimeoutError`. `preflight()` in `llm.py` reuses `get_models()`, so a slow-but-responsive
   Ollama will report `OllamaConnectionError` where `OllamaTimeoutError` is more precise.
   Acceptable for Phase I. Fix in a future `OllamaClient` refactor (add `requests.Timeout` handling
   to all discovery methods).

4. **`pipeline.generate_content` raises `ParseError` for a post-repair *validation* failure** (Phase K).
   When the repair attempt returns parseable JSON that still fails manifest validation, the loop
   raises `ParseError("Model returned invalid content after repair")` rather than a validation-specific
   error. This conflates a schema failure with a parse failure. The Phase K GUI maps the `ParseError`
   that is actually raised today, but the semantics are wrong: a schema failure is not a parse failure.
   Phase M (error-handling audit) target: introduce a distinct validation-exhaustion error, or at least a
   message naming the schema cause. The GUI's single ParseError mapping is NOT evidence the semantics
   are correct - it is a deliberate accommodation of current behavior. (`pipeline.py`, attempt-2 branch.)

5. **Blocked Ollama HTTP call is abandoned (not cancelled) at app quit** (Phase K).
   The MainWindow worker pattern (OllamaWorker / GenerateWorker / ManipulateWorker and now
   TemplateGenerateWorker) tears threads down in `closeEvent` with `quit()` + `wait(2000)`.
   `quit()` stops a thread's event loop but cannot interrupt a worker blocked in a synchronous
   Ollama HTTP request (up to OLLAMA_TIMEOUT_S). If the user quits the app mid-generation, the
   bounded wait times out and the thread is abandoned to process exit. This is the existing,
   accepted behavior for every worker; Phase K does not change it. TemplateDialog additionally
   blocks its own dismissal while generating, so the only abandonment window is a full app quit.
   A real fix is cooperative cancellation of the in-flight request (cancel token / short request
   timeout with retry), which is out of Phase K scope. Phase M (error-handling/robustness audit)
   target: add cancellation, or formally accept bounded-wait-and-abandon as final.
