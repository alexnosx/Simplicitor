# Phase I: Prompt Builder + Ollama Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `prompt_builder.build_prompt`, `OllamaClient.chat_completion`, and `llm.generate/preflight`, wired to a `simplicitor generate` CLI command with `--dry-run` support.

**Architecture:** `OllamaClient` gains a `chat_completion()` method (Option B — reuses existing HTTP error mapping). `llm.py` is a module-level facade with injectable client for tests. `prompt_builder.py` derives a JSON schema from the manifest and assembles a 4-message chat prompt with a one-shot example.

**Tech Stack:** `requests`, `python-pptx`, `pydantic`, `pytest`, existing `OllamaConnectionError/TimeoutError/GenerationError` from `app.services.ollama_client`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `simplicitor/app/config/defaults.py` | Modify | Add `OLLAMA_CHAT_COMPLETIONS_ENDPOINT` constant |
| `simplicitor/app/services/ollama_client.py` | Modify | Add `chat_completion()` method |
| `simplicitor/templates_engine/prompt_builder.py` | Replace stub | `build_prompt(manifest, user_request, source_text)` |
| `simplicitor/templates_engine/llm.py` | Replace stub | `_client()`, `preflight()`, `generate()` |
| `simplicitor/cli.py` | Modify | Add `_cmd_generate`, `generate` subparser, dispatch |
| `tests/test_ollama_client.py` | Modify | Add 5 `chat_completion` tests |
| `tests/templates_engine/test_prompt_builder.py` | Create | 7 prompt builder tests |
| `tests/templates_engine/test_llm.py` | Create | 5 llm module tests |

---

## Task 1: Add `OLLAMA_CHAT_COMPLETIONS_ENDPOINT` to defaults.py

**Files:**
- Modify: `simplicitor/app/config/defaults.py`

- [ ] **Step 1: Read defaults.py and add the constant**

Read `simplicitor/app/config/defaults.py`. Find the block containing `OLLAMA_CHAT_ENDPOINT`. Add directly after it:

```python
OLLAMA_CHAT_COMPLETIONS_ENDPOINT = "/v1/chat/completions"
```

- [ ] **Step 2: Verify the import works**

```
python -c "from app.config.defaults import OLLAMA_CHAT_COMPLETIONS_ENDPOINT; print(OLLAMA_CHAT_COMPLETIONS_ENDPOINT)"
```

Run from `C:\Repos\simplicitor`. Expected: `/v1/chat/completions`

- [ ] **Step 3: Run existing tests to confirm no regression**

```
python -m pytest tests/ -q --ignore=tests/templates_engine
```

Run from `C:\Repos`. Expected: all pass.

---

## Task 2: Add `chat_completion()` to `OllamaClient` + tests

**Files:**
- Modify: `simplicitor/app/services/ollama_client.py`
- Modify: `tests/test_ollama_client.py`

- [ ] **Step 1: Write failing tests first**

Read `tests/test_ollama_client.py`. Append a new `TestChatCompletion` class:

