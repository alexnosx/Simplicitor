# Simplicitor document workspace UI, 2.2.0

[PRD.md](../../../PRD.md) owns scope, hardware recommendations, language, warning copy, record semantics, review/save rules and acceptance values. [Architecture](2026-10-08-document-architecture-design.md) owns technical detail; [project status](../../PROJECT_STATUS.md) records verification. The [approved mockup](../../design/document-workspace.html) and [2.2.0 plan](../plans/2026-10-12-release-2.2.0.md) define this implemented screen and its B3 drop outcome.

## Modes and layout

TopBar offers **Create new** (default), **Edit document**, local AI status and Settings. Select the local model in Settings. Show the shared product version next to the name; the window title and Settings use the same version. Edit document says Edit for Word arrives in Simplicitor 2.3.0 and editing was turned off while a safer editor is built, with a return to Create new. It cannot invoke the legacy manipulator. Disable mode switching and Settings while work is active.

MainWindow mounts one CreateScreen. Keep Segoe UI, body text of at least 11 pt, the light theme, white cards, darker borders and shared values from defaults.py. Number each workspace box by purpose. Scope the central grey background to the central widget, so card labels retain their card background. Intentional blue, yellow and green notices keep their colours. Describe cards and Review/Evidence panes use roughly 65/35 space; bounded source and coverage lists keep controls accessible.

The step indicator follows the active option: Write shows Describe and Save; Pull shows Describe, Choose columns, Review and save, even before files are added. Success opens the Saved page. A mode change retains the Create setup when idle.

Use one /api/show parameter-size lookup for the selected model to show the PRD's dismissible, non-blocking warning when appropriate. Ignore stale results. Lookup must not freeze the UI or disable generation; no hardware checks are added. A missing local engine shows an explanation and Retry.

## Describe

At the top, offer **Write a new document** ("Word, PDF, PowerPoint or Excel, from a description.") and **Pull information from documents into Excel** ("Read your Word files or PDFs and make an Excel table."). Show only the active option's inputs. The chosen option determines the request, independently of attached files.

Writing shows **1. Describe the document you need** and **2. Choose the output**. File-type choices are Word, PDF, Excel and PowerPoint, retaining backend identifiers internally. Use light blue for hovered/chosen dropdown items and a blue focus border. **Create file** sends only type, folder and description to the existing generator. PDF follows the Word response structure.

For PowerPoint, **Use a template** is a blue secondary button with hover, pressed and chosen states. The picker offers only business_pitch and technical_overview and keeps structure confirmation. After selection, show **Template: <name>** and **Clear**. A real file-type change away from PowerPoint clears the choice; switching to Pull and back retains it.

Pulling shows **1. Describe the information you need** and **2. Add your source files**, with the extraction prompt hint and one-row-per-file explanation. It always produces Excel and has no writing file-type, folder or template controls. **Next: choose columns** requires a request, files and completed inspection. Removing all files keeps the Pull option and disables this action.

Retain writing description/type and pulling request/files separately during switching. Leaving Pull clears columns, review and acknowledgement through setup_changed and discards the owned job. Switching is blocked during any work; late results for the other option are ignored. Editing the request, sources or columns invalidates confirmation/review as before; each extraction rerun discards its previous owned job.

## Source files and reading problems

Offer browse/drop for DOCX and PDFs with selectable text on Pull's Describe step while idle. Keep one removable row per attachment; same-named or identical files remain separate. Display each filename once and retain its accessible name. Reading is off-thread. Rows show **Reading**, **Ready** or **Partly read**; the last means that file has reading problems. Failed reading retains setup and offers **Read files again**.

Name detected text boxes, tracked text (including moves), form fields, fields, embedded documents, footnotes/endnotes and nested tables as not read. Tracked formatting/row changes instead need review in Word while their text is retained. Present problems in a bounded, scrollable box beginning:

> Some information may be missing from the table. Check these problems before you use it:

Show reading/extraction progress on file rows and the main action, as well as the footer status. Forward the pipeline's source ID so duplicate names cannot confuse progress. The busy progress list scrolls to the active file; its compact row shows filename, reading state and processed-unit progress.

## Choose columns

Suggest columns uses the request and first source. Show a compact editable table with names, descriptions and human-readable types: Text, Whole number, Decimal number and Date. Keep add/remove controls and per-column details. Apply recognized proposal types, otherwise text. Prefill English number settings; validate supported separators and show day/month order only for ambiguous numeric dates in date columns.

Title the box **3. Choose columns**. Retain at least four full rows at 1280x800 while extracting; the compact File progress box must not squeeze them out. A disabled selected row uses light blue with readable text.

**Extract to Excel** confirms the current columns and starts extraction in one action. Require at least one column, descriptions, valid separators and any needed date order. If inspection is still pending, resume confirmation only after successful inspection. Failed suggestions retain the setup and allow manual columns or retry; they cannot start extraction. Back to Describe keeps the editable setup.

## Review and save

Freeze setup and prevent duplicate submission while busy. Show file/section progress and cooperative cancellation state. Retain instructions after failure; invalidate old review on rerun, cancellation or failed replacement. A late result cannot revive cancelled review.

Title the cards **4. Review your table** and **5. Where this value came from**. Build the read-only grid from saved Data cells. It starts with File and omits Record; Record stays in the workbook and Evidence. Display saved types and number/date formats, including decimal trailing zeros. Highlight flagged proposed values and absent blanks. Selecting a Data cell shows its saved verbatim value/proposal, source text, location and reason to check. Use plain text for all model/source text, filenames and paths, never rich-text interpretation.

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

The [2.2.0 plan](../plans/2026-10-12-release-2.2.0.md#part-d-tasks-as-built) and [project status](../../PROJECT_STATUS.md#220-part-d-verification) record route/input isolation, busy/stale-result guards, job invalidation, file states/progress, template controls and style checks. scripts/capture_screens.py stages 13 synthetic 1280x800 views using shared app styles. Earlier [C2.7 evidence](../../builds/2.1.0-ui-ci.json) retains the source walkthrough and hosted MSI qualification. These checks do not establish every native UI interaction, model accuracy or a clean-machine walkthrough.

Edit for Word in 2.3.0 is next, before table-row extraction, under a separate approved mockup, technical design and plan. Its C2 mockup and editor implementation are not part of 2.2.0.
