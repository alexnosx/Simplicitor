# Phase J: Generate-Validate-Repair-Render Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the complete generate → clean → parse → validate → (repair) → render pipeline behind `simplicitor generate --out deck.pptx`, replacing the Phase I scaffolding stub.

**Architecture:** New `templates_engine/pipeline.py` orchestrates one `llm.generate` call, cleans and parses the response, validates against the manifest's Pydantic model, and on any failure (parse or validation) attempts one repair before hard-failing with `ParseError`. `chat_completion` and `llm.generate` gain a `max_tokens` kwarg for the truncation-bump branch. `build_repair_prompt` in `prompt_builder.py` constructs differentiated correction messages. The CLI `generate` command gains `--out` and dispatches to the pipeline.

**Tech Stack:** `requests`, `python-pptx`, `pydantic`, `pytest`, existing `OllamaConnectionError/TimeoutError/GenerationError` from `app.services.ollama_client`, `ParseError` from `app.parsers.llm_response_parser`, `ManipulationError` from `app.services.file_manipulator`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `simplicitor/app/parsers/llm_response_parser.py` | Modify | Rename `_clean` → `clean`; update 3 internal call sites; update 1 comment in `generate_worker.py` |
| `simplicitor/app/workers/generate_worker.py` | Modify | Update comment referencing `_clean()` |
| `simplicitor/app/config/defaults.py` | Modify | Add `OLLAMA_REPAIR_MAX_TOKENS = 4096` |
| `simplicitor/app/services/ollama_client.py` | Modify | Add `max_tokens: int \| None = None` to `chat_completion` |
| `simplicitor/templates_engine/llm.py` | Modify | Add `max_tokens: int \| None = None` to `generate`; thread via kwargs only when not None |
| `simplicitor/templates_engine/prompt_builder.py` | Modify | Add `build_repair_prompt(original_messages, raw_response, errors=None) -> list[dict]` |
| `simplicitor/templates_engine/pipeline.py` | Create | `run()`, `_try_parse()`, `_looks_truncated()` |
| `simplicitor/cli.py` | Modify | Add `--out`; handler validation; wire `pipeline.run`; extend except tuple |
| `tests/test_ollama_client.py` | Modify | +2 tests for `max_tokens` in `TestChatCompletion` |
| `tests/templates_engine/test_llm.py` | Modify | +1 test for `max_tokens` threading |
| `tests/templates_engine/test_prompt_builder.py` | Modify | +3 tests for `build_repair_prompt` |
| `tests/templates_engine/test_pipeline.py` | Create | 6 pipeline tests |

---

## Task 1: Rename `_clean` → `clean` on `LlmResponseParser`

**Files:**
- Modify: `simplicitor/app/parsers/llm_response_parser.py`
- Modify: `simplicitor/app/workers/generate_worker.py`

- [ ] **Step 1: Apply rename and internal call-site updates**

In `simplicitor/app/parsers/llm_response_parser.py`, make these four changes:

Change line 37 (definition):
```python
# Before:
    def _clean(text: str) -> str:
# After:
    def clean(text: str) -> str:
```

Change line 91 (`parse_word_response`):
```python
# Before:
        cleaned = self._clean(text)
# After:
        cleaned = self.clean(text)
```

Change line 157 (`parse_excel_response`):
```python
# Before:
        cleaned = self._clean(text)
# After:
        cleaned = self.clean(text)
```

Change line 228 (`parse_pptx_response`):
```python
# Before:
        cleaned = self._clean(text)
# After:
        cleaned = self.clean(text)
```

In `simplicitor/app/workers/generate_worker.py`, update the comment at line 90:
```python
# Before:
        # rely on the system prompt's JSON-only instruction and _clean()'s extraction logic.
# After:
        # rely on the system prompt's JSON-only instruction and .clean()'s extraction logic.
```

- [ ] **Step 2: Confirm no stray `_clean(` references remain**

Run from `C:\Repos`:
```
python -m grep -r "_clean(" simplicitor/ tests/ 2>/dev/null || echo "none"
```

Or use the Grep tool with pattern `_clean\(` across the repo. Expected: zero hits.

- [ ] **Step 3: Run full test suite to confirm no regression**

Run from `C:\Repos`:
```
python -m pytest tests/ -q
```

Expected: all 516 tests pass. If any fail, the rename missed a call site — fix before proceeding.

---

## Task 2: Add `OLLAMA_REPAIR_MAX_TOKENS` to `defaults.py`

**Files:**
- Modify: `simplicitor/app/config/defaults.py`

