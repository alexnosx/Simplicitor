"""Build patched copies of the Word fixtures for the one-off Word check (Task C2).

Usage: python scripts/build_edit_samples.py <empty output folder outside the repository>
Every sample goes through open_document and build_candidate, the production route. Prints
each sample's SHA-256 for the check record; exits 2 without writing for an unsafe folder.
"""
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "simplicitor") not in sys.path:
    sys.path.insert(0, str(ROOT / "simplicitor"))

from editing.models import Proposal, ProposedParagraph  # noqa: E402
from editing.package import open_document  # noqa: E402
from editing.patch import build_candidate  # noqa: E402

FIXTURES = ROOT / "tests" / "editing" / "fixtures"
SAMPLES = [
    ("bold-value", "word-basic.docx", "Invoices are payable",
     [(0, "Invoices are payable within 45 days of receipt.")]),
    ("range-split", "word-basic.docx", "1. Scope",
     [(0, "1. Project scope"), (1, "Review the documents."), (1, "Added paragraph."),
      (2, "Deliver the draft.\tTab kept.\nLine kept.")]),
    ("list-item-added", "word-basic.docx", "A short findings report",
     [(0, "A short findings report."), (1, "One review meeting."), (1, "A final presentation.")]),
    ("headings-split", "word-ranges.docx", "First heading",
     [(0, "Opening heading"), (1, "Closing heading"), (1, "A new line.")]),
    ("page-break-split", "word-ranges.docx", "This paragraph starts",
     [(0, "This paragraph starts on a new page."), (0, "This added paragraph must not.")]),
    ("goback-rewrite", "word-ranges.docx", "The GoBack",
     [(0, "The hidden bookmark now sits in a rewritten sentence.")]),
]


def main(out: Path) -> int:
    out = Path(out).resolve()
    if out == ROOT or ROOT in out.parents or (out.exists() and any(out.iterdir())):
        print("Choose an empty folder outside the repository.")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    for name, fixture, start, items in SAMPLES:
        opened = open_document(FIXTURES / fixture)
        first = next(b.index for b in opened.paragraphs if b.text.startswith(start))
        last = first + max(source for source, _ in items)
        proposal = Proposal(tuple(ProposedParagraph(s, t) for s, t in items))
        data = build_candidate(opened, first, last, proposal).data
        (out / f"{name}.docx").write_bytes(data)
        print(f"{name}.docx {hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])) if len(sys.argv) == 2 else 2)
