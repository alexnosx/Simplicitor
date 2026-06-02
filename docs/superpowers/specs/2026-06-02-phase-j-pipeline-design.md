# Phase J: Generate-Validate-Repair-Render Pipeline

**Date:** 2026-06-02
**Scope:** `simplicitor/templates_engine/pipeline.py` (new), `simplicitor/app/parsers/llm_response_parser.py` (rename + call sites), `simplicitor/app/services/ollama_client.py` (max_tokens param), `simplicitor/templates_engine/llm.py` (max_tokens param), `simplicitor/templates_engine/prompt_builder.py` (repair prompt), `simplicitor/app/config/defaults.py` (new constant), `simplicitor/cli.py` (--out, pipeline wired)
**Depends on:** Phases A-I (manifest, validation, config, breakdown, renderer, prompt builder, llm facade all committed)

---

## 1. Overview

Phase I left `_cmd_generate` printing raw model JSON to stdout with a two-line comment:
```python
# Phase I: prints raw model JSON to stdout as scaffolding.
# Phase J replaces this with the full render + repair loop + --out path.
```

Phase J delivers that replacement. The end-to-end flow through the CLI becomes:

```
simplicitor generate --template <name> --request <text> --out <deck.pptx>
```

Internally:
```
build_prompt → llm.generate → clean → json.loads → validate_content → render → .pptx
                                          ↓ (on any failure, one repair attempt)
                               build_repair_prompt → llm.generate → clean → json.loads → validate_content → render
```

---

## 2. `LlmResponseParser._clean` → `clean` rename

**Motivation:** `_clean` is a static text normalizer that any caller with raw LLM output has a legitimate reason to use. Keeping it private while `pipeline.py` needs it would require calling a private method across module boundaries. The correct fix is to make it public.

**Change:** Rename `_clean` to `clean` on `LlmResponseParser`. Update all call sites in the same commit.

**Call-site inventory** (confirmed by grep before spec):

| File | Line | Change |
|------|------|--------|
| `app/parsers/llm_response_parser.py` | definition | `def _clean` → `def clean` |
| `app/parsers/llm_response_parser.py:91` | `parse_word_response` | `self._clean(text)` → `self.clean(text)` |
| `app/parsers/llm_response_parser.py:157` | `parse_excel_response` | `self._clean(text)` → `self.clean(text)` |
| `app/parsers/llm_response_parser.py:228` | `parse_pptx_response` | `self._clean(text)` → `self.clean(text)` |
| `app/workers/generate_worker.py:90` | comment only | update comment text to reference `.clean()` |

No tests call `_clean` directly. No other external call sites exist in the repo.

---

## 3. New constant

```python
# defaults.py
OLLAMA_REPAIR_MAX_TOKENS = 4096
```

This is the **floor** for the repair-attempt max_tokens budget when truncation is detected. At the call site in `pipeline.py`, the actual value is computed as:

```python
repair_max_tokens = max(original_max_tokens or 0, OLLAMA_REPAIR_MAX_TOKENS)
```

This ensures the constant is a minimum, not a ceiling. If a future caller passes a higher `max_tokens` to `pipeline.run`, the repair bump never silently caps it.

---

## 4. `OllamaClient.chat_completion` — `max_tokens` parameter

```python
def chat_completion(
    self,
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    timeout: int | None = None,
    max_tokens: int | None = None,
) -> str:
```

When `max_tokens` is not `None`, it is included in the request body:
```python
if max_tokens is not None:
    body["max_tokens"] = max_tokens
```

When `None` (default), the key is absent from the body. Ollama's own default applies. **All existing call sites are unaffected** -- the parameter is keyword-only at the tail of the signature.

---

## 5. `llm.generate` — `max_tokens` parameter

```python
def generate(
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    max_tokens: int | None = None,
    client: OllamaClient | None = None,
) -> str:
```

Threading to `chat_completion`: pass `max_tokens` as a keyword argument only when not `None`, to preserve the call signature observed by existing test assertions:

```python
def generate(messages, model, temperature=0.3, max_tokens=None, client=None):
    kwargs = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return _client(client).chat_completion(messages, model, temperature, **kwargs)
```