- [ ] **Step 1: Add the constant after the existing Ollama constants block**

Open `simplicitor/app/config/defaults.py`. Find the line:
```python
OLLAMA_MANIPULATION_TIMEOUT_S = 120  # manipulation sends file content → needs more time
```

Add directly after it:
```python
OLLAMA_REPAIR_MAX_TOKENS = 4096      # floor for max_tokens on truncation-bump repair attempt
```

- [ ] **Step 2: Verify the import works**

Run from `C:\Repos\simplicitor`:
```
python -c "from app.config.defaults import OLLAMA_REPAIR_MAX_TOKENS; print(OLLAMA_REPAIR_MAX_TOKENS)"
```

Expected: `4096`

---

## Task 3: Add `max_tokens` param to `OllamaClient.chat_completion` + tests

**Files:**
- Modify: `simplicitor/app/services/ollama_client.py`
- Modify: `tests/test_ollama_client.py`

- [ ] **Step 1: Write the two failing tests**

Open `tests/test_ollama_client.py`. Find the end of the `TestChatCompletion` class (after `test_chat_completion_missing_choices_raises_ollama_generation_error`). Append these two tests inside the class:

```python
    def test_chat_completion_max_tokens_included_in_body(self):
        client = OllamaClient(BASE_URL)
        mock_resp = _mock_response(200, {
            "choices": [{"message": {"content": '{"slides": []}'}}]
        })
        with patch("app.services.ollama_client.requests.post", return_value=mock_resp) as mock_post:
            client.chat_completion(self.MESSAGES, "llama3", max_tokens=512)
        body = mock_post.call_args[1]["json"]
        assert body["max_tokens"] == 512

    def test_chat_completion_max_tokens_absent_when_none(self):
        client = OllamaClient(BASE_URL)
        mock_resp = _mock_response(200, {
            "choices": [{"message": {"content": '{"slides": []}'}}]
        })
        with patch("app.services.ollama_client.requests.post", return_value=mock_resp) as mock_post:
            client.chat_completion(self.MESSAGES, "llama3", max_tokens=None)
        body = mock_post.call_args[1]["json"]
        assert "max_tokens" not in body
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `C:\Repos`:
```
python -m pytest tests/test_ollama_client.py::TestChatCompletion::test_chat_completion_max_tokens_included_in_body tests/test_ollama_client.py::TestChatCompletion::test_chat_completion_max_tokens_absent_when_none -v
```

Expected: 2 failures (`TypeError: chat_completion() got an unexpected keyword argument 'max_tokens'`).

- [ ] **Step 3: Add `max_tokens` parameter to `chat_completion`**

Open `simplicitor/app/services/ollama_client.py`. Find the `chat_completion` method signature:

```python
    def chat_completion(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.3,
        timeout: int | None = None,
    ) -> str:
```

Change to:

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

Find the body dict construction inside `chat_completion`:

```python
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
```

Change to:

```python
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
```

Also update the docstring to document the new parameter — add after the `timeout` line in Args:
```
            max_tokens: Maximum number of tokens to generate. When None (default),
                Ollama's own default applies. Pass an explicit value to raise the
                output budget on retry attempts.
```

- [ ] **Step 4: Run tests to confirm they pass**

Run from `C:\Repos`:
```
python -m pytest tests/test_ollama_client.py::TestChatCompletion -v
```

Expected: all 7 tests pass (5 original + 2 new).

- [ ] **Step 5: Full suite regression check**

```
python -m pytest tests/ -q
```

Expected: all 518 tests pass.

---

## Task 4: Add `max_tokens` param to `llm.generate` + test

**Files:**
- Modify: `simplicitor/templates_engine/llm.py`
- Modify: `tests/templates_engine/test_llm.py`

- [ ] **Step 1: Write the failing test**

Open `tests/templates_engine/test_llm.py`. Append this test at the end of the file:

```python
def test_generate_threads_max_tokens_to_chat_completion():
    mock = _mock_client(chat_return='{"slides": []}')
    messages = [{"role": "user", "content": "Make a deck."}]
    generate(messages, "llama3", max_tokens=512, client=mock)
    mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3, max_tokens=512)
```

- [ ] **Step 2: Run test to confirm it fails**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_llm.py::test_generate_threads_max_tokens_to_chat_completion -v
```

Expected: FAIL (`TypeError: generate() got an unexpected keyword argument 'max_tokens'`).

- [ ] **Step 3: Add `max_tokens` to `llm.generate`**

