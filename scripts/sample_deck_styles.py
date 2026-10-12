# scripts/sample_deck_styles.py
"""Render a sample deck for every .pptx in a folder, the way the app would import it.

Usage:
    .venv/Scripts/python.exe scripts/sample_deck_styles.py <decks folder> <output folder>

Each deck goes through templates_engine.config.prepare_template, the same choice the
app makes on import: its own layouts, or its captured look. One slide per slide type
is filled with representative text at the template's limits and rendered to
<name>-sample.pptx, with one line per deck in report.txt. No AI model is called.
The output folder must be outside the decks folder; nothing else is written.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "simplicitor"))

from PIL import Image  # noqa: E402

from templates_engine.config import MANIFEST_NAME, prepare_template  # noqa: E402
from templates_engine.manifest import Manifest, load_manifest  # noqa: E402
from templates_engine.render_pptx import render  # noqa: E402
from templates_engine.validation import validate_content  # noqa: E402

_WORDS = ("Revenue grew twelve percent against plan while support response time fell to "
          "four hours and two enterprise customers signed annual contracts with the team.")


def _text(limit: int | None) -> str:
    """Representative text: about 90% of the field limit, or one long sentence."""
    if limit is None:
        return _WORDS
    text = (_WORDS + " ") * (limit // len(_WORDS) + 1)
    cut = text[:max(1, int(limit * 0.9))]
    return cut.rsplit(" ", 1)[0] if " " in cut.strip() else cut.strip()


def sample_content(manifest: Manifest, picture: Path) -> dict:
    """One slide per slide type, every field filled near its limits."""
    slides = []
    for name, slide_type in manifest.slide_types.items():
        fields = {}
        for field in slide_type.fields:
            if field.kind == "text":
                fields[field.name] = _text(field.max_chars)
            elif field.kind == "bullets":
                fields[field.name] = [_text(70) for _ in range(field.max_items or 4)]
            else:
                fields[field.name] = str(picture)
        slides.append({"type": name, "fields": fields})
    return {"slides": slides}


def sample(deck: Path, out: Path, picture: Path) -> str:
    """Prepare one deck as the app would, render its sample, and return its report line."""
    folder = out / deck.stem
    folder.mkdir(parents=True, exist_ok=True)
    prepared = prepare_template(deck, folder, deck.stem)
    manifest = load_manifest(folder / MANIFEST_NAME)
    valid, content = validate_content(manifest, sample_content(manifest, picture))
    if not valid:
        raise ValueError("Sample content does not fit the template.")
    render(manifest, content, out / f"{deck.stem}-sample.pptx", folder)
    if not prepared["captured"]:
        return f"{deck.name}: own layouts kept, {len(manifest.slide_types)} slide types."
    skipped = f" Could not copy: {', '.join(prepared['skipped'])}." if prepared["skipped"] else ""
    return f"{deck.name}: look captured. {prepared['report']}{skipped}"


def main(decks: Path, out: Path) -> list[str]:
    decks, out = decks.resolve(), out.resolve()
    if decks == out or decks in out.parents or out in decks.parents:
        raise SystemExit("Choose an output folder outside the decks folder.")
    out.mkdir(parents=True, exist_ok=True)
    picture = out / "sample-picture.png"
    Image.new("RGB", (640, 480), (150, 150, 150)).save(picture)
    lines = []
    for deck in sorted(decks.glob("*.pptx")):
        try:
            lines.append(sample(deck, out, picture))
        except Exception as exc:  # report every deck, even one that fails
            lines.append(f"{deck.name}: FAILED ({type(exc).__name__})")
    (out / "report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    for line in main(Path(sys.argv[1]), Path(sys.argv[2])):
        print(line)
