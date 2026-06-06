# Template Picker Flow Redesign

**Date:** 2026-06-06
**Status:** Approved pending spec review

## Problem

The "From template..." flow opens a dialog that carries its own prompt box on the
CONFIRM page, separate from the main Create prompt. A user who types a prompt on the
main screen, then opens the template flow, meets a second empty prompt box. Two prompt
entry points, a confusing flow, and the in-dialog generate / preview / render duplicate
surfaces the main panel already provides (status banner, Open file).

## Goal

Turn the dialog into a template PICKER. Selecting a template loads it onto the main
Create screen. The main Generate button then drives template generation from the single
main prompt, rendering directly to the "Save to" folder with the existing result
surfaces.

## Behavior

1. "From template..." is enabled only when Ollama is connected and the file type is
   PowerPoint (unchanged from the prior fix). It opens the picker.
2. Picker pages:
   - SELECTION: list built-in and user templates; "Upload a .pptx..." (import and
     hard-stop path unchanged); "Next".
   - CONFIRM: template name, slide-types summary, and the detection report for uploads.
     No prompt box. The button reads "Next".
3. Clicking CONFIRM's "Next" closes the dialog and loads the template into MainWindow.
   The panel button relabels to "From Template: selected".
4. Clicking the button again, loaded or not, reopens the picker. Picking a new template
   replaces the loaded one. Cancelling (X, hard-stop cancel) leaves any loaded template
   untouched.
5. Main Generate:
   - If a template is loaded AND file type is PowerPoint: run the template engine with
     the main prompt. Build the prompt from the loaded manifest, run pipeline.run (LLM,
     validate, one repair, render) off the UI thread, write the .pptx into the main
     "Save to" folder with the existing output-path naming, then show the result via the
     panel status banner and Open file button. No JSON preview.
   - Otherwise: the from-scratch path, exactly as today.
6. The loaded template clears (button reverts to "From template...") when either:
   - a template generate completes successfully, or
   - the file type is switched to anything other than PowerPoint.
7. A failed template generate keeps the template loaded for retry.

## Components

### TemplateDialog (simplified to a picker)
- Pages: SELECTION then CONFIRM. Removes PREVIEW and DONE.
- Removes: the second prompt box, in-dialog generate / preview / render, the
  generate_requested signal, the worker-result slots, and the generating-close guard.
- Adds: `template_selected(manifest, template_dir, name)` emitted when CONFIRM's "Next"
  is clicked, followed by accept().
- Keeps: selection list, manifest summary, detection-report display, upload + import +
  HardStopDialog routing.

### TemplateGenerateWorker
- Runs the full pipeline (generate and render) off the UI thread.
- Constructor: (manifest, template_dir, user_request, out_path, model, client).
- run(): build_prompt then pipeline.run, emit completed(path: str, issues: list[str]);
  map OllamaTimeout / Connection / Generation, ParseError, and render faults
  (ValueError, ManipulationError) to friendly failed(message) strings.

### CreatePanel
- Add `file_type_changed(str)` signal, emitted when the file-type combo changes.
- Add `set_template_loaded(bool)` to switch the button text between "From template..."
  and "From Template: selected".
- Button click still emits template_requested(); enable logic unchanged (connected and
  PowerPoint).

### MainWindow
- State: `_loaded_template` = {manifest, dir, name} or None, plus the existing template
  worker and thread members.
- `_on_template_requested`: guard on a running model (unchanged), open the picker,
  connect `template_selected` to `_on_template_selected`, exec.
- `_on_template_selected(manifest, dir, name)`: store `_loaded_template`, call
  `panel.set_template_loaded(True)`.
- `_on_file_type_changed(file_type)`: if file_type is not PowerPoint and
  `_loaded_template` is set, clear it and call `panel.set_template_loaded(False)`.
- `_on_generate_requested(file_type, save_path, prompt)`: if `_loaded_template` is set
  and file_type is PowerPoint, start the template worker (out_path from save_path and
  prompt); else from-scratch as today.
- Template worker result: completed(path, issues) shows success on the panel + Open file
  + clears `_loaded_template` + set_template_loaded(False); failed(msg) shows the error
  on the panel and keeps the template loaded.

## Data flow (template generate)

main prompt + loaded {manifest, dir} -> build_prompt -> TemplateGenerateWorker (QThread)
-> pipeline.run (LLM -> validate -> repair x1 -> render to out_path) -> completed(path,
issues) -> CreatePanel status banner + Open file -> clear loaded state.

## Error handling

Reuse the existing friendly-message conventions. The worker maps:
- OllamaTimeoutError -> "The AI engine timed out. It may be busy; please try again."
- OllamaConnectionError -> "The AI engine stopped responding. Please check Ollama is running."
- OllamaGenerationError -> "The AI returned an unexpected response. Please try again."
- ParseError -> "The AI could not produce a valid slide structure after retrying. Try a simpler request or a different model."
- ValueError (template open) -> "The template file could not be opened as a PowerPoint file."
- ManipulationError (render I/O or manifest/template mismatch) -> "Could not save the presentation, or the template and its manifest are out of sync."

Render uses temp then rename, so no partial file is left on failure. Failures keep the
loaded template.

## Testing (TDD)

- CreatePanel: `set_template_loaded` toggles the button text; `file_type_changed` is
  emitted on type change; click still emits template_requested; enable logic still
  connected and PowerPoint.
- TemplateDialog: CONFIRM has no prompt box; "Next" emits template_selected with the
  chosen manifest / dir / name; cancel emits nothing; hard-stop path intact; selecting a
  built-in then Next works.
- TemplateGenerateWorker: pipeline.run success emits completed(path, issues); each mapped
  exception emits the right failed message (mock the client or pipeline).
- MainWindow: routing (loaded + PowerPoint -> template worker; loaded + non-PowerPoint ->
  from-scratch; not loaded -> from-scratch); template_selected stores and relabels;
  file-type off PowerPoint clears and relabels; template completed clears and relabels and
  shows the file; template failed keeps the template loaded.

## Out of scope

- No JSON preview / edit step (removed).
- No change to the from-scratch Word / Excel / PPTX path.
- No change to the import / breakdown / hard-stop logic.
