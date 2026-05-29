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
