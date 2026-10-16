# Simplicitor document workspace UI, 2.3.0

[PRD.md](../../../PRD.md) owns scope, hardware recommendations, language, warning copy, record semantics, review/save rules and acceptance values. [Architecture](2026-10-08-document-architecture-design.md) owns technical detail; [project status](../../PROJECT_STATUS.md) records verification. The [Create mockup](../../design/document-workspace.html) and [2.2.0 plan](../plans/2026-10-12-release-2.2.0.md) retain the built-in-only Create design. The [approved Edit mockup](../../design/edit-document.html), [Edit design](2026-10-13-edit-for-word-design.md) and [2.3.0 plan](../plans/2026-10-13-release-2.3.0.md) define the implemented Word editor.

## Modes and layout

TopBar offers **Create new** (default), **Edit document**, local AI status and Settings. Select the local model in Settings. Show the shared product version next to the name; the window title and Settings use the same version. Edit document mounts the selective Word editor below and cannot invoke the legacy manipulator. Disable mode switching and Settings while work is active.

MainWindow mounts CreateScreen and EditScreen. Keep Segoe UI, body text of at least 11 pt, the light theme, white cards, darker borders and shared values from defaults.py. Number each workspace box by purpose. Scope the central grey background to the central widget, so card labels retain their card background. Intentional blue, yellow and green notices keep their colours. Describe cards and Review/Evidence panes use roughly 65/35 space; bounded source and coverage lists keep controls accessible.

The step indicator follows the active option: Write shows Describe and Save; Pull shows Describe, Choose columns, Review and save, even before files are added. Success opens the Saved page. A mode change retains the Create setup when idle.

Use one /api/show parameter-size lookup for the selected model to show the PRD's dismissible, non-blocking warning when appropriate. Ignore stale results. Lookup must not freeze the UI or disable generation; no hardware checks are added. A missing local engine shows an explanation and Retry.

## Azure desktop presentation (2.5.0 feature branch)

