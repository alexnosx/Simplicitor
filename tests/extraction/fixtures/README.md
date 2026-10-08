# Synthetic extraction corpus

authored_cases.json contains separately authored source text and expected field values. scripts/build_extraction_fixtures.py renders pages into real DOCX/PDF files and copies the labels into separate JSON files; it does not infer expected values from a reader or model.

The manifest supplies confirmed columns and numeric-date order. The evaluation sends only those columns and actual extracted source units to the model. Label files are loaded only by the scorer.

The corpus contains English invoices and contracts, DOCX header tables, page-spanning fields, competing totals/dates, leading-zero IDs, literal formula-like text, and deliberately absent values. Names, identifiers, and email domains are synthetic.

Regenerate from the repository root with .venv/Scripts/python.exe scripts/build_extraction_fixtures.py. The source recipe and canonical expected values must be reviewed independently when changing fixtures; do not alter labels to fit model outputs.

[Product requirements](../../../PRD.md#limits-and-evaluation-gates) own acceptance thresholds. The final production corpus must add oversized documents to exercise conditional sectioning.