Open `simplicitor/templates_engine/llm.py`. Replace the `generate` function:

```python
def generate(
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    max_tokens: int | None = None,
    client: OllamaClient | None = None,
) -> str:
    """Call Ollama chat completions and return the response content string.

    Args:
        messages: OpenAI-format message list.
        model: Ollama model name.
        temperature: Sampling temperature (default 0.3 for structured output).
        max_tokens: Maximum tokens to generate. None means Ollama's default applies.
            Pass an explicit value to raise the output budget on repair attempts.
        client: Optional injected OllamaClient for testing.

    Returns:
        The raw content string from the model (expected to be JSON).

    Raises:
        OllamaTimeoutError: If the request times out.
        OllamaConnectionError: If the request fails at the network level.
        OllamaGenerationError: If the response is malformed or non-200.
    """
    kwargs: dict = {}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return _client(client).chat_completion(messages, model, temperature, **kwargs)
```

- [ ] **Step 4: Run all llm tests to confirm they pass**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_llm.py -v
```

Expected: all 10 tests pass (9 original + 1 new).

Note: `test_generate_returns_content_string` asserts `mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3)`. This passes because when `max_tokens=None`, no kwargs are added and `chat_completion` is called with exactly three positional args.

- [ ] **Step 5: Full suite regression check**

```
python -m pytest tests/ -q
```

Expected: all 519 tests pass.

---

## Task 5: Add `build_repair_prompt` to `prompt_builder.py` + tests

**Files:**
- Modify: `simplicitor/templates_engine/prompt_builder.py`
- Modify: `tests/templates_engine/test_prompt_builder.py`

- [ ] **Step 1: Write the three failing tests**

Open `tests/templates_engine/test_prompt_builder.py`. Add this import at the top of the file (after the existing imports):

```python
from templates_engine.prompt_builder import build_prompt, build_repair_prompt
```

Replace the existing import line:
```python
from templates_engine.prompt_builder import build_prompt
```
with:
```python
from templates_engine.prompt_builder import build_prompt, build_repair_prompt
```

Then append these three tests at the end of the file:

```python
# ---------------------------------------------------------------------------
# build_repair_prompt
# ---------------------------------------------------------------------------

def test_build_repair_prompt_appends_two_messages(manifest):
    original = build_prompt(manifest, "Make a deck.")
    result = build_repair_prompt(original, "not json")
    assert len(result) == len(original) + 2
    assert result[-2]["role"] == "assistant"
    assert result[-1]["role"] == "user"


def test_build_repair_prompt_parse_failure_instruction(manifest):
    original = build_prompt(manifest, "Make a deck.")
    result = build_repair_prompt(original, "not json", errors=None)
    correction = result[-1]["content"]
    assert "could not be parsed" in correction
    assert "no prose" in correction.lower()
    assert "no markdown fences" in correction.lower()


def test_build_repair_prompt_validation_failure_contains_error_strings(manifest):
    original = build_prompt(manifest, "Make a deck.")
    errors = ["slides[0].fields.title: Field required."]
    result = build_repair_prompt(original, '{"slides": []}', errors=errors)
    correction = result[-1]["content"]
    assert "slides[0].fields.title: Field required." in correction
    assert "Fix only the fields" in correction
```

- [ ] **Step 2: Run tests to confirm they fail**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_prompt_builder.py::test_build_repair_prompt_appends_two_messages tests/templates_engine/test_prompt_builder.py::test_build_repair_prompt_parse_failure_instruction tests/templates_engine/test_prompt_builder.py::test_build_repair_prompt_validation_failure_contains_error_strings -v
```

Expected: 3 failures (`ImportError: cannot import name 'build_repair_prompt'`).

- [ ] **Step 3: Implement `build_repair_prompt`**

Open `simplicitor/templates_engine/prompt_builder.py`. Add this import at the top — add `format_validation_errors` to imports. After the existing imports, add:

```python
from templates_engine.validation import format_validation_errors
```

Then append this function at the end of the file:

