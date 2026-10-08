# Simplicitor first-release UI design

[PRD.md](../../../PRD.md) owns scope, supported hardware/language, warning copy, record semantics, review/save rules, and acceptance values. [Architecture](2026-10-08-document-architecture-design.md) owns technical detail; [project status](../../PROJECT_STATUS.md) records current implementation.

## Create workspace

Mount CreateWorkspace in MainWindow; do not mount EditPanel. Keep the top-bar model state, Settings, Segoe UI, light theme, restrained borders, and shared styling from defaults.py.

Within Create, offer From source files and From prompt. Source extraction is the initial view. From prompt hosts the existing CreatePanel, including current output choices and PowerPoint template picker, routing to its existing workers.

Show the PRD's dismissible, non-blocking warning for an undersized or unknown selected model. Update it on model selection and metadata results, not only when a model becomes loaded. Metadata lookup must not freeze the UI or disable generation.

## Sources and proposed columns

1. Add DOCX/PDF files through a multi-file picker or drop area. List each separately, including same-named files, without legacy upload copying.
2. Enter the extraction request. Explain that each file will produce one spreadsheet row; do not show a record-mode picker or table/header mapping controls.
3. Inspect sources off the UI thread, show page/coverage issues, and ask the model to propose columns from the request and first source. Label this action **Suggest columns**.
4. Show proposed names, descriptions, and types in an editable list with add/remove actions. Apply the proposal's recognized type, otherwise text. English number settings are prefilled; per-column overrides stay in a compact details control.
5. Ask for day/month order only when source inspection finds ambiguous numeric dates for a date column. English month-name dates need no order question.
6. Require column confirmation before **Extract**. If proposals fail, retain sources/request and allow manual columns or a retry. No failed suggestion starts extraction.

A revised request/source list clears column confirmation and any prior review. Column edits clear review and acknowledgement. A rerun uses the same job candidate rather than adding a version picker.

## Extract and review

Disable duplicate submission and setup changes while busy. Show file/section progress, retain instructions after failure, and show cooperative cancellation state. Invalidate the previous review when a rerun starts; a late or failed run cannot revive it.

Build the read-only grid from the saved workbook. Valid fields use their saved typed values. Flagged cells show saved proposed values, highlighted; absent proposals remain highlighted blanks. Selecting any Data cell opens its saved quote, anchor, and issue in the Evidence panel. Coverage issues stay visible above the grid.

There is no PDF rendering pane, cell editor, approval token, or candidate-version selection.

## Save As and close

Use **Save As** for the current reviewed candidate. If fields or coverage are flagged, require acknowledgement before opening the standard Windows dialog. Keep normal overwrite confirmation enabled. Refuse a source path and show an actionable message.

Dialog cancellation keeps review. Copy/write/rename failure keeps review and never reports success; the user can choose another destination. Successful save reports the chosen output. Re-running clears the acknowledgement.

Normal close cancels/waits for work as needed and deletes the job folder. Startup cleanup is automatic under the PRD retention rule, without a crash-recovery screen.

## Historical mockup and checks

[document-workspace.html](../../design/document-workspace.html) remains an earlier concept for later editing, not this screen specification.

The [plan](../plans/2026-10-08-first-release-extraction.md) defines tests for default mode, selected-model warnings, column suggestions/confirmation, preserved Create/template routing, saved proposed values/evidence, flagged-export acknowledgement, cancellation, native overwrite confirmation, source-path refusal, and cleanup.
