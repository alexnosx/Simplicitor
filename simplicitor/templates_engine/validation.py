# templates_engine/validation.py
# Phase C: Content model generation and validation.
import logging
from typing import Annotated, Any

from pydantic import BaseModel, Field, ValidationError, create_model

from templates_engine.manifest import FieldDef, Manifest, SlideTypeDef

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _field_annotation_and_default(field: FieldDef) -> tuple[Any, Any]:
    """Return (annotation, default) for use in create_model.

    Required fields use ``...`` (Ellipsis) as the default.
    Optional text/image fields default to None; optional bullets default to [].
    """
    if field.kind == "text":
        if field.max_chars is not None:
            ann: Any = Annotated[str, Field(max_length=field.max_chars)]
        else:
            ann = str
        if not field.required:
            ann = ann | None
        return (ann, ... if field.required else None)

    if field.kind == "bullets":
        if field.max_items is not None:
            ann = Annotated[list[str], Field(max_length=field.max_items)]
        else:
            ann = list[str]
        return (ann, ... if field.required else [])

    if field.kind == "image":
        ann = str | None if not field.required else str
        return (ann, ... if field.required else None)

    raise ValueError(f"Unknown field kind: {field.kind!r}")  # pragma: no cover


def _build_fields_model(slide_name: str, slide_def: SlideTypeDef) -> type[BaseModel]:
    """Build a Pydantic model that validates the 'fields' dict for one slide type."""
    field_defs: dict[str, tuple[Any, Any]] = {}
    for field in slide_def.fields:
        ann, default = _field_annotation_and_default(field)
        field_defs[field.name] = (ann, default)
    return create_model(f"_{slide_name.title()}Fields", **field_defs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_content_model(manifest: Manifest) -> type[BaseModel]:
    """Return a Pydantic model class for the structural shape of content JSON.

    The returned model validates that 'slides' is a list of objects, each with a
    'type' string and a 'fields' dict. It does NOT enforce per-field constraints
    (max_chars, max_items, required). For full validation use validate_content().

    Args:
        manifest: A validated Manifest from load_manifest().

    Returns:
        A BaseModel subclass named ContentModel.
    """
    class _SlideData(BaseModel):
        type: str
        fields: dict[str, Any] = {}

    class ContentModel(BaseModel):
        slides: list[_SlideData]

    return ContentModel


def validate_content(
    manifest: Manifest, raw_json: Any
) -> tuple[bool, Any]:
    """Validate raw content JSON against the manifest.

    Checks that every slide has a known type, required fields are present,
    text fields respect max_chars, and bullet lists respect max_items. All
    errors are collected before returning — a single call surfaces every problem.

    Args:
        manifest: A validated Manifest from load_manifest().
        raw_json: The parsed JSON value to validate. Expected shape:
            ``{"slides": [{"type": str, "fields": dict}, ...]}``.

    Returns:
        ``(True, parsed)`` on success, where ``parsed`` is a dict
        ``{"slides": [{"type": str, "fields": dict}, ...]}``.

        ``(False, errors)`` on failure, where ``errors`` is a ``list[str]``
        of field-specific messages. Each message names the offending location
        (e.g. ``"slides[0].fields.heading: Field required."``). Pass to
        format_validation_errors() to produce the repair prompt string.
    """
    if not isinstance(raw_json, dict):
        return False, [f"Content must be a JSON object, got {type(raw_json).__name__}."]

    if "slides" not in raw_json:
        return False, ["Content is missing required key 'slides'."]

    slides_raw = raw_json["slides"]
    if not isinstance(slides_raw, list):
        return False, [f"'slides' must be a list, got {type(slides_raw).__name__}."]

    # Build per-slide-type field validators once (avoids repeated create_model calls)
    fields_models: dict[str, type[BaseModel]] = {
        name: _build_fields_model(name, sdef)
        for name, sdef in manifest.slide_types.items()
    }
    valid_types = set(manifest.slide_types.keys())

    errors: list[str] = []
    parsed_slides: list[dict] = []

    for idx, slide in enumerate(slides_raw):
        prefix = f"slides[{idx}]"

        if not isinstance(slide, dict):
            errors.append(f"{prefix}: must be an object, got {type(slide).__name__}.")
            continue

        slide_type = slide.get("type")
        if slide_type is None:
            errors.append(f"{prefix}.type: required field is missing.")
            continue
        if not isinstance(slide_type, str):
            errors.append(
                f"{prefix}.type: expected string, got {type(slide_type).__name__}."
            )
            continue
        if slide_type not in valid_types:
            known = ", ".join(sorted(valid_types))
            errors.append(
                f"{prefix}.type: unknown slide type '{slide_type}' "
                f"(known types: {known})."
            )
            continue

        fields_raw = slide.get("fields") or {}
        if not isinstance(fields_raw, dict):
            errors.append(
                f"{prefix}.fields: must be an object, got {type(fields_raw).__name__}."
            )
            continue

        try:
            parsed = fields_models[slide_type].model_validate(fields_raw)
            parsed_slides.append({"type": slide_type, "fields": parsed.model_dump()})
        except ValidationError as exc:
            for e in exc.errors():
                loc = ".".join(str(part) for part in e["loc"]) if e["loc"] else "value"
                errors.append(f"{prefix}.fields.{loc}: {e['msg']}.")

    if errors:
        logger.debug("Content validation failed with %d error(s).", len(errors))
        return False, errors

    return True, {"slides": parsed_slides}


def format_validation_errors(errors: list[str]) -> str:
    """Format validation errors as a compact, model-readable string.

    The output is designed to feed the LLM repair loop in Phase J.

    Args:
        errors: List of error strings from validate_content().

    Returns:
        A numbered list of errors as a single string, suitable for inclusion
        in an LLM prompt asking the model to fix the content JSON.
    """
    header = f"Content validation failed ({len(errors)} error(s)):"
    lines = [header] + [f"  {i}. {err}" for i, err in enumerate(errors, 1)]
    return "\n".join(lines)
