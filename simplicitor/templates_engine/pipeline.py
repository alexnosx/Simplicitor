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

    NOTE: This stub always returns False. Task 9 replaces this with the real
    heuristic once done_reason behaviour is verified against Ollama.
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
        repair_max_tokens = OLLAMA_REPAIR_MAX_TOKENS if truncated else None
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
