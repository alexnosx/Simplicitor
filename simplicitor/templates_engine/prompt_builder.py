# templates_engine/prompt_builder.py
# Phase I: Prompt builder.
import json
import logging

from templates_engine.manifest import Manifest, SlideTypeDef
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
        "Produce as many slides as the request implies. Most decks have 3 to 7 slides. "
        "Use a mix of the slide types provided. Content-shaped slide types (those with "
        "bullets fields) can appear multiple times in a single deck.",
    ]

    return "\n".join(lines)


def _has_bullets_field(slide_def: SlideTypeDef) -> bool:
    """True if the slide type defines at least one field of kind 'bullets'."""
    return any(f.kind == "bullets" for f in slide_def.fields)


def _build_one_shot_assistant(manifest: Manifest) -> str:
    """Build one-shot assistant JSON demonstrating type variety and content repeatability.

    Emits every slide type once in manifest order, then appends a second occurrence of
    each slide type that has at least one kind:bullets field. The pattern shows the
    model that all schema types are available and that content-shaped types can repeat
    in a single deck, without anchoring on a specific overall slide count.
    """
    base_order: list[str] = list(manifest.slide_types.keys())
    duplicates: list[str] = [
        name for name in base_order
        if _has_bullets_field(manifest.slide_types[name])
    ]
    slide_order = base_order + duplicates

    example_slides = []
    for slide_name in slide_order:
        slide_def = manifest.slide_types[slide_name]
        fields: dict = {}
        for field in slide_def.fields:
            if not field.required:
                continue  # omit optional fields from example
            if field.kind == "text":
                # Capitalise each word of the field name for readable synthetic content
                label = field.name.replace("_", " ").title()
                fields[field.name] = f"Example {label}"
            elif field.kind == "bullets":
                fields[field.name] = ["First point", "Second point"]
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