```python
class TestChatCompletion:
    MESSAGES = [
        {"role": "system", "content": "Return JSON only."},
        {"role": "user", "content": "Make a deck about dogs."},
    ]

    def test_chat_completion_returns_content_string(self):
        client = OllamaClient(BASE_URL)
        mock_resp = _mock_response(200, {
            "choices": [{"message": {"content": '{"slides": []}'}}]
        })
        with patch("requests.post", return_value=mock_resp):
            result = client.chat_completion(self.MESSAGES, "llama3")
        assert result == '{"slides": []}'

    def test_chat_completion_timeout_raises_ollama_timeout_error(self):
        from app.services.ollama_client import OllamaTimeoutError
        client = OllamaClient(BASE_URL)
        with patch("requests.post", side_effect=requests.Timeout("timed out")):
            with pytest.raises(OllamaTimeoutError):
                client.chat_completion(self.MESSAGES, "llama3")

    def test_chat_completion_connection_error_raises_ollama_connection_error(self):
        client = OllamaClient(BASE_URL)
        with patch("requests.post", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(OllamaConnectionError):
                client.chat_completion(self.MESSAGES, "llama3")

    def test_chat_completion_non_200_raises_ollama_generation_error(self):
        client = OllamaClient(BASE_URL)
        mock_resp = _mock_response(500, {})
        mock_resp.text = "Internal Server Error"
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(OllamaGenerationError):
                client.chat_completion(self.MESSAGES, "llama3")

    def test_chat_completion_missing_choices_raises_ollama_generation_error(self):
        client = OllamaClient(BASE_URL)
        mock_resp = _mock_response(200, {"model": "llama3"})  # no "choices" key
        with patch("requests.post", return_value=mock_resp):
            with pytest.raises(OllamaGenerationError):
                client.chat_completion(self.MESSAGES, "llama3")
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/test_ollama_client.py::TestChatCompletion -v
```

Expected: 5 failures with `AttributeError` (method does not exist yet).

- [ ] **Step 3: Implement `chat_completion()` in OllamaClient**

Read `simplicitor/app/services/ollama_client.py`. Add the method after `generate()`, following the same error-mapping pattern:

```python
def chat_completion(
    self,
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    timeout: int | None = None,
) -> str:
    """Send a chat completion request to ``/v1/chat/completions`` and return the content string.

    Args:
        messages: List of message dicts with "role" and "content" keys.
        model: The Ollama model name to use.
        temperature: Sampling temperature (default 0.3 for structured output).
        timeout: Request timeout in seconds. Defaults to ``OLLAMA_TIMEOUT_S``.

    Returns:
        The ``choices[0].message.content`` string from the response.

    Raises:
        OllamaTimeoutError: If the request exceeds the timeout.
        OllamaConnectionError: If the HTTP request fails for any other network reason.
        OllamaGenerationError: If the server returns a non-200 status or the response
            does not contain ``choices[0].message.content``.
    """
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    effective_timeout = timeout if timeout is not None else OLLAMA_TIMEOUT_S

    try:
        response = requests.post(
            f"{self._base_url}{OLLAMA_CHAT_COMPLETIONS_ENDPOINT}",
            json=body,
            timeout=effective_timeout,
        )
    except requests.Timeout as exc:
        raise OllamaTimeoutError(str(exc)) from exc
    except requests.RequestException as exc:
        raise OllamaConnectionError(str(exc)) from exc

    if response.status_code != 200:
        raise OllamaGenerationError(
            f"Ollama returned status {response.status_code}: {response.text}"
        )

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise OllamaGenerationError(
            f"Unexpected response format from Ollama chat completion: {exc}"
        ) from exc

    return content
```

Also add the import for `OLLAMA_CHAT_COMPLETIONS_ENDPOINT` in the existing imports block at the top of the file.

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/test_ollama_client.py::TestChatCompletion -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full test suite to confirm no regression**

```
python -m pytest tests/ -q --ignore=tests/templates_engine
```

Expected: all pass.

---

## Task 3: Implement `prompt_builder.py` + tests

**Files:**
- Replace stub: `simplicitor/templates_engine/prompt_builder.py`
- Create: `tests/templates_engine/test_prompt_builder.py`

- [ ] **Step 1: Write failing tests**

Create `tests/templates_engine/test_prompt_builder.py`:

```python
# tests/templates_engine/test_prompt_builder.py
# Phase I: Tests for the prompt builder.
import pytest
from templates_engine.manifest import load_manifest
from templates_engine.prompt_builder import build_prompt
from pathlib import Path

FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "render_manifest.yaml"


@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


def test_build_prompt_returns_four_messages(manifest):
    messages = build_prompt(manifest, "Make a deck about dogs.")
    assert len(messages) == 4
    assert all("role" in m and "content" in m for m in messages)


def test_build_prompt_system_message_is_first(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    assert messages[0]["role"] == "system"


def test_build_prompt_system_message_contains_all_slide_types(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    system = messages[0]["content"]
    for slide_type in manifest.slide_types:
        assert slide_type in system


def test_build_prompt_system_message_contains_field_names(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    system = messages[0]["content"]
    # title_slide has fields: title, subtitle
    assert "title" in system
    assert "subtitle" in system


def test_build_prompt_contains_one_shot_exchange(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    roles = [m["role"] for m in messages]
    # user, assistant, then user again
    assert roles == ["system", "user", "assistant", "user"]


def test_build_prompt_last_message_contains_user_request(manifest):
    request = "Build a deck about quarterly results"
    messages = build_prompt(manifest, request)
    assert request in messages[-1]["content"]


def test_build_prompt_includes_source_text_when_provided(manifest):
    messages = build_prompt(manifest, "Summarise this.", source_text="Q3 revenue was $4.2M.")
    assert "Q3 revenue was $4.2M." in messages[-1]["content"]


def test_build_prompt_omits_source_section_when_none(manifest):
    messages = build_prompt(manifest, "Make a deck.", source_text=None)
    assert "Source content:" not in messages[-1]["content"]
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/templates_engine/test_prompt_builder.py -v
```

Expected: 8 failures (`NotImplementedError`).

- [ ] **Step 3: Implement `build_prompt()`**

Replace the stub at `simplicitor/templates_engine/prompt_builder.py`:

```python
# templates_engine/prompt_builder.py
# Phase I: Prompt builder — assembles chat messages from a manifest and user request.
import json
import logging
from templates_engine.manifest import Manifest

logger = logging.getLogger(__name__)


def _schema_from_manifest(manifest: Manifest) -> str:
    """Derive a human-readable schema block from the manifest's slide_types."""
    lines = ['SCHEMA — return a JSON object exactly matching this structure:',
             '{"slides": [<one object per slide>]}',
             '',
             'Each slide object:',
             '  {"type": "<slide_type>", "fields": {<field_name>: <value>}}',
             '',
             'SLIDE TYPES:']
    for type_name, slide_def in manifest.slide_types.items():
        lines.append(f"  {type_name}:")
        for field in slide_def.fields:
            constraints = []
            if field.required:
                constraints.append("required")
            else:
                constraints.append("optional")
            if field.kind == "text":
                constraints.append("string")
                if field.max_chars is not None:
                    constraints.append(f"max {field.max_chars} chars")
            elif field.kind == "bullets":
                constraints.append("array of strings")
                if field.max_items is not None:
                    constraints.append(f"max {field.max_items} items")
            elif field.kind == "image":
                constraints.append("file path string")
            lines.append(f"    - {field.name}: {', '.join(constraints)}")
    return "\n".join(lines)


def _one_shot_example(manifest: Manifest) -> tuple[str, str]:
    """Return a synthetic (user_message, assistant_response) example pair."""
    user = "Create a 2-slide overview deck."

    # Build a minimal example using the first two slide types in the manifest.
    slide_types = list(manifest.slide_types.items())
    example_slides = []

    for type_name, slide_def in slide_types[:2]:
        fields: dict = {}
        for field in slide_def.fields:
            if not field.required:
                continue
            if field.kind == "text":
                fields[field.name] = f"Example {field.name.replace('_', ' ').title()}"
            elif field.kind == "bullets":
                fields[field.name] = ["First point", "Second point"]
            elif field.kind == "image":
                fields[field.name] = "path/to/image.png"
        example_slides.append({"type": type_name, "fields": fields})

    assistant = json.dumps({"slides": example_slides}, separators=(", ", ": "))
    return user, assistant


def build_prompt(
    manifest: Manifest,
    user_request: str,
    source_text: str | None = None,
) -> list[dict]:
    """Assemble a 4-message chat prompt from a manifest and user request.

    Returns messages in OpenAI chat format:
        [system, user (one-shot), assistant (one-shot), user (request)]

    The system message contains a JSON-only instruction and the full schema
    derived from the manifest. The one-shot example shows the expected output
    structure using synthetic content. The final user message contains the
    actual request and, if provided, the source text.

    Args:
        manifest: Validated Manifest describing available slide types and fields.
        user_request: The user's natural language instruction.
        source_text: Optional source document content to include in the request.
            Never logged (privacy rule).

    Returns:
        List of 4 message dicts with 'role' and 'content' keys.
    """
    system_content = "\n".join([
        "You are a JSON generator for a PowerPoint presentation tool.",
        "Return ONLY valid JSON. No markdown fences, no explanation, no preamble.",
        "",
        _schema_from_manifest(manifest),
        "",
        "RULES:",
        '- "bullets" fields must be arrays of strings.',
        "- Omit optional fields if not needed.",
        "- Do not include keys not defined in the schema.",
        "- Return nothing except the JSON object.",
    ])

    one_shot_user, one_shot_assistant = _one_shot_example(manifest)

    user_content = f"Request: {user_request}"
    if source_text is not None:
        user_content += f"\n\nSource content:\n{source_text}"

    return [
        {"role": "system",    "content": system_content},
        {"role": "user",      "content": one_shot_user},
        {"role": "assistant", "content": one_shot_assistant},
        {"role": "user",      "content": user_content},
    ]
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/templates_engine/test_prompt_builder.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Run full templates_engine suite to confirm no regression**

```
python -m pytest tests/templates_engine/ -q
```

Expected: all pass (159 + 8 new).

---

## Task 4: Implement `llm.py` + tests

**Files:**
- Replace stub: `simplicitor/templates_engine/llm.py`
- Create: `tests/templates_engine/test_llm.py`

- [ ] **Step 1: Write failing tests**

Create `tests/templates_engine/test_llm.py`:

```python
# tests/templates_engine/test_llm.py
# Phase I: Tests for the llm module-level facade.
import pytest
from unittest.mock import MagicMock
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaTimeoutError,
)
from templates_engine.llm import generate, preflight


