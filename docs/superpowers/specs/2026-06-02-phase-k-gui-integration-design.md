# Phase K: GUI Integration Design Spec

**Status:** PLAN-FIRST. Awaiting review + explicit Proceed before any implementation.
**Ground:** Phase J commit `3768d7d`.
**Model context:** Opus (GUI architectural judgment).
**Goal:** Wire the Phase A-J PPTX template-generation backend (`templates_engine/`) into Simplicitor's existing PySide6 GUI (`app/`), reusing the existing worker, status, error, and logging patterns. No parallel async system, no new logger, no new exception types.

This is the design spec. The bite-sized TDD implementation plan follows after Proceed, in `docs/superpowers/plans/`.

---

## 0. Headline findings (decisions you must rule on)

| # | Finding | Recommendation | Risk if ignored |
|---|---------|----------------|-----------------|
| F1 | `pipeline.generate` does not exist. The real entry is `pipeline.run`, which renders at the end of the validate-repair loop (pipeline.py:84,122). The flow needs validated JSON *before* render. | Extract a render-free `pipeline.generate(...)` from `run()`; make `run()` compose `generate()` + `render()`. One small backend change. | Either duplicate the repair loop in the GUI worker (violates "no second validator", DRY) or no editable preview at all. |
| F2 | The "error-dialog pattern" is the inline `StatusBanner` (NOTES.md:69-75), not a modal. Only modal exemplar is `SettingsDialog`. No `QMessageBox` anywhere in `app/`. | Hard-stop = a small `QDialog` (two buttons), matching SettingsDialog. In-dialog failures = an inline error label inside the TemplateDialog, mirroring StatusBanner semantics. | Inventing a QMessageBox-based surface diverges from the established pattern. |
| F3 | `ValidationError` never escapes the pipeline. Post-repair failure is raised as `ParseError` (pipeline.py:109-120). Edit-time validation returns `(False, errors)` with no exception. | Map ParseError (post-repair) and `(False, errors)` (edit-time) explicitly. There is nothing to catch named ValidationError at the worker boundary. | A `except ValidationError` clause that never fires; an uncaught ParseError. |
| F4 | The multi-step flow (select -> breakdown -> [hard-stop] -> confirm -> generate -> preview -> render) is wizard-shaped and branches. It does not fit the single-shot CreatePanel + StatusBanner pattern. | A dedicated modal `TemplateDialog(QDialog)` with a `QStackedWidget`, launched from a "From template..." entry point. The dialog owns its worker (justified extension of the moveToThread pattern). | Cramming a wizard into CreatePanel distorts it and breaks the symmetric two-panel layout. |
| F5 | Built-in templates do not exist until Phase L. `list_templates()` will return only user templates; the built-in root may be absent. The hard-stop's "use a built-in template" choice lands on an empty list today. | Wire the routing now. Selection page shows "No built-in templates available yet" when empty. Functionally complete at Phase L with zero rework. | Hard-stop routing appears broken in manual testing before Phase L. |

---

## 1. Attachment point

**Entry point:** A new secondary button `From template...` in `CreatePanel`, emitting a new signal `template_requested()`. `MainWindow` handles it, guards on `_current_model` (same guard as `_on_generate_requested`, main_window.py:226), and opens `TemplateDialog.exec()`.

**Why CreatePanel, not the TopBar:** "Create from a template" is a creation action; creation actions already live in CreatePanel (`generate_requested`). The TopBar is connectivity + settings only. This keeps semantic grouping intact and `MainWindow` remains the orchestrator that owns `_ollama_client` and `_current_model`.

**Why a dialog, not a third panel or a new file-type branch:**
- A third panel breaks the symmetric two-panel `QHBoxLayout` (main_window.py:84-90).
- CreatePanel already exposes `PowerPoint (.pptx)` as a *freeform* generation type (defaults.py:73). Branching that into a template mode would conflate two distinct PPTX paths inside one panel. The template path is a separate capability; keep it separate.
- The flow is genuinely multi-step with a branch (hard-stop) and an editable preview. A `QStackedWidget` inside a modal `QDialog` is the correct Qt idiom and reuses the `SettingsDialog` modal pattern.

**What MainWindow passes into TemplateDialog:** `self._ollama_client`, `self._current_model`, `self._settings`, and `parent=self`. Modality blocks re-entry; no extra in-progress flag needed at the MainWindow level.

---

## 2. User flow as an explicit state machine

