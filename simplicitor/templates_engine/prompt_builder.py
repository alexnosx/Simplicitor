# templates_engine/prompt_builder.py
# Phase I: Prompt builder.
import json
import logging

from templates_engine.manifest import Manifest

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
    one_shot_user = "Create a 2-slide overview deck."
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
    ]

    return "\n".join(lines)


def _build_one_shot_assistant(manifest: Manifest) -> str:
    """Build one-shot assistant JSON using the first two slide types from the manifest."""
    slide_names = list(manifest.slide_types.keys())
    example_slides = []

    for slide_name in slide_names[:2]:
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