```python
def build_repair_prompt(
    original_messages: list[dict],
    raw_response: str,
    errors: list[str] | None = None,
) -> list[dict]:
    """Build a repair prompt by appending a correction block to the original messages.

    Extends the conversation with the model's previous (bad) output as an assistant
    message, followed by a user correction message explaining what was wrong.

    Args:
        original_messages: The messages list from build_prompt (4 messages).
        raw_response: The model's previous raw output (the bad response).
        errors: If None, the failure was a JSON parse error. If a list of strings,
            these are the pydantic validation error messages from validate_content().

    Returns:
        original_messages + [assistant: raw_response, user: correction_text]
    """
    if errors is None:
        correction = (
            "Your previous response could not be parsed as JSON.\n\n"
            f"Previous output:\n{raw_response}\n\n"
            "Return ONLY valid JSON matching the schema. "
            "No prose, no markdown fences, no think blocks."
        )
    else:
        correction = (
            "Your previous response had schema validation errors:\n\n"
            f"{format_validation_errors(errors)}\n\n"
            "Fix only the fields listed above. Return the complete corrected JSON."
        )

    return list(original_messages) + [
        {"role": "assistant", "content": raw_response},
        {"role": "user",      "content": correction},
    ]
```

- [ ] **Step 4: Run tests to confirm they pass**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_prompt_builder.py -v
```

Expected: all 11 tests pass (8 original + 3 new).

- [ ] **Step 5: Full suite regression check**

```
python -m pytest tests/ -q
```

Expected: all 522 tests pass.

---

## Task 6: Write failing pipeline tests

**Files:**
- Create: `tests/templates_engine/test_pipeline.py`

These tests are written BEFORE the implementation. All 6 will fail at import time until Task 7 creates `pipeline.py`.

- [ ] **Step 1: Create `tests/templates_engine/test_pipeline.py`**

```python
# tests/templates_engine/test_pipeline.py
# Phase J: Tests for the generate-validate-repair-render pipeline.
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from templates_engine.manifest import load_manifest
from templates_engine import pipeline

FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "render_manifest.yaml"

# Minimal valid JSON that passes validate_content for render_manifest.yaml.
# title_slide requires: title (text, max_chars=20). "My Title" is 8 chars.
VALID_CONTENT = json.dumps({
    "slides": [{"type": "title_slide", "fields": {"title": "My Title"}}]
})

# Parseable JSON that fails validation: title_slide's required 'title' field is absent.
INVALID_CONTENT = json.dumps({
    "slides": [{"type": "title_slide", "fields": {}}]
})

# Structurally incomplete JSON: unbalanced braces → _looks_truncated returns True.
TRUNCATED_CONTENT = '{"slides": [{"type": "title_slide",'


@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_run_valid_first_attempt(manifest, tmp_template):
    """Pipeline succeeds on first attempt with no repair needed."""
    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", return_value=VALID_CONTENT) as mock_gen:
        result = pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert mock_gen.call_count == 1
    assert result["path"] == out_path
    assert isinstance(result["issues"], list)
    assert out_path.exists()


# ---------------------------------------------------------------------------
# Repair on parse failure
# ---------------------------------------------------------------------------

def test_run_parse_failure_repair_success(manifest, tmp_template):
    """Attempt 1 returns unparseable text; attempt 2 returns valid JSON. File is written."""
    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", side_effect=["not json", VALID_CONTENT]) as mock_gen:
        result = pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert mock_gen.call_count == 2
    assert out_path.exists()
    # Second call's messages must contain the parse-failure correction instruction.
    second_call_messages = mock_gen.call_args_list[1].args[0]
    correction_text = second_call_messages[-1]["content"]
    assert "could not be parsed" in correction_text


# ---------------------------------------------------------------------------
# Repair on validation failure
# ---------------------------------------------------------------------------

def test_run_validation_failure_repair_success(manifest, tmp_template):
    """Attempt 1 passes parse but fails validation; attempt 2 returns valid JSON."""
    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", side_effect=[INVALID_CONTENT, VALID_CONTENT]) as mock_gen:
        result = pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert mock_gen.call_count == 2
    assert out_path.exists()
    # Second call's messages must reference the field error (title is required).
    second_call_messages = mock_gen.call_args_list[1].args[0]
    full_correction = " ".join(m["content"] for m in second_call_messages)
    assert "title" in full_correction


# ---------------------------------------------------------------------------
# Hard fail after repair
# ---------------------------------------------------------------------------

def test_run_repair_still_fails_parse(manifest, tmp_template):
    """Both attempts return unparseable text → ParseError raised."""
    from app.parsers.llm_response_parser import ParseError

    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", side_effect=["not json", "still not json"]):
        with pytest.raises(ParseError, match="after repair"):
            pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert not out_path.exists()


def test_run_repair_still_fails_validation(manifest, tmp_template):
    """Both attempts produce parseable JSON that fails validation → ParseError raised."""
    from app.parsers.llm_response_parser import ParseError

    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", side_effect=[INVALID_CONTENT, INVALID_CONTENT]):
        with pytest.raises(ParseError, match="after repair"):
            pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert not out_path.exists()