Existing test `assert_called_once_with(messages, "llama3", 0.3)` continues to pass when `max_tokens=None` because `chat_completion` is called without kwargs.

---

## 6. `build_repair_prompt` in `prompt_builder.py`

```python
def build_repair_prompt(
    original_messages: list[dict],
    raw_response: str,
    errors: list[str] | None = None,
) -> list[dict]:
```

Returns `original_messages` plus two new messages: an `assistant` message containing the model's previous output, followed by a `user` correction message. The correction is differentiated by failure type:

**Parse failure** (`errors=None`):
```python
{
    "role": "user",
    "content": (
        "Your previous response could not be parsed as JSON.\n\n"
        f"Previous output:\n{raw_response}\n\n"
        "Return ONLY valid JSON matching the schema. "
        "No prose, no markdown fences, no think blocks."
    )
}
```

**Validation failure** (`errors=[...]`):
```python
{
    "role": "user",
    "content": (
        "Your previous response had schema validation errors:\n\n"
        f"{format_validation_errors(errors)}\n\n"
        "Fix only the fields listed above. Return the complete corrected JSON."
    )
}
```

`format_validation_errors` is imported from `templates_engine.validation` (already exists from Phase C; its docstring explicitly notes it is "designed to feed the LLM repair loop in Phase J").

---

## 7. `pipeline.py` — public API

```python
def run(
    manifest: Manifest,
    template_dir: Path | str,
    messages: list[dict],
    model: str,
    out_path: Path | str,
    client: OllamaClient | None = None,
) -> dict:
```

Returns `{"path": Path, "issues": list[str]}` -- the same dict shape as `render()`.

Raises:
- `ParseError` -- if the model cannot produce parseable, valid JSON after one repair attempt.
- `OllamaTimeoutError`, `OllamaConnectionError`, `OllamaGenerationError` -- propagated as-is from `llm.generate`.
- `ManipulationError` -- propagated from `render()` (layout/placeholder mismatch, I/O failure).
- `ValueError` -- propagated from `render()` (corrupt/missing template).

No new exception types. Conforms to NOTES.md exception table.

---

## 8. `pipeline.py` — internal helpers

### `_looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool`

Cheap truncation heuristic. Returns `True` if either condition holds:

1. **Position-based:** `exc.pos` is not `None` and lands within 10 characters of the end of `cleaned`.
2. **Structural:** a single pass counting `{` / `[` increments and `}` / `]` decrements produces a positive final depth (more openers than closers).

```python
def _looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool:
    if exc.pos is not None and exc.pos >= len(cleaned) - 10:
        return True
    depth = 0
    for ch in cleaned:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return depth > 0
```

### `_try_parse(raw: str) -> tuple[dict | None, json.JSONDecodeError | None]`

Applies `LlmResponseParser.clean(raw)` then `json.loads`. Returns `(parsed, None)` on success; `(None, exc)` on failure. Never raises. Used so the pipeline can branch on the `JSONDecodeError` without interrupting control flow.

---

## 9. `pipeline.run` — full flow

```python
def run(manifest, template_dir, messages, model, out_path, client=None):
    from app.parsers.llm_response_parser import LlmResponseParser, ParseError
    from app.services.file_manipulator import ManipulationError
    from templates_engine.prompt_builder import build_repair_prompt
    from templates_engine.validation import format_validation_errors, validate_content
    from templates_engine.render_pptx import render
    from templates_engine import llm

    # ── Attempt 1 ────────────────────────────────────────────────────────────
    raw1 = llm.generate(messages, model, client=client)
    parsed1, parse_exc1 = _try_parse(raw1)

    if parsed1 is not None:
        ok, result = validate_content(manifest, parsed1)
        if ok:
            return render(manifest, result, out_path, template_dir)
        # Validation failed → repair with error list
        repair_msgs = build_repair_prompt(messages, raw1, errors=result)
        repair_max_tokens = None  # validation failures do not trigger token bump

    else:
        # Parse failed → truncation check, repair with parse-failure correction
        cleaned1 = LlmResponseParser.clean(raw1)
        truncated = _looks_truncated(cleaned1, parse_exc1)
        original_budget = None  # Phase J callers do not pass max_tokens to run()
        repair_max_tokens = (
            max(original_budget or 0, OLLAMA_REPAIR_MAX_TOKENS) if truncated else None
        )
        repair_msgs = build_repair_prompt(messages, raw1, errors=None)

    # ── Attempt 2 (repair) ───────────────────────────────────────────────────
    raw2 = llm.generate(repair_msgs, model, max_tokens=repair_max_tokens, client=client)
    parsed2, parse_exc2 = _try_parse(raw2)

    if parsed2 is None:
        raise ParseError(
            "LLM response could not be parsed as JSON after repair",
            details=str(parse_exc2),
        )

    ok2, result2 = validate_content(manifest, parsed2)
    if not ok2:
        raise ParseError(
            "Model returned invalid content after repair",
            details=format_validation_errors(result2),
        )

    return render(manifest, result2, out_path, template_dir)
```

