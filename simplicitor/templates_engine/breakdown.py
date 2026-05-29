# templates_engine/breakdown.py
# Phase D-F: PPTX structural inspector, content stripping, draft manifest generation.
import logging
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_EMU_PER_INCH = 914_400
_SLIDE_REL_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
# Placeholder types that carry no fillable content (date stamp, footer text, slide counter).
_DECORATIVE_TYPES = frozenset({"DATE", "FOOTER", "SLIDE_NUMBER"})


def _emu_to_in(emu: int | None) -> str:
    if emu is None:
        return "?"
    return f"{emu / _EMU_PER_INCH:.2f}\""


def _open_presentation(path: Path):
    """Open a .pptx file, raising ValueError on missing, wrong extension, or corrupt file."""
    from pptx import Presentation
    from pptx.exceptions import InvalidXmlError, PackageNotFoundError

    if not path.exists():
        raise ValueError(f"File not found: '{path}'.")
    if path.suffix.lower() != ".pptx":
        raise ValueError(
            f"Expected a .pptx file, got '{path.suffix or '(no extension)'}' ('{path.name}')."
        )
    try:
        return Presentation(str(path))
    except (PackageNotFoundError, InvalidXmlError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(
            f"Could not open '{path.name}' as a PowerPoint file."
        ) from exc
    except Exception as exc:
        # Unexpected failure — surface the type name only, never str(exc) which may
        # contain internal paths or unrelated details.
        raise ValueError(
            f"Could not open '{path.name}' as a PowerPoint file "
            f"({type(exc).__name__})."
        ) from exc


# ---------------------------------------------------------------------------
# Phase D: inspect_pptx + format_inspection
# ---------------------------------------------------------------------------

def inspect_pptx(path: str | Path) -> dict[str, Any]:
    """Inspect the layout/placeholder structure of a .pptx file (read-only).

    Args:
        path: Path to the .pptx file to inspect.

    Returns:
        A dict with keys:
            ``path`` (str): absolute resolved path.
            ``layouts`` (list): one entry per slide layout with:
                ``layout_index`` (int), ``name`` (str),
                ``placeholders`` (list) each with:
                    ``idx`` (int),
                    ``type`` (str, e.g. ``"TITLE (1)"``),
                    ``name`` (str),
                    ``position`` (dict: left/top/width/height in EMU, may be None),
                    ``is_custom`` (bool, True when idx >= 10).

    Raises:
        ValueError: If the file is missing, does not have a .pptx extension,
            or cannot be opened as a PowerPoint presentation.
    """
    path = Path(path)
    prs = _open_presentation(path)

    layouts: list[dict[str, Any]] = []
    for layout_idx, layout in enumerate(prs.slide_layouts):
        placeholders: list[dict[str, Any]] = []
        for ph in layout.placeholders:
            ph_idx = ph.placeholder_format.idx
            placeholders.append({
                "idx": ph_idx,
                "type": str(ph.placeholder_format.type),
                "name": ph.name,
                "position": {
                    "left": ph.left,
                    "top": ph.top,
                    "width": ph.width,
                    "height": ph.height,
                },
                "is_custom": ph_idx >= 10,
            })
        layouts.append({
            "layout_index": layout_idx,
            "name": layout.name,
            "placeholders": placeholders,
        })

    logger.debug("Inspected '%s': %d layout(s).", path.name, len(layouts))
    return {
        "path": str(path.resolve()),
        "layouts": layouts,
    }


def format_inspection(report: dict[str, Any]) -> str:
    """Format an inspection report as a human-readable string for CLI output.

    Args:
        report: The dict returned by inspect_pptx().

    Returns:
        A multi-line string showing each layout and its placeholders.
    """
    lines: list[str] = [
        f"File: {report['path']}",
        f"Layouts: {len(report['layouts'])}",
    ]

    for layout in report["layouts"]:
        ph_count = len(layout["placeholders"])
        lines.append(
            f"\n  [{layout['layout_index']:2d}] {layout['name']}  "
            f"({ph_count} placeholder{'s' if ph_count != 1 else ''})"
        )
        for ph in layout["placeholders"]:
            pos = ph["position"]
            pos_str = (
                f"left={_emu_to_in(pos['left'])} "
                f"top={_emu_to_in(pos['top'])} "
                f"w={_emu_to_in(pos['width'])} "
                f"h={_emu_to_in(pos['height'])}"
            )
            custom = "  [CUSTOM]" if ph["is_custom"] else ""
            lines.append(
                f"       idx={ph['idx']:2d}  {ph['type']:<25}  {ph['name']!r:<35}  {pos_str}{custom}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Phase E: strip_to_template, score_layouts
# ---------------------------------------------------------------------------

def strip_to_template(path: str | Path, out_path: str | Path) -> None:
    """Remove all slides from a .pptx, keeping masters/layouts/theme, and save.

    Args:
        path: Path to the source .pptx file.
        out_path: Destination path for the stripped template.

    Raises:
        ValueError: If path is missing, not a .pptx, or cannot be opened.
        ManipulationError: If out_path cannot be written (permissions, disk).
            No partial file is left behind on failure.
    """
    from app.services.file_manipulator import ManipulationError

    path = Path(path)
    out_path = Path(out_path)
    prs = _open_presentation(path)

    # Remove all slides while keeping masters/layouts/theme intact.
    slide_id_list = prs.slides._sldIdLst
    for sld_id in list(slide_id_list):
        r_id = sld_id.get(_SLIDE_REL_ATTR)
        if r_id:
            prs.part.drop_rel(r_id)
        slide_id_list.remove(sld_id)

    try:
        prs.save(str(out_path))
    except OSError as exc:
        # Best-effort cleanup: remove any partial file written before the failure.
        try:
            out_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not clean up partial file '%s'.", out_path.name)
        logger.error("Failed to write stripped template to '%s': %s", out_path, exc)
        raise ManipulationError(
            f"Could not write template to '{out_path.name}': {exc}"
        ) from exc

    logger.debug("Stripped '%s' -> '%s' (0 slides).", path.name, out_path.name)


def score_layouts(inspection: dict[str, Any]) -> dict[str, Any]:
    """Score each layout in an inspection report as usable or unusable for templating.

    A layout is usable if it has at least one non-title content placeholder:
    idx >= 1 (not the title), idx < 10 (not custom), and type not in
    {DATE, FOOTER, SLIDE_NUMBER} (not purely decorative).
    Title-only layouts (only idx=0) are unusable — no body to fill.

    Args:
        inspection: The dict returned by inspect_pptx().

    Returns:
        A dict with:
            ``layouts`` (list): per-layout dicts with ``layout_index``, ``name``,
                ``usable`` (bool).
            ``is_usable`` (bool): True if at least one layout is usable.
    """
    layout_scores: list[dict[str, Any]] = []
    any_usable = False

    for layout in inspection["layouts"]:
        has_content_ph = any(
            1 <= ph["idx"] < 10
            and not any(dt in ph["type"].upper() for dt in _DECORATIVE_TYPES)
            for ph in layout["placeholders"]
        )
        if has_content_ph:
            any_usable = True
        layout_scores.append({
            "layout_index": layout["layout_index"],
            "name": layout["name"],
            "usable": has_content_ph,
        })

    return {
        "layouts": layout_scores,
        "is_usable": any_usable,
    }


# ---------------------------------------------------------------------------
# Phase F stubs: generate_draft_manifest, detection_report, hard_stop_result
# ---------------------------------------------------------------------------

def generate_draft_manifest(
    inspection: dict[str, Any],
    scoring: dict[str, Any],
    template_file: str,
) -> dict[str, Any]:
    raise NotImplementedError


def detection_report(
    inspection: dict[str, Any],
    scoring: dict[str, Any],
) -> str:
    raise NotImplementedError


def hard_stop_result() -> dict[str, Any]:
    raise NotImplementedError
