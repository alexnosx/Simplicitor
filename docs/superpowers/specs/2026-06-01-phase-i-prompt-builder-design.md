# Phase I: Prompt Builder + Ollama Client Design

**Date:** 2026-06-01
**Scope:** `simplicitor/templates_engine/prompt_builder.py`, `simplicitor/templates_engine/llm.py`, `simplicitor/app/services/ollama_client.py` (new method), `simplicitor/app/config/defaults.py` (new constant), `simplicitor/cli.py` (new subcommand)
**Depends on:** Phases A-H (manifest, validation, config, breakdown, renderer all committed)

---

## 1. Public API

### `prompt_builder.build_prompt`

```python
def build_prompt(
    manifest: Manifest,
    user_request: str,
    source_text: str | None = None,
) -> list[dict]:
```

Returns a messages list in OpenAI chat format:

```python
[
    {"role": "system",    "content": "<system message>"},
    {"role": "user",      "content": "<one-shot user example>"},
    {"role": "assistant", "content": "<one-shot assistant response>"},
    {"role": "user",      "content": "<actual request>"},
]
```

**System message structure (in order):**
1. One-line instruction: "Return ONLY valid JSON. No markdown fences, no explanation, no preamble."
2. Schema block — derived from `manifest.slide_types`: shows the exact JSON shape with field names, kinds (`text`/`bullets`/`image`), required status, and constraints (`max_chars`, `max_items`).
3. Rules block: bullets are string arrays, omit optional fields if not needed, no extra keys.

**One-shot example:** Synthetic two-slide example (title slide + content slide) using real field names from the manifest. Hardcoded to show the expected JSON structure; not derived from live data.

**Actual user message:** `f"Request: {user_request}"` plus, if `source_text` is provided, a `"\nSource content:\n{source_text}"` section appended. If `source_text` is `None`, the source section is omitted entirely.

---

### `OllamaClient.chat_completion` (new method on existing class)

```python
def chat_completion(
    self,
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    timeout: int | None = None,
) -> str:
```

Calls `POST /v1/chat/completions` with:
```json
{
  "model": "<model>",
  "messages": [...],
  "temperature": 0.3,
  "response_format": {"type": "json_object"}
}
```

Returns `choices[0]["message"]["content"]` as a string.

Error mapping (same pattern as `generate()`):
- `requests.Timeout` → `OllamaTimeoutError`
- `requests.RequestException` → `OllamaConnectionError`
- Non-200 status → `OllamaGenerationError`
- Missing `choices[0].message.content` → `OllamaGenerationError`

`timeout` defaults to `OLLAMA_TIMEOUT_S` if not provided.

---

### `llm` module-level functions

```python
def _client(client: OllamaClient | None = None) -> OllamaClient:
    """Return the passed client if given; otherwise construct a default OllamaClient.
    The optional arg exists for test injection — pass a mock to avoid real HTTP calls."""

def preflight(model: str, client: OllamaClient | None = None) -> None:
    """Check Ollama is reachable and the model is available.
    Raises OllamaConnectionError (with remediation hint) if unreachable.
    Raises OllamaGenerationError (with remediation hint) if model not in installed list."""

def generate(
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    client: OllamaClient | None = None,
) -> str:
    """Call chat_completion and return the content string."""
```

`_client()` reads `OLLAMA_BASE_URL` from `app.config.defaults` to construct the default client. Tests inject a mock via the `client` parameter — no module-level patching required.

---

## 2. Error handling

All Ollama-facing errors reuse existing types from `app.services.ollama_client`. No new exception types.

| Condition | Exception | Remediation hint |
|-----------|-----------|-----------------|
| Ollama unreachable (from `preflight`) | `OllamaConnectionError` | "Check that Ollama is running." |
| Model not in installed list (from `preflight`) | `OllamaGenerationError` | "Run 'ollama pull \<model\>' to download it." |
| Request timeout (from `chat_completion`) | `OllamaTimeoutError` | (message includes timeout duration) |
| Connection dropped mid-request | `OllamaConnectionError` | (message includes base URL) |
| Non-200 response | `OllamaGenerationError` | (message includes status code) |
| Missing `choices[0].message.content` | `OllamaGenerationError` | (message includes actual response keys) |

`preflight` wraps `get_models()` in a try/except to enrich the `OllamaConnectionError` message with the remediation hint before re-raising. The original exception is chained (`from exc`).

