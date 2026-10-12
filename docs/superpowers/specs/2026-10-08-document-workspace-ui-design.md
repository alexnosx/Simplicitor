# Simplicitor document workspace UI, 2.1.0

[PRD.md](../../../PRD.md) owns scope, hardware recommendations, language, warning copy, record semantics, review/save rules and acceptance values. [Architecture](2026-10-08-document-architecture-design.md) owns technical detail; [project status](../../PROJECT_STATUS.md) records verification. The [approved mockup](../../design/document-workspace.html) and [2.1.0 plan](../plans/2026-10-09-release-2.1.0.md) define this implemented screen.

## Modes and layout

TopBar offers **Create new** (default), **Edit document**, local model selection and Settings. Edit document is an explanatory page for deferred selective editing, with a return to Create new. It cannot invoke the legacy manipulator. Disable mode switching and Settings while work is active.

MainWindow mounts one CreateScreen. Keep Segoe UI, the light theme, white cards, restrained borders and shared values from defaults.py. Scope the central grey background to the central widget, so card labels retain their card background. Intentional blue, yellow and green notices keep their colours. The Describe cards and Review/Evidence panes use roughly 65/35 space; bounded source and coverage lists keep controls accessible.

The step indicator retains the current step. Without sources it shows Describe and Save; with sources it shows Describe, Choose columns, Review and save. Success opens the Saved page. A mode change retains the Create setup when idle.

Use one /api/show parameter-size lookup for the selected model to show the PRD's dismissible, non-blocking warning when appropriate. Ignore stale results. Lookup must not freeze the UI or disable generation; no hardware checks are added. A missing local engine shows an explanation and Retry.

## Describe

The left card contains the request, File type and Save to folder. File-type choices are Word, Excel, PowerPoint and PDF; display simple names while retaining the existing generator identifiers internally. Without sources, **Create file** uses the existing generation worker and saves to the selected folder. PowerPoint offers **Use a template**, preserving its picker/import/generation route. PDF follows the Word response structure.

The right card contains optional DOCX/text-layer PDF sources, browse/drop, one removable row per attachment, reading status and coverage. Same-named or identical files remain separate attachments without legacy upload copying. Display each filename once and keep its accessible name. Accept drops only on Describe while idle.

Adding sources forces Excel and disables the file-type choice, hides prompt-generation folder/template controls, and shows the explanation that files become an Excel table and reports from files come later. The primary action becomes **Next: choose columns**. Removing the last source restores the prompt route. Inspect sources off the UI thread; show readable problems and provide Read files again after reading failure.

Request, source or model changes invalidate column confirmation and prior review. Editing columns clears review and acknowledgement. Each extraction rerun discards the previous owned job before replacing its candidate.

## Choose columns

Suggest columns uses the request and first source. Show a compact editable table with names, descriptions and human-readable types: Text, Whole number, Decimal number and Date. Keep add/remove controls and per-column details. Apply recognized proposal types, otherwise text. Prefill English number settings; validate supported separators and show day/month order only for ambiguous numeric dates in date columns.

**Extract to Excel** confirms the current columns and starts extraction in one action. Require at least one column, descriptions, valid separators and any needed date order. If inspection is still pending, resume confirmation only after successful inspection. Failed suggestions retain the setup and allow manual columns or retry; they cannot start extraction. Back to Describe keeps the editable setup.

## Review and save

Freeze setup and prevent duplicate submission while busy. Show file/section progress and cooperative cancellation state. Retain instructions after failure; invalidate old review on rerun, cancellation or failed replacement. A late result cannot revive cancelled review.

Build the read-only grid from saved Data cells. It starts with File and omits Record; Record stays in the workbook and Evidence. Display saved types and number/date formats, including decimal trailing zeros. Highlight flagged proposed values and absent blanks. Selecting a Data cell opens **Where this value came from**, with its saved verbatim value/proposal, source text, location and reason to check. Use plain text for all model/source text, filenames and paths, never rich-text interpretation.

Translate internal anchors and issue codes into readable labels. Display coverage separately in a bounded, scrollable view with file and page/unit locations. There is no cell editor or PDF preview pane.

Show the acknowledgement checkbox whenever candidate.issues is not empty. Choose its label by the issues present:

- **I have checked the highlighted values**
- **I have checked the reading problems**
- **I have checked the highlighted values and reading problems**

**Save to Excel** remains disabled until required acknowledgement. Back to columns resets acknowledgement and allows changes and a rerun. Every extracted cell from a sectioned source is highlighted, including valid typed values and blanks. This review policy alone is not a reading problem; whole-file validation stays unchanged.

## Native export, Saved and close

Save to Excel opens the standard Windows Save As dialog limited to .xlsx, retaining normal overwrite confirmation and source-path refusal. Cancellation and copy/write/rename failure keep review and cannot show success. Successful prompt generation or Excel export shows the filename, Open file and Create another file on Saved. Prompt generation also reports the chosen location; Excel export reports that the workbook was saved. Create another file returns to Describe and clears the previous result.

Normal close cooperatively cancels work or waits for an accepted save, retaining worker ownership until native thread completion. Cleanup then deletes the owned job. Startup cleanup follows the PRD retention rule without a recovery screen. No UI wait may prevent the event loop from handling worker completion.

## Checks

The [2.1.0 plan](../plans/2026-10-09-release-2.1.0.md) defines route/state, plain-label, column, saved evidence, acknowledgement, cancellation, overwrite, source-refusal and cleanup checks. [C2.7 evidence](../../builds/2.1.0-ui-ci.json) records the synthetic source walkthrough and hosted MSI qualification. The [C2 UI follow-up](../../builds/2026-10-12-c2-ui-followup.json) records six refreshed 1280x800 screenshots, rendered label-background checks and local tests. These samples do not claim every native layout or a clean-machine walkthrough.
