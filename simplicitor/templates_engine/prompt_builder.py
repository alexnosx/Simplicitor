# templates_engine/prompt_builder.py
# Phase I: Prompt builder.
import json
import logging

from templates_engine.manifest import Manifest
from templates_engine.validation import format_validation_errors

logger = logging.getLogger(__name__)


def build_prompt(
    manifest: Manifest,
    user_request: str,
    source_text: str | None = None,
) -> list[dict]:
    """Build a 4-message OpenAI chat prompt from a manifest and user request.

    Args:
        manifest: Validated Manifest instance describing slide types and fields.
        user_request: The user's deck-creation request.
        source_text: Optional source material to include in the final user message.

    Returns:
        List of 4 dicts in OpenAI chat format:
        [system, user (one-shot), assistant (one-shot), user (actual request)]
    """
    system_content = _build_system_message(manifest)
    one_shot_user = "Create a deck about machine learning fundamentals."
    one_shot_assistant = _build_one_shot_assistant(manifest)
    actual_user = _build_actual_user_message(user_request, source_text)

    logger.debug(
        "Built prompt with %d slide types.",
        len(manifest.slide_types),
    )

    return [
        {"role": "system",    "content": system_content},
        {"role": "user",      "content": one_shot_user},
        {"role": "assistant", "content": one_shot_assistant},
        {"role": "user",      "content": actual_user},
    ]


def _build_system_message(manifest: Manifest) -> str:
    lines = [
        "Return ONLY valid JSON. No markdown fences, no explanation, no preamble.",
        "",
        "SLIDE TYPE SCHEMA:",
    ]

    for slide_name, slide_def in manifest.slide_types.items():
        lines.append(f"{slide_name} (layout {slide_def.layout_index}):")
        for field in slide_def.fields:
            parts = [f"  {field.name}: {field.kind}"]
            parts.append("required" if field.required else "optional")
            if field.max_chars is not None:
                parts.append(f"max {field.max_chars} chars")
            if field.max_items is not None:
                parts.append(f"max {field.max_items} items")
            lines.append(", ".join(parts))

    lines += [
        "",
        "OUTPUT SHAPE:",
        '{"slides": [{"type": "<slide_type>", "fields": {<field_name>: <value>, ...}}, ...]}',
        "",
        "RULES:",
        "- bullets fields must be arrays of strings",
        "- omit optional fields if not needed",
        "- no extra keys beyond those listed in the schema",
        "",
        "LENGTH:",
        "Produce a substantive deck. Default to 8 to 12 slides covering the topic "
        "with depth, regardless of how briefly or lengthily the user phrased the "
        "request. A short prompt about a substantive topic still deserves a thorough deck.",
        "",
        "Honor explicit length signals in the user's request:",
        '- Words like "brief", "quick", "summary", "overview", "short": produce 4 to 6 slides',
        '- Words like "comprehensive", "detailed", "in-depth", "thorough", "deep dive": produce 12 to 16 slides',
        '- An explicit slide count ("5-slide deck", "10 slides", etc.): honor it exactly',
        "- Otherwise: 8 to 12 slides",
        "",
        "When in a range, target the upper end. Each slide covers one focused topic "
        "with substantive content. Use a mix of the slide types provided. Content-shaped "
        "slide types (those with bullets fields) can appear multiple times in a single deck.",
    ]

    return "\n".join(lines)


def _build_one_shot_assistant(manifest: Manifest) -> str:
    """Build one-shot assistant JSON demonstrating type variety.

    Emits every slide type exactly once, in manifest order. Synthetic field content
    varies by slide type (text fields include the slide name; bullets fields include
    the slide name in each item) so adjacent slides are visibly distinct. The earlier
    in-place duplication scheme produced byte-for-byte identical adjacent slides,
    which degenerated gemma4 in JSON-constrained mode; the LENGTH guidance in the
    system message now carries the slide-count intent on its own, and this one-shot
    only has to demonstrate the JSON shape.
    """
    example_slides = []
    for slide_name, slide_def in manifest.slide_types.items():
        fields: dict = {}
        for field in slide_def.fields:
            if not field.required:
                continue  # omit optional fields from example
            if field.kind == "text":
                # Capitalise each word of the field name for readable synthetic content;
                # include the slide name so the example reads as distinct per-slide content.
                label = field.name.replace("_", " ").title()
                fields[field.name] = f"Example {slide_name.title()} {label}"
            elif field.kind == "bullets":
                fields[field.name] = [
                    f"First {slide_name} point",
                    f"Second {slide_name} point",
                ]
            elif field.kind == "image":
                fields[field.name] = "path/to/image.png"
            else:
                logger.warning(
                    "Unknown field kind '%s' for field '%s' — omitted from one-shot example.",
                    field.kind,
                    field.name,
                )

        example_slides.append({"type": slide_name, "fields": fields})

    return json.dumps({"slides": example_slides})


def _build_actual_user_message(user_request: str, source_text: str | None) -> str:
    message = f"Request: {user_request}"
    if source_text is not None:
        message += f"\n\nSource content:\n{source_text}"
    return message


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