The [approved Azure reference](../../design/azure-desktop.html) and [2.5.0 wording table](../plans/2026-10-16-release-2.5.0.md#wording-decisions-for-alex) govern the refreshed presentation. Task 4 source evidence is in [Azure acceptance](../../design/azure-desktop-acceptance.md); Claude's review and Alex's Qt approval are required before merge.

Use the shared Azure palette with a blue brand row, actual app icon, name/version, **Powered by your local LLM** directly under the name, and **Your documents. Your computer. Your control.** on the right. Keep a white navigation row below. The footer keeps **Your documents and the AI processing stay on your computer.** and displays the actual selected model as plain, elided text with its full tooltip, empty when none is selected.

Create's Describe caption is **What would you like to work on?**, with **Local processing** as an informational pill. Keep later-step captions. Describe's card body can scroll while its shared primary action row remains outside the scroll area. Preserve **Only your description is used.** for Write and **Source files are kept unchanged** for Pull, without a new gate. Source-format and scanned-PDF warnings keep their existing exact wording.

At 1024 x 640, columns and Excel/Word review use scrollable bodies with readable minimum view heights. Acknowledgement, Save to Excel and Word review actions remain reachable by mouse, focus and scrolling. Do not compress the grid or overlap controls to make everything fit. At 1280 x 800, extracting still shows four complete column rows. Keep at least 11 pt body/input text and native operating-system dialogs. Styling does not change processing, cancellation, closing or save rules.

## Describe

At the top, offer **Write a new document** ("Word, PDF, PowerPoint or Excel, from a description.") and **Pull information into Excel** ("Read your Word files or PDFs and make an Excel table."). Show only the active option's inputs. The chosen option determines the request, independently of attached files.

Writing shows **1. Describe the document you need** and **2. Choose the output**. File-type choices are Word, PDF, Excel and PowerPoint, retaining backend identifiers internally. Use four checkable format buttons with names/extensions, light blue hover/chosen states and a blue focus border. **Create file** sends only type, folder and description to the existing generator. PDF follows the Word response structure.

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

## Edit your Word document

Show the title **Edit your Word document** and subtitle **Select a part, describe the change, then review it before saving a new file.** The steps are Open, Select, Describe, Review and Save.

1. **Open your Word document.** Show **Drop a .docx here, or browse for a Word document.** and **Browse .docx** with the native Word file filter. During reading, keep **Reading the document...** and Cancel in this step. A refusal shows its message and keeps the drop zone. After opening, show **You are working on: <name>**, **Choose another file**, and **Original in <folder>. Your original will not be overwritten.**
2. **Select the part to edit.** A scrollable, virtualized reading view shows headers, body and footers in order, with controlled heading size, bold/italic and list bullets. Tables are read-only grids and pictures are placeholders. Document characters are plain text, including apparent HTML. Grey rows say Read-only; hover or click gives the reason. Click selects a whole editable body paragraph; Shift-click or a drag extends from the first click. A range cannot cross a table or read-only paragraph; a rejected range keeps the previous selection. Show the selected count, Clear selection and Edit this part. The PRD's selection limit disables Edit this part when exceeded.
3. **Describe the change.** Keep the selected part visible and read-only beside the description. Use the mockup example placeholder and the PRD's description limit. Review change requires a nonblank description and selected local model. With no model, show the warning and Open Settings. Back to selection retains the description. While proposing, show **The local AI is working...** and Cancel; freeze Settings, modes and Choose another file.
4. **Review the selected part.** Show Before and After using the same plain-text delegate; changed characters in After are light green. Removed or replaced text in Before has a pale red background, dark red text and a strike-through, retaining bold/italic and literal text. When present, explain **Removed or replaced text is red and crossed out in Before.** Above the comparison, also identify the number of original paragraphs removed or merged; an intentional merge is allowed even when no words disappear. Hide this notice for insertion-only changes, and clear it and the markers on reset or replacement review. Show the Track Changes notice when appropriate. Keep **Only the selected part is shown. Longer text can change page breaks.** Use this change goes to Save; Try again keeps the description and increments the attempt; Cancel returns to selection with the selection kept.
5. **Save as a new file.** Suggest the PRD's filename beside the original in the native .docx Save As dialog, with normal overwrite confirmation. Cancelling the dialog retains the candidate. Ordinary retry/destination outcomes choose again after the worker joins; an original-change failure resets to Open, and a write failure retains Save. Success shows the saved path, **The original is unchanged.** and only **Open another document**, with one change per saved file.

Choose another file and drops pick the replacement first. A selection, description or unsaved candidate then requires **Discard your changes to <name>?**, with **Discard** and default **Keep editing**. Keep editing preserves the session and scroll position. Switching to Create asks the same question and restores the Edit mode button when rejected. An accepted discard resets session ownership; busy actions and late results are guarded.

Closing cancels reading/proposals and waits for an accepted save without blocking the event loop. Show **Waiting for local processing to stop before closing...** on Edit when it is visible. A failed accepted save withdraws closing and leaves its failure on Save with the candidate retained, without an automatic dialog covering the error; discovery resumes. Source and destination checks still apply before every save.

## Checks

The [2.2.0 plan](../plans/2026-10-12-release-2.2.0.md#part-d-tasks-as-built) and [project status](../../PROJECT_STATUS.md#220-part-d-verification) record retained Create behavior. The [2.3.0 as-built record](../plans/2026-10-13-release-2.3.0.md#part-b-tasks-as-built) records the Edit selection, discard, review, worker, busy and close checks and its pre-merge corrections. scripts/capture_screens.py stages 16 synthetic 1280x800 views, including four Edit states, using shared app styles. The [model report](../../evaluation/2.3.0-edit-model-check.json) and [Word check](../../builds/2.3.0-word-check.json) record the separate Part C checks. Earlier [C2.7 evidence](../../builds/2.1.0-ui-ci.json) retains historical qualification. These checks do not establish every native UI interaction or a clean-machine walkthrough.

Table-row extraction and Excel/PowerPoint editing remain later work under the PRD.