States are pages in `TemplateDialog`'s `QStackedWidget`, except `HARD_STOP` (a separate modal sub-dialog) and `GENERATING` (a page with the async worker running).

```
[entry] -> SELECTION

SELECTION:
  - lists templates from config.list_templates() (builtin first, then user)
  - "Upload..." button -> QFileDialog.getOpenFileName(EDIT_FILE_FILTER-equivalent for .pptx)
  - on upload chosen: -> BREAKDOWN
  - on existing template chosen + Next: -> CONFIRM
  - "No built-in templates available yet" shown if builtin set empty (F5)

BREAKDOWN (synchronous, wait cursor):  [upload path only]
  - config.import_template(pptx_path)
  - returns {"status":"hard_stop", ...}     -> HARD_STOP
  - returns {"status":"ok", report, name}   -> refresh list, PRE-SELECT the new template, -> CONFIRM
  - raises ValueError / ManipulationError    -> inline error on SELECTION, stay on SELECTION

HARD_STOP (modal QDialog, two buttons, verbatim _HARD_STOP_MESSAGE):
  - "Use a built-in template"                 -> SELECTION (built-in focus)
  - "Cancel and rebuild with proper layouts"  -> close sub-dialog, stay on SELECTION (or reject whole flow)

CONFIRM (detection-report confirmation):
  - shows manifest-derived structure summary (always available via load_manifest)
  - plus the import `report` string and `lint_warnings` when the template was just uploaded
  - prompt input (QPlainTextEdit) for the deck request
  - "Generate" (enabled when prompt non-empty) -> GENERATING
  - "Back" -> SELECTION

GENERATING (async worker; Generate disabled; status label shows phase):
  - worker runs pipeline.generate(manifest, messages, model, client, progress=cb)
  - progress phases: generating / validating / repairing
  - completed(content_dict)                    -> PREVIEW
  - failed(message)                             -> inline error on CONFIRM, return to CONFIRM

PREVIEW (editable JSON):
  - QPlainTextEdit pre-filled with json.dumps(content_dict, indent=2)
  - "Render"  -> revalidate edited text (section 4); valid -> RENDER; invalid -> inline error, stay on PREVIEW
  - "Back"    -> CONFIRM

RENDER (synchronous, wait cursor):
  - render(manifest, validated_content, out_path, template_dir)
  - success -> DONE
  - raises ManipulationError / ValueError -> inline error on PREVIEW, stay on PREVIEW

DONE:
  - success message + "Open file" (os.startfile, same as CreatePanel._on_open_file)
  - "Close"
```

**"Uploaded pre-selected"** (from the objective): after a successful import, the SELECTION list is refreshed and the newly imported template is the current selection before advancing to CONFIRM.

---

## 3. Threading design

**Reused pattern:** the exact `QObject` worker + `moveToThread(QThread)` lifecycle from `main_window.py:250-267`:
`thread.started -> worker.run`; `worker.completed/failed -> thread.quit`; `thread.finished -> worker.deleteLater + thread.deleteLater`; an explicit in-progress guard.

**Ownership:** `TemplateDialog` owns the worker + thread (created on the main thread inside the modal dialog). This is a localized, justified extension of the existing pattern: the dialog is modal and self-contained, so it plays the orchestrator role `MainWindow` plays for the inline flows. Same lifecycle, different owner.

**What runs off-thread vs on-thread:**

| Operation | Thread | Rationale |
|-----------|--------|-----------|
| `pipeline.generate` (Ollama validate-repair loop) | Background worker | The only operation with unbounded latency. Mirrors `GenerateWorker` wrapping one LLM call. |
| `import_template` (breakdown: pptx parse + strip + manifest write) | Main thread, wait cursor | Bounded, local, sub-second to low-seconds. Wrapping it would add a worker class for no responsiveness benefit (YAGNI). Promotable to the same worker pattern later if large-deck profiling shows lag. |
| `render` (pptx save) | Main thread, wait cursor | Bounded and fast; `SettingsDialog` already does synchronous I/O on the main thread. |

**The single worker class:** `TemplateGenerateWorker(QObject)`.

```
Signals:
  started   = Signal()
  progress  = Signal(str)     # phase label: "generating" / "validating" / "repairing"
  completed = Signal(object)  # validated content dict {"slides": [...]}
  failed    = Signal(str)     # friendly message, no exception types or stack traces
```