def _mock_client(models=None, chat_return=None, raises=None):
    """Build a minimal OllamaClient mock for injection."""
    client = MagicMock(spec=OllamaClient)
    if raises is not None:
        client.get_models.side_effect = raises
        client.chat_completion.side_effect = raises
    else:
        client.get_models.return_value = models or []
        client.chat_completion.return_value = chat_return or '{"slides": []}'
    return client


def test_preflight_raises_connection_error_when_ollama_unreachable():
    mock = _mock_client(raises=OllamaConnectionError("refused"))
    with pytest.raises(OllamaConnectionError, match=r"[Oo]llama"):
        preflight("llama3", client=mock)


def test_preflight_raises_generation_error_when_model_not_available():
    mock = _mock_client(models=["other_model:latest"])
    with pytest.raises(OllamaGenerationError, match=r"llama3"):
        preflight("llama3", client=mock)


def test_preflight_succeeds_when_model_available():
    mock = _mock_client(models=["llama3:latest", "llama3"])
    preflight("llama3", client=mock)  # must not raise


def test_generate_returns_content_string():
    mock = _mock_client(chat_return='{"slides": []}')
    messages = [{"role": "user", "content": "Make a deck."}]
    result = generate(messages, "llama3", client=mock)
    assert result == '{"slides": []}'
    mock.chat_completion.assert_called_once_with(messages, "llama3", 0.3)


def test_generate_timeout_propagates():
    mock = _mock_client(raises=OllamaTimeoutError("timed out"))
    with pytest.raises(OllamaTimeoutError):
        generate([{"role": "user", "content": "x"}], "llama3", client=mock)
