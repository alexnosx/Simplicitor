# templates_engine/breakdown.py
# Phase D-F: PPTX structural inspector, content stripping, draft manifest generation.
import logging
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_EMU_PER_INCH = 914_400


def _emu_to_in(emu: int | None) -> str:
    if emu is None:
        return "?"
    return f"{emu / _EMU_PER_INCH:.2f}\""


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
    from pptx import Presentation  # local import keeps startup cost low
    from pptx.exceptions import InvalidXmlError, PackageNotFoundError

    path = Path(path)

    if not path.exists():
        raise ValueError(f"File not found: '{path}'.")

    if path.suffix.lower() != ".pptx":
        raise ValueError(
            f"Expected a .pptx file, got '{path.suffix or '(no extension)'}' ('{path.name}')."
        )

    try:
        prs = Presentation(str(path))
    except (PackageNotFoundError, InvalidXmlError, KeyError, zipfile.BadZipFile) as exc:
        # Known python-pptx failure modes: corrupt/non-zip, bad XML, missing content type.
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
# Phase E stubs: strip_to_template, score_layouts
# ---------------------------------------------------------------------------

def strip_to_template(path: str | Path, out_path: str | Path) -> None:
    raise NotImplementedError


def score_layouts(inspection: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError


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