`run()` calls `pipeline.generate(self._manifest, self._messages, self._model, client=self._client, progress=self._emit_progress)` and maps backend exceptions to `failed(msg)` (section 6). `_emit_progress(label)` just emits `self.progress`; it runs on the worker thread and only emits a Qt signal (queued delivery to the main-thread slot). It never touches a widget.

**No-QWidget-off-thread guarantee:** the worker touches zero widgets. Every widget mutation (page switches, status label, JSON editor, error label, wait cursor) happens in `TemplateDialog` slots connected to worker signals, which execute on the main thread via queued connections. The `progress` callback passed into `pipeline.generate` emits a signal rather than calling a widget method, preserving the boundary.

**Status set requested in the objective:** generating / validating / repairing come from the `progress` callback inside `pipeline.generate`; **rendering** is emitted by the dialog immediately before the synchronous `render`; **done** = `completed` slot reaching the DONE page; **failed** = `failed` slot. This requires `pipeline.generate` to accept the optional `progress` callback (section 7, a progress hook, not new logic).

**Cancellation:** out of scope (objective). The existing pattern provides none for in-flight LLM calls, and we add none. The modal dialog's Close is disabled while GENERATING; `closeEvent` quits/joins the thread with a bounded `wait()` exactly like `MainWindow.closeEvent` (main_window.py:409-422).

---

## 4. Editable JSON preview and re-validation

**Display:** PREVIEW page holds a `QPlainTextEdit` pre-filled with `json.dumps(content_dict, indent=2)`, where `content_dict` is the validated output from `pipeline.generate`.