```

- [ ] **Step 2: Run tests to confirm they fail**

```
python -m pytest tests/templates_engine/test_llm.py -v
```

Expected: 5 failures (`NotImplementedError`).

- [ ] **Step 3: Implement `llm.py`**

Replace the stub at `simplicitor/templates_engine/llm.py`:

```python
# templates_engine/llm.py
# Phase I: Module-level facade over OllamaClient for the chat-completions path.
import logging
from app.config.defaults import OLLAMA_BASE_URL
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
)

logger = logging.getLogger(__name__)


def _client(client: OllamaClient | None = None) -> OllamaClient:
    """Return the passed client if given; otherwise construct a default OllamaClient.

    The optional arg exists for test injection — pass a mock to avoid real HTTP calls.
    In production, the default client reads OLLAMA_BASE_URL from app.config.defaults.
    """
    if client is not None:
        return client
    return OllamaClient(base_url=OLLAMA_BASE_URL)


def preflight(model: str, client: OllamaClient | None = None) -> None:
    """Check Ollama is reachable and the model is available.

    Raises:
        OllamaConnectionError: If Ollama is unreachable, with remediation hint.
        OllamaGenerationError: If the model is not in the installed list,
            with remediation hint.
    """
    c = _client(client)
    try:
        models = c.get_models()
    except OllamaConnectionError as exc:
        raise OllamaConnectionError(
            f"Ollama is not responding. Check that Ollama is running. ({exc})"
        ) from exc

    # Check for exact name match OR name-without-tag match (e.g. "llama3" matches "llama3:latest").
    if not any(m == model or m.startswith(f"{model}:") for m in models):
        raise OllamaGenerationError(
            f"Model '{model}' is not available in Ollama. "
            f"Run 'ollama pull {model}' to download it."
        )


def generate(
    messages: list[dict],
    model: str,
    temperature: float = 0.3,
    client: OllamaClient | None = None,
) -> str:
    """Call Ollama chat completions and return the response content string.

    Args:
        messages: OpenAI-format message list.
        model: Ollama model name.
        temperature: Sampling temperature (default 0.3 for structured output).
        client: Optional injected OllamaClient for testing.

    Returns:
        The raw content string from the model (expected to be JSON).

    Raises:
        OllamaTimeoutError: If the request times out.
        OllamaConnectionError: If the request fails at the network level.
        OllamaGenerationError: If the response is malformed or non-200.
    """
    return _client(client).chat_completion(messages, model, temperature)
```

- [ ] **Step 4: Run tests to confirm they pass**

```
python -m pytest tests/templates_engine/test_llm.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run full suite to confirm no regression**

```
python -m pytest tests/ -q
```

Expected: all pass.

---

## Task 5: CLI `generate` command

**Files:**
- Modify: `simplicitor/cli.py`

- [ ] **Step 1: Add `_cmd_generate` after `_cmd_render` (before `_build_parser`)**

Read `simplicitor/cli.py`. Add the following function after `_cmd_render`:

```python
def _cmd_generate(args: argparse.Namespace) -> int:
    from app.services.ollama_client import (
        OllamaConnectionError,
        OllamaGenerationError,
        OllamaTimeoutError,
    )
    from templates_engine.config import list_templates
    from templates_engine.manifest import load_manifest
    from templates_engine.prompt_builder import build_prompt
    from templates_engine import llm

    try:
        templates = list_templates()
        match = next((t for t in templates if t["name"] == args.template), None)
        if match is None:
            raise ValueError(f"Template '{args.template}' not found.")

        manifest = load_manifest(match["manifest_path"])

        source_text = None
        if args.source:
            source_path = Path(args.source)
            try:
                source_text = source_path.read_text(encoding="utf-8")
            except OSError:
                raise ValueError(f"Source file not found or not readable: {source_path}")

        messages = build_prompt(manifest, args.request, source_text)

        if args.dry_run:
            labels = ["SYSTEM", "USER (one-shot example)", "ASSISTANT (one-shot response)", "USER (request)"]
            for label, msg in zip(labels, messages):
                print(f"=== {label} ===")
                print(msg["content"])
                print()
            return 0

        # Phase I: prints raw model JSON to stdout as scaffolding.
        # Phase J replaces this with the full render + repair loop + --out path.
        llm.preflight(args.model)
        raw = llm.generate(messages, args.model)
        print(raw)
        return 0

    except (ValueError, OllamaConnectionError, OllamaTimeoutError, OllamaGenerationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
```

