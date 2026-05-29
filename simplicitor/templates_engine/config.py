# templates_engine/config.py
# Phase G: Two-directory template system — config resolution, listing, and import.
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

TEMPLATE_PPTX_NAME = "template.pptx"
MANIFEST_NAME = "manifest.yaml"
_APP_NAME = "Simplicitor"


# ---------------------------------------------------------------------------
# Directory resolution
# ---------------------------------------------------------------------------

def get_builtin_root() -> Path:
    """Return the read-only built-in templates root (ships with the app)."""
    return Path(__file__).parent / "builtin"


def get_user_root() -> Path:
    """Return the writable user templates root, creating it on first call.

    Uses %APPDATA%\\Simplicitor\\templates on Windows, or
    ~/.simplicitor/templates as fallback. Can be overridden via
    simplicitor.toml (``[templates] user_dir = "..."``).

    Raises:
        ManipulationError: If the directory cannot be created (permissions/disk).
    """
    override = _config_override("user_dir")
    if override is not None:
        if not isinstance(override, str) or not override.strip():
            raise ValueError(
                "simplicitor.toml [templates] user_dir must be a non-empty string."
            )
        root = Path(override)
    else:
        appdata = os.environ.get("APPDATA")
        if appdata:
            root = Path(appdata) / _APP_NAME / "templates"
        else:
            root = Path.home() / f".{_APP_NAME.lower()}" / "templates"
    _ensure_dir(root)
    return root


def _ensure_dir(path: Path) -> None:
    """Create *path* and all parents, raising ManipulationError on failure."""
    from app.services.file_manipulator import ManipulationError
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Cannot create directory '%s': %s", path, exc)
        raise ManipulationError(
            f"Cannot create user templates directory: {exc}"
        ) from exc


def _config_override(key: str) -> str | None:
    """Read an optional value from simplicitor.toml under [templates], if present."""
    import tomllib
    appdata = os.environ.get("APPDATA")
    candidates: list[Path] = []
    if appdata:
        candidates.append(Path(appdata) / _APP_NAME / "simplicitor.toml")
    candidates.append(Path.home() / f".{_APP_NAME.lower()}" / "simplicitor.toml")
    for config_path in candidates:
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    data = tomllib.load(f)
                return data.get("templates", {}).get(key)
            except Exception:
                logger.warning("Could not read config from '%s'.", config_path.name)
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "template"


def _is_valid_template_dir(path: Path) -> bool:
    """True if *path* contains both template.pptx and manifest.yaml."""
    return (path / TEMPLATE_PPTX_NAME).is_file() and (path / MANIFEST_NAME).is_file()


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------

def list_templates(
    user_root: Path | None = None,
    builtin_root: Path | None = None,
) -> list[dict[str, Any]]:
    """Return all templates from both roots, tagged with their source.

    Args:
        user_root: Override the user root (default: get_user_root()).
        builtin_root: Override the built-in root (default: get_builtin_root()).

    Returns:
        A list of dicts with keys:
            ``name`` (str): folder name.
            ``source`` (str): "builtin" or "user".
            ``path`` (Path): the template folder.
            ``manifest_path`` (Path): folder / "manifest.yaml".
            ``template_pptx`` (Path): folder / "template.pptx".
        Built-in templates come first, then user; each set is alphabetical.
        Subdirectories that lack either required file are silently skipped.
    """
    broot = builtin_root if builtin_root is not None else get_builtin_root()
    uroot = user_root if user_root is not None else get_user_root()

    templates: list[dict[str, Any]] = []
    for source, root in (("builtin", broot), ("user", uroot)):
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and _is_valid_template_dir(entry):
                templates.append({
                    "name": entry.name,
                    "source": source,
                    "path": entry,
                    "manifest_path": entry / MANIFEST_NAME,
                    "template_pptx": entry / TEMPLATE_PPTX_NAME,
                })

    logger.debug("list_templates: %d template(s) found.", len(templates))
    return templates


# ---------------------------------------------------------------------------
# import_template
# ---------------------------------------------------------------------------

def import_template(
    pptx_path: str | Path,
    user_root: Path | None = None,
) -> dict[str, Any]:
    """Import a .pptx file as a user template.

    Runs inspect -> score -> (if usable) strip + manifest. The hard-stop
    result is returned as a normal value for an unusable deck; genuine
    failures raise. No partial folder is left behind on failure.

    Args:
        pptx_path: Path to the source .pptx.
        user_root: Override the user root (useful in tests).

    Returns:
        Success: {"status": "ok", "name": str, "path": Path,
                  "report": str, "lint_warnings": list[str]}
        Hard stop: {"status": "hard_stop", "message": str}

    Raises:
        ValueError: If pptx_path is invalid, or a same-named template already
            exists in the user root.
        ManipulationError: If the user root cannot be created, the template
            folder cannot be created, or a write fails. No partial folder
            is left behind.
    """
    from app.services.file_manipulator import ManipulationError
    from templates_engine.breakdown import (
        detection_report,
        generate_draft_manifest,
        hard_stop_result,
        inspect_pptx,
        score_layouts,
        strip_to_template,
    )
    from templates_engine.manifest import lint_manifest, load_manifest

    pptx_path = Path(pptx_path)
    uroot = user_root if user_root is not None else get_user_root()

    # Inspect and score (ValueError propagates for bad input).
    inspection = inspect_pptx(pptx_path)
    scoring = score_layouts(inspection)

    if not scoring["is_usable"]:
        logger.debug("Import rejected (unusable deck): '%s'.", pptx_path.name)
        return hard_stop_result()

    name = _slugify(pptx_path.stem)
    template_dir = uroot / name

    if template_dir.exists():
        raise ValueError(
            f"A template named '{name}' already exists in the user templates directory. "
            "Delete or rename it before importing again."
        )

    report = detection_report(inspection, scoring)

    # Create the folder; wrap mkdir failure as ManipulationError.
    try:
        template_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ManipulationError(
            f"Cannot create template folder '{name}': {exc}"
        ) from exc

    try:
        out_pptx = template_dir / TEMPLATE_PPTX_NAME
        strip_to_template(pptx_path, out_pptx)

        manifest_dict = generate_draft_manifest(inspection, scoring, TEMPLATE_PPTX_NAME)
        manifest_path = template_dir / MANIFEST_NAME
        try:
            manifest_path.write_text(
                yaml.dump(manifest_dict, allow_unicode=True), encoding="utf-8"
            )
        except OSError as exc:
            raise ManipulationError(
                f"Could not write manifest for '{name}': {exc}"
            ) from exc

    except Exception:
        # No-partial-folder discipline: remove the template folder before re-raising.
        try:
            shutil.rmtree(template_dir)
        except OSError:
            logger.warning("Could not clean up partial template folder '%s'.", name)
        raise

    # Load and lint the written manifest.
    lint_warnings: list[str] = []
    try:
        loaded = load_manifest(manifest_path)
        lint_warnings = lint_manifest(loaded)
    except (ValueError, OSError):
        pass  # lint failure is non-fatal; warnings unavailable

    logger.debug("Imported template '%s'.", name)
    return {
        "status": "ok",
        "name": name,
        "path": template_dir,
        "report": report,
        "lint_warnings": lint_warnings,
    }
