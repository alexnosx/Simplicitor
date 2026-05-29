# templates_engine/manifest.py
# Phase B: Manifest schema, loader, and linter.
import logging
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

VALID_KINDS = {"text", "bullets", "image"}


class FieldDef(BaseModel):
    name: str
    placeholder_idx: int
    kind: Literal["text", "bullets", "image"]
    required: bool
    max_chars: Optional[int] = None
    max_items: Optional[int] = None


class SlideTypeDef(BaseModel):
    layout_index: int
    repeatable: bool = False
    fields: list[FieldDef] = []


class Manifest(BaseModel):
    name: str
    type: Literal["pptx"]
    template_file: str
    description: str
    slide_types: dict[str, SlideTypeDef]


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_manifest(path: str | Path) -> Manifest:
    """Load and validate a manifest YAML file.

    Args:
        path: Path to the manifest YAML file.

    Returns:
        A validated Manifest instance.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the YAML is malformed, missing required keys, contains
            an invalid field kind, or has duplicate field names within a slide type.
            The error message names the specific problem.
    """
    path = Path(path)
    raw_text = path.read_text(encoding="utf-8")

    try:
        raw = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Manifest '{path.name}' is not valid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError(
            f"Manifest '{path.name}' must be a YAML mapping at the top level, "
            f"got {type(raw).__name__}."
        )

    try:
        manifest = Manifest.model_validate(raw)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        raise ValueError(
            f"Manifest '{path.name}' validation failed: {errors}"
        ) from exc

    # Duplicate field name check (not covered by Pydantic)
    for slide_name, slide in manifest.slide_types.items():
        seen: set[str] = set()
        for field in slide.fields:
            if field.name in seen:
                raise ValueError(
                    f"Manifest '{path.name}': slide type '{slide_name}' has "
                    f"duplicate field name '{field.name}'."
                )
            seen.add(field.name)

    logger.debug("Loaded manifest '%s' with %d slide type(s).", path.name, len(manifest.slide_types))
    return manifest


# ---------------------------------------------------------------------------
# Linter
# ---------------------------------------------------------------------------

def lint_manifest(manifest: Manifest) -> list[str]:
    """Return a list of warning strings for non-fatal issues in the manifest.

    Does not raise. Returns an empty list if no issues are found.

    Args:
        manifest: A validated Manifest instance (from load_manifest).

    Returns:
        List of human-readable warning strings.
    """
    warnings: list[str] = []

    for slide_name, slide in manifest.slide_types.items():
        if not slide.fields:
            warnings.append(
                f"Slide type '{slide_name}' has no fields defined — "
                "it will always render as a blank slide."
            )

        for field in slide.fields:
            if field.max_chars is not None and field.kind != "text":
                warnings.append(
                    f"Slide type '{slide_name}', field '{field.name}': "
                    f"max_chars is only meaningful for kind='text' (this field is '{field.kind}')."
                )
            if field.max_items is not None and field.kind != "bullets":
                warnings.append(
                    f"Slide type '{slide_name}', field '{field.name}': "
                    f"max_items is only meaningful for kind='bullets' (this field is '{field.kind}')."
                )

    return warnings