**Re-validation on Render (reuses the pipeline's pydantic validator, no second validator):**
1. `try: parsed = json.loads(editor.toPlainText())` -> on `json.JSONDecodeError`, show inline error "That is not valid JSON: <line/col>", stay on PREVIEW, do not render.
2. `ok, result = validate_content(manifest, parsed)` (the same `templates_engine.validation.validate_content` the pipeline uses).
   - `ok is False`: show `format_validation_errors(result)` in the inline error area (the same formatter the repair loop uses), stay on PREVIEW, do not render.
   - `ok is True`: proceed to RENDER with `result` (the parsed/normalized dict, not the raw edited text).

**Why this is correct:** `validate_content` is the single source of truth for manifest conformance. The GUI calls it directly; it does not re-implement field checks. The edit-time failure path is value-returning (`(False, errors)`), so it is surfaced inline, never as an exception. This is the same validator, same formatter, same error strings the LLM repair loop sees.

**Assert-vs-raise discipline:** edited JSON is user input -> handled with `if/raise`-style control flow and inline surfacing, never `assert`. `assert` is reserved for design-held invariants (e.g. that `validate_content` returns a `{"slides": [...]}` shape on success), consistent with [[feedback_assert_vs_raise]].

---

## 5. Hard-stop routing

`HardStopDialog(QDialog)`: a small modal with the verbatim `_HARD_STOP_MESSAGE` (via `breakdown.hard_stop_result()["message"]`) and **exactly two** buttons:

| Button | Action |
|--------|--------|
| `Use a built-in template` | returns a result that routes `TemplateDialog` back to SELECTION with built-in focus |
| `Cancel and rebuild with proper layouts` | returns a result that closes the sub-dialog; the flow stays on SELECTION |

No theme-extraction fallback. No preview-and-assess. No silent cleverness. No third option. This matches the locked product decision (breakdown.py:16-23,460-473): the hard stop is a normal returned value representing expected input (a hand-built deck), and the only sanctioned recoveries are "use a built-in" or "go rebuild it." **Confirmed against the locked decision.**

---

## 6. Error-to-dialog mapping

All messages follow the NOTES.md pattern "[what happened] + [what you can do]", contain no exception types or stack traces, and log technical detail via `logging.getLogger(__name__)`. Mirrors the existing `GenerateWorker` mapping (generate_worker.py:93-102).

**Generate step (caught inside `TemplateGenerateWorker.run`, emitted as `failed`):**

| Exception | Order | Message |
|-----------|-------|---------|
| `OllamaTimeoutError` | catch **before** `OllamaConnectionError` (it is a subclass) | "The AI engine timed out. It may be busy; please try again." |
| `OllamaConnectionError` | after Timeout | "The AI engine stopped responding. Please check Ollama is running." |
| `OllamaGenerationError` | | "The AI returned an unexpected response. Please try again." |
| `ParseError` (post-repair: unparseable JSON OR validation-failed-after-repair, pipeline.py:109-120) | | "The AI could not produce a valid slide structure after retrying. Try a simpler request or a different model." |

The subclass-before-superclass ordering is required and is the [[feedback_layered_except_pattern]] applied: `OllamaTimeoutError(OllamaConnectionError)` per NOTES.md must be caught first or the timeout message is unreachable.

**Import/breakdown step (caught in the synchronous SELECTION handler, shown inline on SELECTION):**

| Exception | Message |
|-----------|---------|
| `ValueError` (bad input; or duplicate-name from import_template, config.py:200-203) | bad input: "That file is not a usable PowerPoint deck."; duplicate: "A template with that name already exists. Delete or rename it, then upload again." |
| `ManipulationError` (folder/strip/manifest write failure) | "Could not save the imported template. Check disk space and permissions." |

**Render step (caught in the synchronous PREVIEW handler, shown inline on PREVIEW):**

| Exception | Message |
|-----------|---------|
| `ManipulationError` (write failure, or manifest/template placeholder/layout mismatch, render_pptx.py:40-44,172-177,197) | write: "Could not save the presentation. Check the folder exists and you have write permission."; mismatch: "This template and its manifest are out of sync and cannot be rendered." |
| `ValueError` (corrupt/missing template file, render_pptx.py:24-31) | "The template file could not be opened as a PowerPoint file." |

**On `ValidationError`:** there is no clause. Pydantic's `ValidationError` is consumed inside `validate_content` (validation.py:154-157) and never reaches the GUI. Post-repair validation failure arrives as `ParseError` (handled above); edit-time validation failure arrives as `(False, errors)` (section 4, inline, not an exception). This is the F3 discrepancy versus the objective's error list, resolved.

**No new exception types are introduced.** Every caught type already exists in the modules named in NOTES.md:36-46.

---

## 7. The one backend change (F1): `pipeline.generate`

Extract the render-free loop. Backward compatible: `run()` keeps its signature and behavior; the CLI (`pipeline.run`) is unaffected and its existing tests stay green as a regression guard.

```
def generate(
    manifest: Manifest,
    messages: list[dict],
    model: str,
    client=None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Generate -> validate -> (repair) loop. Returns validated content
    {"slides": [...]}. Does NOT render.
    Raises ParseError after the single repair attempt is exhausted;
    propagates Ollama* errors from llm.generate."""
    # exact body of run() up to (but not including) each render() call,
    # returning the validated dict instead of calling render().
    # progress(label) invoked at: "generating", "validating", "repairing".

def run(manifest, template_dir, messages, model, out_path, client=None):
    content = generate(manifest, messages, model, client=client)
    return render(manifest, content, out_path, template_dir)
```

`progress` is an optional hook; when `None`, behavior is identical to today. The worker passes a callback that emits its `progress` signal. This is the cleanest way to surface the validating/repairing phases the objective asks for without the worker reaching inside the loop.

Naming: the objective calls this `pipeline.generate`; that name is unambiguous at the call site (`from templates_engine import pipeline; pipeline.generate(...)`) and distinct from `llm.generate`. Open to `generate_content` if you prefer to disambiguate from `llm.generate`.

---

## 8. File structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `simplicitor/templates_engine/pipeline.py` | Modify | Extract `generate()`; `run()` composes `generate()` + `render()`; add `progress` hook. |
| `simplicitor/app/workers/template_worker.py` | Create | `TemplateGenerateWorker(QObject)`: runs `pipeline.generate` off-thread; maps Ollama*/ParseError to `failed`; emits phase `progress`. |
| `simplicitor/app/widgets/template_dialog.py` | Create | `TemplateDialog(QDialog)`: QStackedWidget state machine; owns worker+thread; synchronous import/render; inline error label; reuses defaults colors/fonts. |
| `simplicitor/app/widgets/hard_stop_dialog.py` | Create | `HardStopDialog(QDialog)`: verbatim message, exactly two buttons, returns the routing choice. |
| `simplicitor/app/widgets/create_panel.py` | Modify | Add `From template...` button + `template_requested` signal. Surgical: no other change. |
| `simplicitor/app/main_window.py` | Modify | Connect `template_requested` -> guard on `_current_model` -> open `TemplateDialog`. |
| `tests/test_template_worker.py` | Create | Worker error-to-message mapping + completed/progress. |
| `tests/test_template_dialog.py` | Create | Hard-stop routing, edit-then-revalidate (valid + invalid), render success, error surfacing. |

Tests go in top-level `tests/` (pytest.ini: `testpaths = tests`). Note: `simplicitor/tests/` contains duplicate/stale copies of `test_pipeline.py` and `test_cli.py` that are not collected; left untouched per surgical discipline, flagged for a separate cleanup.

---

## 9. Test approach

pytest-qt (`qtbot`), offscreen Qt (tests/conftest.py). Mock the single boundary that matters; real fixtures elsewhere (real `validate_content`, real `render`, real `tmp_template` manifest+template fixture from tests/templates_engine/conftest.py).

**Worker (`tests/test_template_worker.py`):**
- Mock boundary = the injected client (`pipeline.generate(..., client=mock)`), or mock `pipeline.generate` directly for raise-each-exception cases.
- `qtbot.waitSignal(worker.failed)` then `worker.run()`; assert friendly message present AND raw technical text absent (the test_generate_worker.py:57-72 contract).
- Cover each row of the generate-step table in section 6, including `OllamaTimeoutError` resolving to the timeout message (proves subclass ordering), not the connection message.
- Cover `completed(content_dict)` with a real `tmp_template` + a stubbed client returning valid JSON (exercises the real validate-repair loop).

**Dialog (`tests/test_template_dialog.py`), assert on real state not existence proxies:**
1. **Hard-stop routing:** monkeypatch `import_template` to return `{"status":"hard_stop", ...}`; drive upload; assert `HardStopDialog` shown; "Use a built-in" returns dialog to SELECTION (`dialog._stack.currentWidget() is dialog._selection_page`); "Cancel" leaves the flow on SELECTION. Assert the displayed message equals `_HARD_STOP_MESSAGE` verbatim.
2. **Edit-then-revalidate, valid:** real `tmp_template`; put manifest-conformant JSON in the editor; click Render; assert `render` produced a file and the opened `Presentation` has the expected slide count; dialog reaches DONE.
3. **Edit-then-revalidate, invalid:** put JSON with an unknown slide type (and separately a missing required field); click Render; assert `validate_content` rejected it, the inline error label text contains the `format_validation_errors` substring, render was NOT called (no file written), `currentWidget() is dialog._preview_page`.
4. **Error-to-dialog mapping:** inject a worker/`pipeline.generate` that raises each exception; assert the dialog's inline error label shows the mapped friendly message and the dialog returned to CONFIRM.

---

## 10. Scope and conformance

**Out of scope (deferred):** the two built-in templates (Phase L), the holistic error-handling audit (Phase M), any new async framework, any new logger, any new exception type, cancellation of in-flight generation.

**Conformance checklist:**
- Worker/thread pattern: reused verbatim (moveToThread, started/progress/completed/failed, quit+deleteLater).
- Logger: `logging.getLogger(__name__)` per module; technical detail to logs, friendly text to UI; never log prompt or file content (NOTES.md:56-65).
- Exceptions: only the NOTES.md:36-46 set; subclass-before-superclass ordering; no new types.
- No-partial-file discipline: untouched. `render` (atomic temp+rename, render_pptx.py:185-199), `strip_to_template`, and `import_template` (no-partial-folder, config.py:230-236) already guarantee it; the GUI adds nothing that writes partials.
- assert-vs-raise: user/runtime conditions use if/raise + inline surfacing; assert only for design invariants.
- Existing patterns win: StatusBanner semantics, SettingsDialog modal construction, CreatePanel `os.startfile` open, defaults.py colors/fonts/`EDIT_FILE_FILTER`.

---

## 11. Open decisions for review

1. **Backend seam (F1):** approve extracting `pipeline.generate` + `progress` hook. Name `generate` vs `generate_content`?
2. **Entry point (F4):** `From template...` button inside CreatePanel, vs a TopBar entry. Recommendation: CreatePanel.
3. **Worker ownership:** TemplateDialog owns the worker (recommended) vs MainWindow owns it and drives the dialog.
4. **Import/breakdown threading:** synchronous with wait cursor (recommended, YAGNI) vs a second worker.
5. **CONFIRM report source:** manifest-derived summary always, plus import `report`/`lint_warnings` on the upload path (recommended) vs re-running `detection_report` on every template including built-ins.
6. **F5:** confirm we wire hard-stop "use a built-in" routing now and ship the empty-built-in-list copy until Phase L.
