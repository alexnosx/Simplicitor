# templates_engine/pipeline.py
# Phase J: Generate-validate-repair-render pipeline.
import json
import logging
from collections.abc import Callable
from pathlib import Path

from app.config.defaults import OLLAMA_REPAIR_MAX_TOKENS, OLLAMA_TEMPLATE_TIMEOUT_S
from app.parsers.llm_response_parser import LlmResponseParser, ParseError
from templates_engine import llm
from templates_engine.manifest import Manifest
from templates_engine.prompt_builder import build_repair_prompt
from templates_engine.render_pptx import render
from templates_engine.validation import format_validation_errors, validate_content

logger = logging.getLogger(__name__)


def _try_parse(raw: str) -> tuple[str, dict | None, json.JSONDecodeError | None]:
    """Clean raw LLM output and attempt to parse it as a JSON object. Never raises.

    A degenerate model can emit valid JSON that is not an object ("null", a list,
    a bare scalar). That is a parse failure for our purposes: a synthetic
    JSONDecodeError (pos=0, so _looks_truncated reads it as malformed-in-shape,
    not truncated) routes it through the repair loop.

    Returns:
        (cleaned_text, parsed_dict, None) on success.
        (cleaned_text, None, json.JSONDecodeError) on failure.
    """
    cleaned = LlmResponseParser.clean(raw)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return cleaned, None, exc
    if not isinstance(parsed, dict):
        exc = json.JSONDecodeError(
            f"Expected JSON object at top level, got {type(parsed).__name__}",
            cleaned,
            0,
        )
        return cleaned, None, exc
    return cleaned, parsed, None


def _looks_truncated(cleaned: str, exc: json.JSONDecodeError) -> bool:
    """Return True if the parse failure appears to be caused by truncation.

    Two signals, either sufficient:
    1. Position-based: the JSONDecodeError position lands within 10 chars of the end.
    2. Structural: a depth count of { [ vs } ] ends positive (more openers than closers).
    """
    if exc.pos is not None and len(cleaned) >= 10 and exc.pos >= len(cleaned) - 10:
        return True
    depth = 0
    for ch in cleaned:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
    return depth > 0


def generate_content(
    manifest: Manifest,
    messages: list[dict],
    model: str,
    client=None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Run the generate -> validate -> (repair) loop and return validated content.

    Returns the validated content dict {"slides": [...]}. Does NOT render.

    Args:
        manifest: Validated Manifest from load_manifest().
        messages: OpenAI-format prompt from build_prompt().
        model: Ollama model name.
        client: Optional injected OllamaClient (None uses default).
        progress: Optional callback invoked with phase labels
            ("generating", "validating", "repairing"). Invoked on the calling thread.
            On a clean first attempt only "generating" and "validating" are emitted;
            "repairing" and a second "validating" appear only when a repair attempt runs.

    Raises:
        ParseError: Model could not produce valid content after one repair attempt.
            A post-repair *validation* failure (parseable JSON that still fails the
            manifest) is also raised as ParseError, with a message naming the schema
            cause ("failed schema validation after repair"). See NOTES.md follow-up #4.
        OllamaTimeoutError, OllamaConnectionError, OllamaGenerationError: from llm.generate.
    """
    def _emit(label: str) -> None:
        if progress is not None:
            progress(label)

    # -- Attempt 1 ------------------------------------------------------------
    # Templated generation requests a richer multi-slide JSON deck; on slow local
    # models that exceeds Ollama's default output budget and the global 60s HTTP
    # timeout. Pass an explicit floor for both on attempt 1 to avoid silent
    # truncation and wall-time errors before the repair loop even runs. Opt out
    # of Ollama's grammar-constrained JSON mode (json_mode=False); the prompt
    # instructs the model to return JSON only, and constrained decoding has been
    # observed to degenerate gemma4-class models into dead-end token streams.
    _emit("generating")
    raw1 = llm.generate(
        messages,
        model,
        max_tokens=OLLAMA_REPAIR_MAX_TOKENS,
        timeout=OLLAMA_TEMPLATE_TIMEOUT_S,
        json_mode=False,
        client=client,
    )
    cleaned1, parsed1, parse_exc1 = _try_parse(raw1)

    if parsed1 is not None:
        _emit("validating")
        ok, result = validate_content(manifest, parsed1)
        if ok:
            return result
        logger.warning(
            "Content validation failed on attempt 1 (%d error(s)). Attempting repair.",
            len(result),
        )
        repair_msgs = build_repair_prompt(messages, raw1, errors=result)
        repair_max_tokens = None  # validation failures do not trigger token bump
    else:
        truncated = _looks_truncated(cleaned1, parse_exc1)
        logger.warning(
            "JSON parse failed on attempt 1 (truncated=%s). Attempting repair.",
            truncated,
        )
        repair_max_tokens = OLLAMA_REPAIR_MAX_TOKENS if truncated else None
        repair_msgs = build_repair_prompt(messages, raw1, errors=None)

    # -- Attempt 2 (repair) ---------------------------------------------------
    _emit("repairing")
    raw2 = llm.generate(
        repair_msgs,
        model,
        max_tokens=repair_max_tokens,
        timeout=OLLAMA_TEMPLATE_TIMEOUT_S,
        json_mode=False,
        client=client,
    )
    _, parsed2, parse_exc2 = _try_parse(raw2)

    if parsed2 is None:
        logger.error("JSON parse failed after repair. Giving up.")
        raise ParseError(
            "LLM response could not be parsed as JSON after repair",
            details=str(parse_exc2),
        )

    _emit("validating")
    ok2, result2 = validate_content(manifest, parsed2)
    if not ok2:
        logger.error(
            "Content validation failed after repair. Giving up. Errors: %s",
            "; ".join(result2),
        )
        raise ParseError(
            "Model returned content that failed schema validation after repair",
            details=format_validation_errors(result2),
        )

    return result2


def run(
    manifest: Manifest,
    template_dir: Path | str,
    messages: list[dict],
    model: str,
    out_path: Path | str,
    client=None,
) -> dict:
    """Run the full generate -> validate -> (repair) -> render pipeline.

    Args:
        manifest: Validated Manifest from load_manifest().
        template_dir: Directory containing manifest.template_file.
        messages: OpenAI-format prompt from build_prompt().
        model: Ollama model name.
        out_path: Destination .pptx path. .pptx suffix appended if absent.
        client: Optional injected OllamaClient (for testing; None uses default).

    Returns:
        {"path": Path, "issues": list[str]} - same shape as render().

    Raises:
        ParseError: Model could not produce valid content after one repair attempt.
        OllamaTimeoutError, OllamaConnectionError, OllamaGenerationError: propagated from llm.generate.
        ManipulationError: propagated from render() on I/O failure or manifest/template mismatch.
        ValueError: propagated from render() on corrupt/missing template.
    """
    content = generate_content(manifest, messages, model, client=client)
    return render(manifest, content, out_path, template_dir)