Logging: `logger.warning(...)` before each repair attempt (states why: parse failure or validation failure, with error count for validation). `logger.error(...)` before raising `ParseError` on hard fail. Never logs `raw1` / `raw2` content (privacy rule).

---

## 10. Truncation-bump strategy gate (MUST run before implementing section 8)

Before writing the truncation-bump branch in `pipeline.py`, verify that `done_reason == "length"` actually occurs on the Ollama chat-completions endpoint when output is cut short.

**Procedure:**
1. Use the existing `generate` CLI with a template and a prompt likely to produce a large response.
2. Inspect the raw Ollama response metadata for `done_reason`.
3. Decision:
   - `done_reason == "length"` → truncation-bump strategy is valid. Implement as specced.
   - `done_reason == "stop"` or context-overflow → `max_tokens` is not the constraint. Document the actual cause in NOTES.md under Known follow-ups. Surface to user before continuing. Strategy changes to prompt-shrink or schema-chunking, not a token bump.

This gate applies only to the truncation-bump logic in `_looks_truncated` / `repair_max_tokens`. The rest of the pipeline (parse failure repair, validation failure repair) is not gated on this result.

---

## 11. `cli.py` changes

### `--out` argument
Added to the `generate` subparser:
```python
generate_p.add_argument(
    "--out", default=None,
    help="Output .pptx path (required unless --dry-run)."
)
```

Handler-level validation (placed before any pipeline logic):
```python
if not args.dry_run and not args.out:
    print(
        "Error: --out is required. Use --dry-run to inspect the prompt without generating a file.",
        file=sys.stderr,
    )
    return 1
```

### Scaffolding replacement
The two-line scaffolding comment and the `llm.preflight / print(raw)` block are replaced:
```python
from templates_engine import pipeline

llm.preflight(args.model)
result = pipeline.run(manifest, match["path"], messages, args.model, args.out)
print(result["path"])
for issue in result["issues"]:
    print(f"Warning: {issue}")
```

`--dry-run` path is **unchanged** from Phase I (short-circuits before any pipeline call).

---

## 12. Error surface at the CLI

`_cmd_generate` already catches `(ValueError, OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError)`. Add `ParseError` and `ManipulationError` to the tuple:

```python
except (ValueError, ParseError, ManipulationError,
        OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError) as exc:
    print(f"Error: {exc}", file=sys.stderr)
    return 1
```

`ParseError` is imported from `app.parsers.llm_response_parser`. `ManipulationError` from `app.services.file_manipulator`.

---

## 13. Test coverage

### `tests/templates_engine/test_pipeline.py` (new file)

All tests use the real `render_manifest.yaml` fixture, real `LlmResponseParser.clean`, real `json.loads`, real pydantic validation. Only `llm.generate` is mocked.