# ---------------------------------------------------------------------------
# Truncation-bump
# ---------------------------------------------------------------------------

def test_run_truncation_bump_passes_max_tokens(manifest, tmp_template):
    """Truncated JSON on attempt 1 triggers max_tokens bump on the repair call."""
    from app.config.defaults import OLLAMA_REPAIR_MAX_TOKENS

    out_path = tmp_template / "output.pptx"
    with patch("templates_engine.llm.generate", side_effect=[TRUNCATED_CONTENT, VALID_CONTENT]) as mock_gen:
        pipeline.run(manifest, tmp_template, [{"role": "user", "content": "deck"}], "llama3", out_path)

    assert mock_gen.call_count == 2
    second_call_kwargs = mock_gen.call_args_list[1].kwargs
    assert "max_tokens" in second_call_kwargs, "Repair call must include max_tokens for truncation bump"
    assert second_call_kwargs["max_tokens"] >= OLLAMA_REPAIR_MAX_TOKENS
```

- [ ] **Step 2: Run tests to confirm they fail at import**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_pipeline.py -v
```

Expected: 6 failures with `ImportError: cannot import name 'pipeline' from 'templates_engine'` (or `ModuleNotFoundError`).

---

## Task 7: Implement `pipeline.py` skeleton (without truncation-bump)

**Files:**
- Create: `simplicitor/templates_engine/pipeline.py`

At this stage, implement the full pipeline **except** `_looks_truncated`. The truncation-bump branch calls `_looks_truncated` and passes `max_tokens` to the repair call -- stub it to always return `False` (no bump). Task 9 will replace the stub once the gate in Task 8 is verified.

- [ ] **Step 1: Create `simplicitor/templates_engine/pipeline.py`**

```python
# templates_engine/pipeline.py
# Phase J: Generate-validate-repair-render pipeline.
import json
import logging
from pathlib import Path

from app.config.defaults import OLLAMA_REPAIR_MAX_TOKENS
from app.parsers.llm_response_parser import LlmResponseParser, ParseError
from templates_engine import llm
from templates_engine.manifest import Manifest
from templates_engine.prompt_builder import build_repair_prompt
from templates_engine.render_pptx import render
from templates_engine.validation import format_validation_errors, validate_content

logger = logging.getLogger(__name__)


def _try_parse(raw: str) -> tuple[dict | None, json.JSONDecodeError | None]:
    """Clean and parse raw LLM output as JSON. Never raises.

    Returns:
        (parsed_dict, None) on success.
        (None, json.JSONDecodeError) on failure.
    """
    cleaned = LlmResponseParser.clean(raw)
    try:
        return json.loads(cleaned), None
    except json.JSONDecodeError as exc:
        return None, exc


def _looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool:
    """Return True if the parse failure appears to be caused by truncation.

    NOTE: This stub always returns False. Task 9 (truncation-bump gate) replaces
    this with the real heuristic once done_reason behaviour is verified against Ollama.
    """
    return False  # stub — replaced in Task 9


def run(
    manifest: Manifest,
    template_dir: Path | str,
    messages: list[dict],
    model: str,
    out_path: Path | str,
    client=None,
) -> dict:
    """Run the full generate → validate → (repair) → render pipeline.

    Args:
        manifest: Validated Manifest from load_manifest().
        template_dir: Directory containing manifest.template_file.
        messages: OpenAI-format prompt from build_prompt().
        model: Ollama model name.
        out_path: Destination .pptx path. .pptx suffix appended if absent.
        client: Optional injected OllamaClient (for testing; None uses default).

    Returns:
        {"path": Path, "issues": list[str]} — same shape as render().

    Raises:
        ParseError: Model could not produce valid content after one repair attempt.
        OllamaTimeoutError, OllamaConnectionError, OllamaGenerationError: propagated from llm.generate.
        ManipulationError: propagated from render() on I/O failure or manifest/template mismatch.
        ValueError: propagated from render() on corrupt/missing template.
    """
    # ── Attempt 1 ────────────────────────────────────────────────────────────
    raw1 = llm.generate(messages, model, client=client)
    parsed1, parse_exc1 = _try_parse(raw1)

    if parsed1 is not None:
        ok, result = validate_content(manifest, parsed1)
        if ok:
            return render(manifest, result, out_path, template_dir)
        # Validation failed → build repair prompt with error list
        logger.warning(
            "Content validation failed on attempt 1 (%d error(s)). Attempting repair.",
            len(result),
        )
        repair_msgs = build_repair_prompt(messages, raw1, errors=result)
        repair_max_tokens = None  # validation failures do not trigger token bump

    else:
        # Parse failed → truncation check, repair with parse-failure correction
        cleaned1 = LlmResponseParser.clean(raw1)
        truncated = _looks_truncated(cleaned1, parse_exc1)
        logger.warning(
            "JSON parse failed on attempt 1 (truncated=%s). Attempting repair.",
            truncated,
        )
        repair_max_tokens = (
            max(0, OLLAMA_REPAIR_MAX_TOKENS) if truncated else None
        )
        repair_msgs = build_repair_prompt(messages, raw1, errors=None)

    # ── Attempt 2 (repair) ───────────────────────────────────────────────────
    raw2 = llm.generate(repair_msgs, model, max_tokens=repair_max_tokens, client=client)
    parsed2, parse_exc2 = _try_parse(raw2)

    if parsed2 is None:
        logger.error("JSON parse failed after repair. Giving up.")
        raise ParseError(
            "LLM response could not be parsed as JSON after repair",
            details=str(parse_exc2),
        )

    ok2, result2 = validate_content(manifest, parsed2)
    if not ok2:
        logger.error("Content validation failed after repair. Giving up.")
        raise ParseError(
            "Model returned invalid content after repair",
            details=format_validation_errors(result2),
        )

    return render(manifest, result2, out_path, template_dir)
```