Known limitation: `get_models()` maps `requests.Timeout` to `OllamaConnectionError` (not `OllamaTimeoutError`), so a slow-but-responsive Ollama reports the wrong error type from `preflight`. Logged in NOTES.md Known follow-ups — acceptable for Phase I.

---

## 3. CLI command

```
simplicitor generate --template <name> --request <text> [--source <file>] [--dry-run]
```

**`_cmd_generate` in `cli.py` (added after `_cmd_render`):**

1. Look up template via `list_templates()` — `ValueError` if not found.
2. Load manifest via `load_manifest`.
3. If `--source` provided: read source file — `ValueError` if not found or not readable.
4. Build prompt via `build_prompt(manifest, args.request, source_text)`.
5. If `--dry-run`: print system message then user message in readable layout, exit 0. No model call.
6. Otherwise: call `preflight(model)`, then `generate(messages, model)`, print raw JSON response to stdout.
   Two-line comment in handler: Phase I prints raw model JSON to stdout as scaffolding.
   Phase J replaces this with the full render + repair loop + --out path.

Model name: CLI `--model` argument defaulting to `"llama3"`. Configurable at call time; full config integration is Phase J.

Error surface: wrapping `except (ValueError, OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError)` → `print(f"Error: {exc}", file=sys.stderr); return 1`.

---

## 4. `--dry-run` output format

```
=== SYSTEM ===
<system message content>

=== USER (one-shot example) ===
<example user message>

=== ASSISTANT (one-shot response) ===
<example assistant response>

=== USER (request) ===
<actual user message>
```

Human-readable layout. Not the raw messages JSON array.

---

## 5. New constant in `defaults.py`

```python
OLLAMA_CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
```

Added alongside the existing `OLLAMA_CHAT_ENDPOINT = "/api/chat"`.

---

## 6. Test coverage

**`tests/test_ollama_client.py`** (new tests in existing file):
- `test_chat_completion_returns_content_string` — mock successful response, assert string returned
- `test_chat_completion_timeout_raises_ollama_timeout_error` — mock `requests.Timeout`
- `test_chat_completion_connection_error_raises_ollama_connection_error` — mock `RequestException`
- `test_chat_completion_non_200_raises_ollama_generation_error` — mock status 500
- `test_chat_completion_missing_choices_raises_ollama_generation_error` — mock malformed response

**`tests/templates_engine/test_prompt_builder.py`** (new file):
- `test_build_prompt_returns_four_messages` — list with 4 dicts
- `test_build_prompt_system_message_contains_all_slide_types` — all manifest slide_types in system message
- `test_build_prompt_system_message_contains_field_names` — field names from manifest present
- `test_build_prompt_contains_one_shot_exchange` — user+assistant pair before final user message
- `test_build_prompt_last_message_contains_user_request` — user_request in last message content
- `test_build_prompt_includes_source_text_when_provided` — source_text in last message
- `test_build_prompt_omits_source_section_when_none` — no "Source content:" if source_text=None

**`tests/templates_engine/test_llm.py`** (new file):
- `test_preflight_raises_connection_error_when_ollama_unreachable` — inject mock that raises `OllamaConnectionError`; assert re-raised with remediation hint
- `test_preflight_raises_generation_error_when_model_not_available` — inject mock with different model list
- `test_preflight_succeeds_when_model_available` — inject mock with correct model list; no raise
- `test_generate_returns_content_string` — inject mock client; assert `chat_completion` called and result returned
- `test_generate_timeout_propagates` — inject mock that raises `OllamaTimeoutError`; assert it propagates

---

## 7. Decisions recorded

- `llm.py` uses `/v1/chat/completions` (OpenAI-compatible), not `/api/generate` or `/api/chat`. JSON mode via `response_format: {"type": "json_object"}` — supported in Ollama 0.1.9+; fails gracefully (no crash) on older versions.
- `OllamaClient.chat_completion()` added to the class (Option B). `llm.py` is a thin facade. Avoids duplicating the `requests.Timeout/RequestException` error mapping that already lives in `OllamaClient`.
- `_client()` takes an optional `client` arg for test injection. No module-level monkey-patching needed in tests.
- `preflight` raises, not returns bool. "-> ok" in the spec is imprecise; the Done Check ("raises conventional model-error") is authoritative.
- Phase I CLI prints raw model JSON to stdout. Phase J wires the full render + repair + `--out` path. Documented in a two-line comment in the handler.
- One-shot example is synthetic — shows JSON structure, not real content. Real examples from manifests are out of scope for Phase I.
