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

# Curated templates that ship with the app and are always present in the user's
# Templates folder (seeded from the bundled built-in source if missing).
DEFAULT_TEMPLATE_NAMES = ("business_pitch", "technical_overview")


# ---------------------------------------------------------------------------
# Directory resolution
# ---------------------------------------------------------------------------

def get_builtin_root() -> Path:
    """Return the read-only built-in templates root (ships with the app)."""
    return Path(__file__).parent / "builtin"


def get_app_data_dir() -> Path:
    """Return the per-user Simplicitor data root. No side effects.

    ``%APPDATA%\\Simplicitor`` when APPDATA is set, otherwise ``~/.simplicitor``.
    Settings (settings.json) live directly in this directory (see main.py).
    Template resolution is unified on ``Settings.templates_dir``; the old
    ``templates/`` subfolder here is retired (the CLI prints a notice if
    templates are still found in it).
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / _APP_NAME
    return Path.home() / f".{_APP_NAME.lower()}"


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
    """Return templates from the given roots, tagged with their source.

    Args:
        user_root: The user templates root to scan; None scans built-ins only.
            There is no implicit user root: resolution is unified on
            Settings.templates_dir and callers pass it explicitly.
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

    roots: list[tuple[str, Path]] = [("builtin", broot)]
    if user_root is not None:
        roots.append(("user", user_root))

    templates: list[dict[str, Any]] = []
    for source, root in roots:
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
# list_library / ensure_default_templates (single-folder GUI model)
# ---------------------------------------------------------------------------

def list_library(templates_root: str | Path) -> list[dict[str, Any]]:
    """List templates in a single library folder, tagging defaults vs user uploads.

    The GUI keeps all templates (seeded defaults + user uploads) in one configurable
    folder rather than the two-root builtin/user split that the CLI uses.

    Args:
        templates_root: The folder to scan.

    Returns:
        A list of dicts (same shape as list_templates) with ``source`` set to "default"
        for the curated defaults (names in DEFAULT_TEMPLATE_NAMES) and "user" otherwise.
        Subdirectories missing either required file are skipped; an absent root yields [].
    """
    root = Path(templates_root)
    templates: list[dict[str, Any]] = []
    if not root.is_dir():
        return templates
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and _is_valid_template_dir(entry):
            source = "default" if entry.name in DEFAULT_TEMPLATE_NAMES else "user"
            templates.append({
                "name": entry.name,
                "source": source,
                "path": entry,
                "manifest_path": entry / MANIFEST_NAME,
                "template_pptx": entry / TEMPLATE_PPTX_NAME,
            })
    logger.debug("list_library: %d template(s) in '%s'.", len(templates), root)
    return templates


def ensure_default_templates(templates_root: str | Path) -> None:
    """Ensure the curated default templates exist in *templates_root*.

    Creates the folder if absent, then copies each name in DEFAULT_TEMPLATE_NAMES from
    the bundled built-in source if it is not already a valid template there. An existing
    default (even if edited) is left untouched; a deleted one is restored on the next
    call. Best-effort: a missing source default or a copy failure is logged and skipped,
    never raised, so this is safe to call at startup.

    Args:
        templates_root: The user-facing Templates folder.
    """
    from app.services.file_manipulator import ManipulationError

    root = Path(templates_root)
    try:
        _ensure_dir(root)
    except ManipulationError as exc:
        logger.error("Cannot prepare templates folder '%s': %s", root, exc)
        return

    builtin = get_builtin_root()
    for name in DEFAULT_TEMPLATE_NAMES:
        dest = root / name
        if _is_valid_template_dir(dest):
            continue
        src = builtin / name
        if not _is_valid_template_dir(src):
            logger.warning("Default template source missing or invalid: '%s'.", src)
            continue
        try:
            if dest.exists():
                shutil.rmtree(dest)  # incomplete/partial folder: replace cleanly
            shutil.copytree(src, dest)
            logger.debug("Seeded default template '%s'.", name)
        except OSError as exc:
            logger.error("Could not seed default template '%s': %s", name, exc)


# ---------------------------------------------------------------------------
# import_template
# ---------------------------------------------------------------------------

def import_template(
    pptx_path: str | Path,
    user_root: Path,
) -> dict[str, Any]:
    """Import a .pptx file as a user template.

    Runs inspect -> score -> (if usable) strip + manifest. The hard-stop
    result is returned as a normal value for an unusable deck; genuine
    failures raise. No partial folder is left behind on failure.

    Args:
        pptx_path: Path to the source .pptx.
        user_root: The templates root to import into. Callers resolve it
            explicitly (the app and CLI both use Settings.templates_dir).

    Returns:
        Success:   {"status": "ok", "name": str, "path": Path,
                    "report": str, "lint_warnings": list[str]}
        Hard stop: {"status": "hard_stop", "message": str}
        Collision: {"status": "exists", "name": str}

    Raises:
        ManipulationError: If pptx_path is missing, the user root cannot be
            created, the template folder cannot be created, or a write fails.
            No partial folder is left behind.
        ValueError: If pptx_path does not have a .pptx extension or is corrupt.
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
    uroot = Path(user_root)

    # Inspect and score. ValueError propagates for bad input (wrong ext, corrupt);
    # ManipulationError propagates for missing file.
    inspection = inspect_pptx(pptx_path)
    scoring = score_layouts(inspection)

    if not scoring["is_usable"]:
        logger.debug("Import rejected (unusable deck): '%s'.", pptx_path.name)
        return hard_stop_result()

    name = _slugify(pptx_path.stem)
    template_dir = uroot / name

    if template_dir.exists():
        logger.debug("Import skipped (name collision): '%s'.", name)
        return {"status": "exists", "name": name}

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