- [ ] **Step 2: Add generate subparser in `_build_parser` after the render block**

```python
    generate_p = sub.add_parser("generate", help="Build and optionally send a prompt from a template.")
    generate_p.add_argument("--template", required=True, help="Template name.")
    generate_p.add_argument("--request", required=True, help="User request text.")
    generate_p.add_argument("--source", default=None, help="Optional source file path.")
    generate_p.add_argument("--model", default="llama3", help="Ollama model name (default: llama3).")
    generate_p.add_argument("--dry-run", action="store_true", dest="dry_run",
                            help="Print assembled prompt without calling the model.")
```

- [ ] **Step 3: Add dispatch in `main` after the render block**

```python
    if args.command == "generate":
        return _cmd_generate(args)
```

- [ ] **Step 4: Verify the generate help works**

```
python cli.py generate --help
```

Run from `C:\Repos\simplicitor`. Expected output includes `--template`, `--request`, `--source`, `--model`, `--dry-run`.

- [ ] **Step 5: Smoke test `--dry-run`**

This requires a user-imported template to be present. If `list-templates` shows at least one template, run:

```
python cli.py generate --template <name> --request "Create a test deck" --dry-run
```

Expected: 4 sections printed (`=== SYSTEM ===`, etc.), exit 0.

If no templates exist yet, skip this step and note in the report. Done Check will be completed in Phase L when built-in templates land.

- [ ] **Step 6: Run full test suite to confirm no regression**

```
python -m pytest tests/ -q
```

Expected: all pass.

---

## Task 6: Commit

- [ ] **Step 1: Stage all Phase I files**

```bash
git add simplicitor/app/config/defaults.py \
        simplicitor/app/services/ollama_client.py \
        simplicitor/templates_engine/prompt_builder.py \
        simplicitor/templates_engine/llm.py \
        simplicitor/cli.py \
        simplicitor/templates_engine/NOTES.md \
        tests/test_ollama_client.py \
        tests/templates_engine/test_prompt_builder.py \
        tests/templates_engine/test_llm.py \
        docs/superpowers/specs/2026-06-01-phase-i-prompt-builder-design.md \
        docs/superpowers/plans/2026-06-01-phase-i-prompt-builder.md
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: prompt builder, ollama client, and model-failure handling"
```

- [ ] **Step 3: Confirm clean state**

```
git status
git log --oneline -3
```

Expected: working tree clean, new commit at HEAD.

---

## Self-review checklist

- [x] **Spec coverage:**
  - `build_prompt()` ✓ (Task 3)
  - `llm.generate()` + `llm.preflight()` ✓ (Task 4)
  - `OllamaClient.chat_completion()` ✓ (Task 2)
  - All 4 error modes (unreachable, model not available, timeout, connection dropped) ✓ (Tasks 2, 4)
  - `--dry-run` readable layout ✓ (Task 5)
  - Configurable base URL / model ✓ (Task 4 — `OLLAMA_BASE_URL` from defaults; `--model` arg on CLI)
- [x] **No placeholders:** All code blocks complete.
- [x] **Type consistency:** `build_prompt` returns `list[dict]`, `generate` returns `str`, `preflight` returns `None` (raises on failure). `chat_completion` follows the same return type as `generate()`.
- [x] **Injectable client:** `preflight` and `generate` both accept optional `client` arg passed to `_client()`.
- [x] **Privacy:** `source_text` and `user_request` never logged (passed directly to messages, not through logger).
- [x] **Known follow-ups:** Both persisted in NOTES.md "Known follow-ups" section.