- [ ] **Step 2: Run pipeline tests**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_pipeline.py -v
```

Expected: 5 of 6 tests pass. `test_run_truncation_bump_passes_max_tokens` FAILS because `_looks_truncated` is a stub that always returns False (so `repair_max_tokens` is None, no `max_tokens` kwarg in the second call).

- [ ] **Step 3: Full suite regression check**

```
python -m pytest tests/ -q --ignore=tests/templates_engine/test_pipeline.py
```

Expected: all 522 tests pass (ignoring the known-failing pipeline test for now).

---

## Task 8: Truncation-bump gate verification

**This task must be completed before Task 9. If the gate fails, stop and read the instructions at the end of this task before continuing.**

The truncation-bump strategy assumes that when Ollama cuts output short due to token limits, the response metadata contains `done_reason == "length"`. This task verifies that assumption.

- [ ] **Step 1: Add a temporary debug endpoint to `OllamaClient.chat_completion`**

This is a one-line temporary change. At the very end of `chat_completion` in `simplicitor/app/services/ollama_client.py`, before `return content`, add:

```python
        import logging as _l; _l.getLogger(__name__).warning("done_reason=%r raw_keys=%r", response.json().get("done_reason"), list(response.json().keys()))
```

Resulting in:
```python
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise OllamaGenerationError(
                f"Unexpected response format from Ollama chat completion: {exc}"
            ) from exc

        import logging as _l; _l.getLogger(__name__).warning("done_reason=%r raw_keys=%r", response.json().get("done_reason"), list(response.json().keys()))
        return content