| Test | Mock setup | Assertion |
|------|-----------|-----------|
| `test_run_valid_first_attempt` | `generate` returns valid JSON once | File written; `generate` called once; returned dict has `path` and `issues` keys |
| `test_run_parse_failure_repair_success` | Attempt 1: `"not json"`. Attempt 2: valid JSON | File written; `generate` called twice; second call's `messages` contains "could not be parsed" |
| `test_run_validation_failure_repair_success` | Attempt 1: parseable JSON with required field missing. Attempt 2: valid JSON | File written; `generate` called twice; second call's `messages` contain the field error text |
| `test_run_repair_still_fails_parse` | Both attempts: `"not json"` | `ParseError` raised |
| `test_run_repair_still_fails_validation` | Both attempts: parseable JSON with required field missing | `ParseError` raised |
| `test_run_truncation_bump_passes_max_tokens` | Attempt 1: `'{"slides": [{"type":'` (unbalanced). Attempt 2: valid JSON | `generate` second call receives `max_tokens >= OLLAMA_REPAIR_MAX_TOKENS`; verified via `call_args` |

"Valid JSON" in test fixtures means a dict that passes `validate_content` against `render_manifest.yaml` with at least one slide. Tests assert on the content of the written file (slide count, field values) rather than just file existence.

### Additional tests in existing files

**`tests/test_ollama_client.py`** (+2):
- `test_chat_completion_max_tokens_included_in_body` -- patch `requests.post`, pass `max_tokens=512`, assert `body["max_tokens"] == 512`
- `test_chat_completion_max_tokens_absent_when_none` -- pass `max_tokens=None`, assert `"max_tokens" not in body`

**`tests/templates_engine/test_prompt_builder.py`** (+3):
- `test_build_repair_prompt_appends_two_messages` -- assert `len(result) == len(original) + 2`
- `test_build_repair_prompt_parse_failure_contains_no_prose_instruction` -- `errors=None`; assert `"no prose"` and `"no markdown fences"` in last message content
- `test_build_repair_prompt_validation_failure_contains_error_strings` -- `errors=["slides[0].fields.title: Field required."]`; assert error string in last message content

**`tests/templates_engine/test_llm.py`** (+1):
- `test_generate_threads_max_tokens_to_chat_completion` -- pass `max_tokens=512`; assert `mock.chat_completion` called with `max_tokens=512` in kwargs

---

## 14. File change summary

| File | Change type |
|------|-------------|
| `simplicitor/templates_engine/pipeline.py` | New |
| `tests/templates_engine/test_pipeline.py` | New |
| `simplicitor/app/config/defaults.py` | +1 constant (`OLLAMA_REPAIR_MAX_TOKENS`) |
| `simplicitor/app/parsers/llm_response_parser.py` | Rename `_clean` → `clean`; update 3 internal call sites; update 1 comment |
| `simplicitor/app/workers/generate_worker.py` | Update 1 comment referencing `_clean()` |
| `simplicitor/app/services/ollama_client.py` | +`max_tokens` param on `chat_completion` |
| `simplicitor/templates_engine/llm.py` | +`max_tokens` param on `generate` |
| `simplicitor/templates_engine/prompt_builder.py` | +`build_repair_prompt` |
| `simplicitor/cli.py` | +`--out`, +error validation, replace scaffolding, extend except tuple |
| `tests/test_ollama_client.py` | +2 tests |
| `tests/templates_engine/test_prompt_builder.py` | +3 tests |
| `tests/templates_engine/test_llm.py` | +1 test |

---

## 15. Decisions recorded

- `pipeline.py` calls `LlmResponseParser.clean(raw)` directly. `_clean` renamed to `clean` (public static method) in the same commit as the pipeline. No wrapper, no new module-level function.
- One repair attempt, regardless of failure type (parse or validation). No second-chance on repair failure -- hard-fail with `ParseError`.
- `max_tokens` passed as kwargs only when not `None` in `llm.generate`. Preserves existing test assertions. Existing call sites are not affected.
- `OLLAMA_REPAIR_MAX_TOKENS` is a floor, not a ceiling. Floor computation: `max(original_budget or 0, OLLAMA_REPAIR_MAX_TOKENS)`.
- Truncation-bump strategy is gated on `done_reason` verification before implementation. If `done_reason != "length"`, strategy changes and spec is updated before continuing.
- `--dry-run` is Phase I work, unchanged in Phase J. Phase J's only `--dry-run` interaction: `--out` is optional in the argparser with handler-level validation.
- `_cmd_generate` except tuple extended to include `ParseError` and `ManipulationError`. Both have human-readable `str()` representations and conform to NOTES.md exception table.
