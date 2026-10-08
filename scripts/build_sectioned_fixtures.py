"""Render large synthetic fixtures without rewriting the accepted whole-file corpus."""
import json
from pathlib import Path

from docx import Document
from docx.shared import Pt

from scripts.build_extraction_fixtures import CONTRACT_COLUMNS, INVOICE_COLUMNS, write_pdf

ROOT = Path(__file__).resolve().parents[1] / "tests/extraction/fixtures"
_NOTES = (
    "The operations team keeps supporting correspondence in the agreed review order.",
    "Delivery coordinators review the work register before handing it to the next team.",
    "The review pack describes routine documentation and quality assurance procedures.",
    "Supporting material is retained so reviewers can follow the work between teams.",
)


def build(root: Path = ROOT) -> None:
    """Write four long files and independent labels; keep existing files unchanged."""
    authored = json.loads((root / "sectioned_cases.json").read_text())["cases"]
    manifest = json.loads((root / "manifest.json").read_text())
    for case in authored:
        pages = []
        for page in range(18):
            lines = [f"Note {page * 40 + index + 1:04d}. {_NOTES[index % len(_NOTES)]}"
                     for index in range(40)]
            if page in (0, 9, 17):
                lines = case["blocks"][(0, 9, 17).index(page)] + lines
            pages.append(lines)
        filename = case["id"] + "." + case["format"]
        if case["format"] == "pdf":
            write_pdf(root / filename, pages)
        else:
            doc = Document()
            style = doc.styles["Normal"]
            style.font.size = Pt(10)
            style.paragraph_format.space_after = Pt(0)
            style.paragraph_format.line_spacing = 1
            for index, lines in enumerate(pages):
                if index:
                    doc.add_page_break()
                for line in lines:
                    doc.add_paragraph(line)
            doc.save(root / filename)
        labels = "labels/" + case["id"] + ".json"
        (root / labels).write_text(json.dumps(case["labels"], indent=2) + "\n")
        definitions = INVOICE_COLUMNS if case["kind"] == "invoice" else CONTRACT_COLUMNS
        columns = [{"id": key, "label": label, "description": description, "kind": kind,
                    **({"date_order": "DMY"} if kind == "date" else {})}
                   for key, label, description, kind in definitions]
        manifest["cases"].append({"id": case["id"], "file": filename,
                                  "columns": columns, "labels": labels})
    (root / "full-pipeline-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Created four sectioned fixtures; original corpus and labels unchanged.")


if __name__ == "__main__":
    build()