```

- [ ] **Step 2: Import a template and run generate with a short max_tokens to force truncation**

Run from `C:\Repos\simplicitor`. First check if any templates are available:
```
python cli.py list-templates
```

If no templates, you cannot run this gate now. Skip to the fallback note below.

If templates exist, run with a tiny `--model` that you have installed:
```
python -c "
import sys
sys.path.insert(0, 'simplicitor')
from app.services.ollama_client import OllamaClient
import logging
logging.basicConfig(level=logging.WARNING)
c = OllamaClient('http://localhost:11434')
result = c.chat_completion(
    [{'role':'user','content':'Return a JSON object with key a and value 1.'}],
    'llama3',
    max_tokens=5,
)
print('result:', result[:100])
"
```

Run from `C:\Repos`. Watch the WARNING log line for `done_reason`.

- [ ] **Step 3: Evaluate the gate result**

**If `done_reason == "length"` appears in the log:**
The truncation-bump strategy is correct. Remove the temporary debug line from `chat_completion`. Proceed to Task 9.

**If `done_reason` is missing, `"stop"`, or something else:**
`max_tokens` is not the constraint. The token budget does not control truncation on this Ollama endpoint configuration.
1. Remove the temporary debug line from `chat_completion`.
2. Add to `NOTES.md` under Known follow-ups:
   ```
   3. **Truncation-bump strategy unverified (Phase J gate).**
      `done_reason` on `/v1/chat/completions` did not return "length" when max_tokens was hit.
      `_looks_truncated` stub in pipeline.py returns False. The repair attempt still fires
      (via parse failure path) but without a token bump. Revisit if truncation is observed
      in production: strategy may need prompt-shrink or schema-chunking instead.
   ```
3. Keep `_looks_truncated` as the stub (always returns False). The `test_run_truncation_bump_passes_max_tokens` test will continue to fail — that is the correct signal that the gate was not verified.
4. **Surface to user before continuing.** Do not proceed to Task 9 if the gate failed.

**If Ollama is not running or no templates are available:**
Document this in NOTES.md as above. Proceed to Task 10 with `_looks_truncated` as the stub. The truncation bump test will fail as a permanent reminder.

---

## Task 9: Implement `_looks_truncated` + truncation-bump branch

**Only run this task if Task 8's gate passed (done_reason == "length").**

**Files:**
- Modify: `simplicitor/templates_engine/pipeline.py`

- [ ] **Step 1: Replace the `_looks_truncated` stub with the real heuristic**

In `simplicitor/templates_engine/pipeline.py`, replace the stub function:

```python
def _looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool:
    """Return True if the parse failure appears to be caused by truncation.

    NOTE: This stub always returns False. Task 9 (truncation-bump gate) replaces
    this with the real heuristic once done_reason behaviour is verified against Ollama.
    """
    return False  # stub — replaced in Task 9
```

With the real implementation:

```python
def _looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool:
    """Return True if the parse failure appears to be caused by truncation.

    Two signals, either sufficient:
    1. Position-based: the JSONDecodeError position lands within 10 chars of the end.
    2. Structural: a depth count of { [ vs } ] ends positive (more openers than closers).
    """
    # Signal 1: error near end of string
    if exc.pos is not None and exc.pos >= len(cleaned) - 10:
        return True
    # Signal 2: unbalanced openers
    depth = 0
    for ch in cleaned:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return depth > 0
```

- [ ] **Step 2: Run all pipeline tests**

Run from `C:\Repos`:
```
python -m pytest tests/templates_engine/test_pipeline.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 3: Full suite regression check**

```
python -m pytest tests/ -q
```

Expected: all 528 tests pass (516 original + 2 chat_completion + 1 llm + 3 prompt_builder + 6 pipeline).

---

## Task 10: CLI changes — `--out`, pipeline wiring, except tuple

**Files:**
- Modify: `simplicitor/cli.py`

- [ ] **Step 1: Add `--out` to the `generate` subparser**

In `simplicitor/cli.py`, find:
```python
    generate_p.add_argument("--dry-run", action="store_true", dest="dry_run",
                            help="Print assembled prompt without calling the model.")
```

Add directly after it (before `return parser`):
```python
    generate_p.add_argument(
        "--out", default=None,
        help="Output .pptx path (required unless --dry-run).",
    )
```

- [ ] **Step 2: Add handler-level `--out` validation**

In `_cmd_generate`, find the block that starts with:
```python
        if args.dry_run:
```

Insert this check immediately before that block (after `messages = build_prompt(...)` and before `if args.dry_run:`):

```python
        if not args.dry_run and not args.out:
            print(
                "Error: --out is required. Use --dry-run to inspect the prompt without generating a file.",
                file=sys.stderr,
            )
            return 1

```

- [ ] **Step 3: Replace the scaffolding block with the pipeline call**

Find the scaffolding block:
```python
        # Phase I: prints raw model JSON to stdout as scaffolding.
        # Phase J replaces this with the full render + repair loop + --out path.
        llm.preflight(args.model)
        raw = llm.generate(messages, args.model)
        print(raw)
        return 0
```

Replace it with:
```python
        from app.parsers.llm_response_parser import ParseError
        from app.services.file_manipulator import ManipulationError
        from templates_engine import pipeline

        llm.preflight(args.model)
        result = pipeline.run(manifest, match["path"], messages, args.model, args.out)
        print(result["path"])
        for issue in result["issues"]:
            print(f"Warning: {issue}")
        return 0
```

- [ ] **Step 4: Extend the except tuple**

Find:
```python
    except (ValueError, OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError) as exc:
```

Replace with:
```python
    except (ValueError, ParseError, ManipulationError,
            OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError) as exc:
```

Where `ParseError` and `ManipulationError` were imported inside the `try` block in Step 3.

- [ ] **Step 5: Verify `generate --help` output**

Run from `C:\Repos\simplicitor`:
```
python cli.py generate --help
```

