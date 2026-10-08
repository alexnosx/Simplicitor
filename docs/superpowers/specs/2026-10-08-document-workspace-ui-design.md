# Simplicitor first-release UI design

Release scope, default mode, permitted inputs/outputs, record modes, review rules, and metrics are owned by [PRD.md](../../../PRD.md). [Architecture](2026-10-08-document-architecture-design.md) describes the backing components; [project status](../../PROJECT_STATUS.md) records current implementation.

## Create workspace

Mount a Create workspace in MainWindow rather than the old equal Create/Edit panes. Do not mount EditPanel. Keep the existing top-bar model state and Settings, with shared styling from defaults.py.

Within Create, use a local choice between From source files and From prompt. Source extraction is the initial view; From prompt hosts the existing CreatePanel, including its current output choices and PowerPoint template picker. Its signals continue to route to the existing workers.

## Source extraction view

Use the available width for source inspection and the eventual workbook grid, with a compact control area for the request and schema.

1. Add files through a multi-file picker or drop area. List each source separately, including same-named files; do not use the legacy upload-copy path.
2. Show the request and the output appropriate to the PRD release scope. Offer the PRD record modes with file mode selected initially.
3. Show editable column names, descriptions, and type choices. Text is the safe initial type. Ask for numeric/date interpretation only when relevant. Confirm columns before model extraction.
4. In table mode, inspect detected tables and confirm the header/column mapping. If no supported table exists, show the issue and let the user change mode or sources.
5. Show per-source/page issues, limit information, and structural coverage. Unreadable pages remain visible throughout review.

Use familiar controls and short labels; model/context parameters belong outside the document workflow. Preserve Segoe UI, the light theme, restrained borders, and existing status styling.

## Extract and review

Run processing through the extraction worker. Disable duplicate submission and source/schema changes during a job. Show source/section progress, retained instructions, and cooperative cancellation state. Failed jobs keep the user's setup for correction.

Read the saved candidate into a Qt table model. Data is read-only; flagged cells are highlighted and selecting a cell populates a nearby Evidence panel with the proposed value, quote, anchor, and reason. Coverage issues remain visible above the grid. Review must not display a newly regenerated approximation of the candidate.

Revising setup creates another candidate and removes approval. The final action chooses a new file and approves the current candidate. Flagged or partial results require explicit acknowledgement. A collision or save failure retains the review and offers recovery; it never shows saved success.

Source anchors and quotes provide the evidence view, following [PRD review requirements](../../../PRD.md#first-release-ui).

## Historical mockup

[document-workspace.html](../../design/document-workspace.html) is an earlier interactive concept for the later editing direction. It is not the first-release screen specification and does not implement extraction. Keep it as design history; do not build its Edit mode for this release.

## UI acceptance

The [plan](../plans/2026-10-08-first-release-extraction.md) owns exact checks. Observe the PRD default mode and visibility, preserved legacy Create/template routing, column confirmation, evidence selection, partial-output acknowledgement, cancellation, collision handling, and agreement between the saved workbook and grid.
