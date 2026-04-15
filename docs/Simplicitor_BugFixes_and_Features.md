# Simplicitor - Bug Fixes and Feature Updates

## Priority: CRITICAL BUGS (fix these first)

### BUG-1: Generate button stops working after first successful generation
**Symptom:** After generating one file successfully, clicking Generate again does nothing. No logs are captured. Changing file type or prompt does not help. Only restarting the app fixes it.
**Root cause:** The generation worker's completion signal does not reset the internal "generation in progress" flag. The click handler checks this flag and silently returns when it thinks a generation is already running. The log confirms: "Generate requested while previous generation still running; ignoring."
**Fix:** In main_window.py (or wherever the generation flow is managed), ensure that BOTH the `completed` AND `error` signal handlers from generate_worker reset the generation-in-progress flag to False. Check that:
1. `self._generating = False` (or equivalent flag) is set in BOTH `_on_generation_completed()` AND `_on_generation_error()`
2. The Generate button is re-enabled in both handlers
3. The spinner/progress indicator is stopped in both handlers
4. Test: generate a file, then immediately generate another without restarting. Must work.

### BUG-2: PowerPoint generation hangs after LLM response is received
**Symptom:** LLM returns valid JSON for PowerPoint, the parser succeeds, but the file writing step hangs indefinitely. Word and Excel generation complete fine.
**Root cause:** In pptx_generator.py, likely one of these:
- A slide with `"type": "section"` and `"bullets": []` (empty array) causes an infinite loop or blocking call
- An uncaught exception during slide creation that the worker thread swallows without emitting the error signal
**Fix:**
1. In pptx_generator.py, add explicit handling for empty bullets arrays - skip bullet creation if the array is empty
2. Add handling for slides where "bullets" key might be missing entirely (section/title type slides often have no bullets)
3. Wrap the entire file writing block in try/except and log any exception before re-raising
4. In generate_worker.py, ensure that ANY exception during file writing emits the error signal (not just Ollama errors)
5. Add a debug log line AFTER the file is written: "PowerPoint file written successfully"
6. Test: generate a PowerPoint with a prompt that produces title slides and section dividers (which may have empty or no bullets)

### BUG-3: Model selector shows "No model selected" despite connected status
**Symptom:** The top bar shows green dot + "Connected" but the model dropdown says "No model selected". Intermittent - sometimes it works (Image 1), sometimes it doesn't (Image 2).
**Root cause:** Race condition. The connection status is set to "Connected" before the model list API call (/api/tags) returns and populates the dropdown. Or: the model list call succeeds but /api/ps (currently loaded model) returns empty, so nothing is pre-selected.
**Fix:**
1. In the connection flow, do NOT set status to "Connected" until BOTH /api/tags AND /api/ps have returned
2. If /api/tags succeeds but /api/ps returns no loaded model, populate the dropdown but select the first available model (or show "Select a model" as the default prompt)
3. Log the model list and selected model on every successful connection for debugging
4. Test: start app with Ollama running, verify model is always populated. Stop and restart Ollama, verify model repopulates on reconnect.

---

## Priority: HIGH BUGS

### BUG-4: File manipulation timeout on document editing tasks (4B model)
**Symptom:** Editing a Word document with prompt "add one more page and describe cloud LLMs capabilities" times out at 60 seconds. Ollama is running fine. Simple Excel generation works.
**Root cause:** The manipulation workflow sends the entire extracted file content plus the user prompt to the LLM. For a multi-page document on a 4B model, the combined input may approach or exceed the model's effective processing capacity, causing response time > 60 seconds.
**Fix:**
1. Increase the manipulation timeout to 120 seconds (manipulation tasks are inherently larger than generation tasks because they include file content)
2. Before sending to Ollama, estimate the token count of the extracted text (rough heuristic: word count * 1.3). If it exceeds 2000 tokens, truncate and show a warning: "This file is large. Processing the first portion only."
3. Add a progress indicator that shows elapsed time during manipulation so the user knows something is happening
4. If the timeout is hit, the error message should say: "This task took too long. Try a simpler prompt or use a larger model." (not "AI engine stopped responding" which implies Ollama is broken)
5. Test: upload a multi-page document on a 4B model, attempt manipulation. Should either succeed with more time or fail with a helpful message.

### BUG-5: Duplicate files in upload list
**Symptom:** The same file appears multiple times in the uploaded files list when re-uploaded (visible in Image 2: same .docx appears 3 times with different timestamps).
**Fix:**
1. When a file is uploaded, check if a file with the same name already exists in the uploads directory
2. If it does: overwrite the existing copy in the uploads directory and update the existing entry's timestamp in the file list (move it to the top)
3. Do NOT add a new entry to the list
4. Test: upload a file, upload the same file again. List should show one entry with updated timestamp.

---

## Priority: FEATURES (implement after all bugs are fixed)

### FEATURE-1: Clear prompt after successful operation
**Requirement:** After a file is generated or saved successfully, clear the prompt text box and prepare for a new request.
**Implementation:**
1. In the generation completed handler: clear the prompt QPlainTextEdit, reset the character counter to "0 / 2000"
2. In the manipulation completed handler: clear the prompt QPlainTextEdit, reset the character counter to "0 / 2000"
3. Do NOT clear the prompt on error (user may want to retry with the same prompt)
4. Do NOT clear the file type selector or save location (user likely wants to generate another file of the same type)
5. Do NOT clear the selected file in the Edit panel (user may want to apply another prompt to the same file)
6. Test: generate a file successfully, verify prompt clears. Fail a generation, verify prompt is preserved.

---

## Execution Order

1. BUG-1 (Generate button stuck) - blocks all further testing
2. BUG-2 (PowerPoint hang) - blocks PowerPoint testing
3. BUG-3 (Model selector race condition) - user trust issue
4. FEATURE-1 (Clear prompt on success) - quick win, improves flow
5. BUG-5 (Duplicate uploads) - annoying but not blocking
6. BUG-4 (Manipulation timeout) - requires careful timeout and messaging tuning