Expected output includes `--out OUTPUT .pptx path (required unless --dry-run)`.

- [ ] **Step 6: Verify `--out` validation error**

Run from `C:\Repos\simplicitor`:
```
python cli.py generate --template nonexistent --request "test" 2>&1; echo "exit $?"
```

Expected: `Error: --out is required. Use --dry-run to inspect the prompt without generating a file.` (before template lookup, since `--out` check fires first) — actually `--out` check fires after `build_prompt`, so the error about template not found fires first. That's fine.

More precisely, verify `--out` validation fires when a real template exists:
```
python cli.py generate --template some_real_template --request "test" 2>&1 | head -1
```
Expected (if template exists): `Error: --out is required...`

If no templates exist, skip this smoke test — the argparser will surface the `--template` error first.

- [ ] **Step 7: Full suite regression check**

Run from `C:\Repos`:
```
python -m pytest tests/ -q
```

Expected: all 528 tests pass.

---

## Task 11: Final regression + commit

- [ ] **Step 1: Run full test suite one last time**

Run from `C:\Repos`:
```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass. If any fail, fix before committing.

- [ ] **Step 2: Check working tree**

Run from `C:\Repos`:
```
git status
git diff --stat HEAD
```

Expected changed files:
- `simplicitor/app/config/defaults.py`
- `simplicitor/app/parsers/llm_response_parser.py`
- `simplicitor/app/workers/generate_worker.py`
- `simplicitor/app/services/ollama_client.py`
- `simplicitor/templates_engine/llm.py`
- `simplicitor/templates_engine/prompt_builder.py`
- `simplicitor/templates_engine/pipeline.py` (new)
- `simplicitor/cli.py`
- `tests/test_ollama_client.py`
- `tests/templates_engine/test_llm.py`
- `tests/templates_engine/test_prompt_builder.py`
- `tests/templates_engine/test_pipeline.py` (new)
- `docs/superpowers/plans/2026-06-02-phase-j-pipeline.md` (new, this file)
- `docs/superpowers/specs/2026-06-02-phase-j-pipeline-design.md` (already committed)

- [ ] **Step 3: Stage and commit**

Run from `C:\Repos`:
```bash
git add \
  simplicitor/app/config/defaults.py \
  simplicitor/app/parsers/llm_response_parser.py \
  simplicitor/app/workers/generate_worker.py \
  simplicitor/app/services/ollama_client.py \
  simplicitor/templates_engine/llm.py \
  simplicitor/templates_engine/prompt_builder.py \
  simplicitor/templates_engine/pipeline.py \
  simplicitor/cli.py \
  tests/test_ollama_client.py \
  tests/templates_engine/test_llm.py \
  tests/templates_engine/test_prompt_builder.py \
  tests/templates_engine/test_pipeline.py \
  docs/superpowers/plans/2026-06-02-phase-j-pipeline.md

git commit -m "feat(phase-j): generate-validate-repair-render pipeline"
```

- [ ] **Step 4: Confirm clean state**

```
git status
git log --oneline -3
```

Expected: working tree clean, new commit at HEAD.

---

## Self-review checklist

- [x] Spec section 2 (`_clean` rename): Task 1, steps 1-3
- [x] Spec section 3 (`OLLAMA_REPAIR_MAX_TOKENS`): Task 2
- [x] Spec section 4 (`chat_completion` max_tokens): Task 3
- [x] Spec section 5 (`llm.generate` max_tokens): Task 4
- [x] Spec section 6 (`build_repair_prompt`): Task 5
- [x] Spec section 7-9 (`pipeline.run` public API + helpers + flow): Tasks 6-7
- [x] Spec section 10 (truncation-bump gate): Task 8
- [x] Spec section 10 (`_looks_truncated` real implementation): Task 9
- [x] Spec section 11-12 (CLI `--out`, scaffolding replacement, except tuple): Task 10
- [x] Spec section 13 (all tests): Tasks 3-6 and the pipeline tests cover all 6+3+2+1 items
- [x] Type consistency: `build_repair_prompt` returns `list[dict]` (Task 5 → used in Task 7), `_try_parse` returns `tuple[dict|None, json.JSONDecodeError|None]` (Task 7 → used throughout Task 7)
- [x] `test_generate_returns_content_string` existing assertion (`assert_called_once_with(messages, "llama3", 0.3)`) preserved: Task 4 only adds kwargs when `max_tokens is not None`
- [x] No placeholders: every step contains actual code or exact commands
