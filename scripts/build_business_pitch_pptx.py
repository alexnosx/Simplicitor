"""One-shot rebuilder for templates_engine/builtin/business_pitch/template.pptx.

Takes a source .pptx (the Water-Colored-Splashes deck or a successor), strips
all sample slides, and writes the stripped file to the bundled location. The
manifest is not touched: after running this, re-verify layout indices with
scripts/inspect_template.py and update manifest.yaml if anything moved.

Usage:
    python scripts/build_business_pitch_pptx.py <source-pptx>
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEST = _REPO_ROOT / "simplicitor" / "templates_engine" / "builtin" / "business_pitch" / "template.pptx"


def _strip_slides(prs) -> int:
    """Delete every slide from *prs* in place. Returns the count removed."""
    sldIdLst = prs.slides._sldIdLst
    slide_ids = list(sldIdLst)
    for sldId in slide_ids:
        rId = sldId.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        prs.part.drop_rel(rId)
        sldIdLst.remove(sldId)
    return len(slide_ids)


def build(source: Path) -> None:
    from pptx import Presentation

    if not source.is_file():
        print(f"Source not found: {source}", file=sys.stderr)
        sys.exit(1)
    if source.suffix.lower() != ".pptx":
        print(f"Expected a .pptx file, got: {source.suffix!r}", file=sys.stderr)
        sys.exit(1)

    prs = Presentation(str(source))
    removed = _strip_slides(prs)

    _DEST.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(_DEST))

    layouts = len(prs.slide_masters[0].slide_layouts)
    size_kb = _DEST.stat().st_size / 1024
    print(f"Source : {source.name}")
    print(f"Removed: {removed} slide(s)")
    print(f"Dest   : {_DEST.relative_to(_REPO_ROOT)}")
    print(f"Master 0 layouts: {layouts}")
    print(f"Size   : {size_kb:.1f} KB")
    print()
    print("Next: python scripts/inspect_template.py simplicitor/templates_engine/builtin/business_pitch/template.pptx")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    build(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
