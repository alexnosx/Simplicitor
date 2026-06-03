# Phase K: GUI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the Phase A-J PPTX template backend into Simplicitor's PySide6 GUI: template selection, upload+breakdown, hard-stop routing, detection-report confirmation, async generation off the GUI thread, editable JSON preview with re-validation, render, and failure surfacing through the existing patterns.

**Architecture:** A render-free `pipeline.generate_content` seam (Task 1, its own commit) exposes validated JSON before render. A MainWindow-owned `TemplateGenerateWorker` runs that loop off-thread (reusing the moveToThread pattern). A modal `TemplateDialog` (QStackedWidget state machine) plays the "panel" role: it emits `generate_requested`, receives worker signals on slots, and runs the bounded local steps (import, render) synchronously. A small `HardStopDialog` captures the two-choice hard stop.

**Tech Stack:** PySide6, pytest-qt, python-pptx, pydantic (via `validate_content`). Ground: Phase J commit `3768d7d`.

**Conformance (non-negotiable):** moveToThread reused verbatim; existing StatusBanner/inline-error and logger patterns; NOTES.md exception table only (no new types); assert-vs-raise discipline (assert only for design invariants); no-partial-file discipline untouched. Existing patterns win.

**Rulings applied:** seam named `generate_content`; seam is commit 1 before any GUI code; entry point in CreatePanel; worker MainWindow-owned (matches existing locus) with quit+wait teardown on dialog close including mid-generation; import/breakdown synchronous; CONFIRM uses manifest-derived summary plus import report only on the upload path, never re-running `detection_report` on templates that ship a manifest; hard-stop "use a built-in" button gated on built-in availability so it never dead-ends; validation-exhaustion mislabeling logged to NOTES.md for Phase M.

---

## File structure

| Path | Action | Responsibility |
|------|--------|----------------|
| `simplicitor/templates_engine/pipeline.py` | Modify | Extract `generate_content()`; `run()` composes it + `render()`; optional `progress` hook. |
| `simplicitor/templates_engine/NOTES.md` | Modify | Add Phase M follow-up: validation-exhaustion raised as `ParseError`. |
| `tests/templates_engine/test_pipeline.py` | Modify | Add `generate_content` tests; existing `run` tests stay green. |
| `simplicitor/app/workers/template_worker.py` | Create | `TemplateGenerateWorker`: runs `generate_content` off-thread, maps exceptions to `failed`. |
| `tests/test_template_worker.py` | Create | Worker completed/progress/error-mapping. |
| `simplicitor/app/widgets/hard_stop_dialog.py` | Create | `HardStopDialog`: verbatim message, gated two-button choice. |
| `simplicitor/app/widgets/template_dialog.py` | Create | `TemplateDialog`: state machine, sync import/render, preview re-validation. |
| `tests/test_template_dialog.py` | Create | Hard-stop routing, edit-then-revalidate (valid+invalid), error surfacing, entry-point signal. |
| `simplicitor/app/widgets/create_panel.py` | Modify | Add `From template...` button + `template_requested` signal. |
| `simplicitor/app/main_window.py` | Modify | Wire entry point; own/start/teardown the template worker thread. |

Tests run from repo root; `pytest.ini` sets `testpaths = tests`, `pythonpath = simplicitor`. Note: `simplicitor/tests/` holds duplicate, non-collected copies of `test_pipeline.py`/`test_cli.py`; leave untouched (flagged for separate cleanup).

---

## Task 1: Pipeline seam `generate_content` (backend; own commit, before any GUI code)

**Files:**
- Modify: `simplicitor/templates_engine/pipeline.py`
- Modify: `simplicitor/templates_engine/NOTES.md`
- Test: `tests/templates_engine/test_pipeline.py`

- [ ] **Step 1: Add failing tests for `generate_content`**

Append to `tests/templates_engine/test_pipeline.py` (reuses existing `manifest` fixture, `VALID_CONTENT`, `INVALID_CONTENT`, `TRUNCATED_CONTENT`):

```python
# ---------------------------------------------------------------------------
# Phase K: generate_content seam (render-free)
# ---------------------------------------------------------------------------

def test_generate_content_valid_first_attempt(manifest):
    with patch("templates_engine.llm.generate", return_value=VALID_CONTENT) as mock_gen:
        content = pipeline.generate_content(
            manifest, [{"role": "user", "content": "deck"}], "llama3"
        )
    assert mock_gen.call_count == 1
    assert content["slides"][0]["type"] == "title_slide"
    assert content["slides"][0]["fields"]["title"] == "My Title"


def test_generate_content_does_not_render(manifest):
    with patch("templates_engine.llm.generate", return_value=VALID_CONTENT), \
         patch("templates_engine.pipeline.render") as mock_render:
        pipeline.generate_content(manifest, [{"role": "user", "content": "x"}], "llama3")
    mock_render.assert_not_called()


def test_generate_content_validation_repair_success(manifest):
    with patch("templates_engine.llm.generate",
               side_effect=[INVALID_CONTENT, VALID_CONTENT]) as mock_gen:
        content = pipeline.generate_content(
            manifest, [{"role": "user", "content": "x"}], "llama3"
        )
    assert mock_gen.call_count == 2
    assert content["slides"][0]["fields"]["title"] == "My Title"


def test_generate_content_post_repair_validation_raises_parseerror(manifest):
    from app.parsers.llm_response_parser import ParseError
    with patch("templates_engine.llm.generate",
               side_effect=[INVALID_CONTENT, INVALID_CONTENT]):
        with pytest.raises(ParseError, match="after repair"):
            pipeline.generate_content(manifest, [{"role": "user", "content": "x"}], "llama3")


def test_generate_content_post_repair_parse_raises_parseerror(manifest):
    from app.parsers.llm_response_parser import ParseError
    with patch("templates_engine.llm.generate", side_effect=["nope", "still nope"]):
        with pytest.raises(ParseError, match="after repair"):
            pipeline.generate_content(manifest, [{"role": "user", "content": "x"}], "llama3")


def test_generate_content_emits_progress_phases(manifest):
    phases = []
    with patch("templates_engine.llm.generate",
               side_effect=[INVALID_CONTENT, VALID_CONTENT]):
        pipeline.generate_content(
            manifest, [{"role": "user", "content": "x"}], "llama3",
            progress=phases.append,
        )
    assert phases[0] == "generating"
    assert "repairing" in phases
    assert "validating" in phases
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/templates_engine/test_pipeline.py -k generate_content -v`
Expected: FAIL with `AttributeError: module 'templates_engine.pipeline' has no attribute 'generate_content'`.

- [ ] **Step 3: Implement the seam**

In `simplicitor/templates_engine/pipeline.py`, add the import and replace the body of `run()` by extracting the loop into `generate_content()`.

Add near the top imports:
```python
from collections.abc import Callable
```

Insert `generate_content` above `run` and rewrite `run` to compose:
```python
def generate_content(
    manifest: Manifest,
    messages: list[dict],
    model: str,
    client=None,
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Run the generate → validate → (repair) loop and return validated content.

    Returns the validated content dict {"slides": [...]}. Does NOT render.

    Args:
        manifest: Validated Manifest from load_manifest().
        messages: OpenAI-format prompt from build_prompt().
        model: Ollama model name.
        client: Optional injected OllamaClient (None uses default).
        progress: Optional callback invoked with phase labels
            ("generating", "validating", "repairing"). Invoked on the calling thread.

    Raises:
        ParseError: Model could not produce valid content after one repair attempt.
            NOTE: a post-repair *validation* failure (parseable JSON that still fails
            the manifest) is also raised as ParseError today. See NOTES.md follow-up #4
            (Phase M audit target) — this conflates a schema failure with a parse failure.
        OllamaTimeoutError, OllamaConnectionError, OllamaGenerationError: from llm.generate.
    """
    def _emit(label: str) -> None:
        if progress is not None:
            progress(label)

    # ── Attempt 1 ────────────────────────────────────────────────────────────
    _emit("generating")
    raw1 = llm.generate(messages, model, client=client)
    cleaned1, parsed1, parse_exc1 = _try_parse(raw1)

    if parsed1 is not None:
        _emit("validating")
        ok, result = validate_content(manifest, parsed1)
        if ok:
            return result
        logger.warning(
            "Content validation failed on attempt 1 (%d error(s)). Attempting repair.",
            len(result),
        )
        repair_msgs = build_repair_prompt(messages, raw1, errors=result)
        repair_max_tokens = None  # validation failures do not trigger token bump
    else:
        truncated = _looks_truncated(cleaned1, parse_exc1)
        logger.warning(
            "JSON parse failed on attempt 1 (truncated=%s). Attempting repair.",
            truncated,
        )
        repair_max_tokens = OLLAMA_REPAIR_MAX_TOKENS if truncated else None
        repair_msgs = build_repair_prompt(messages, raw1, errors=None)

    # ── Attempt 2 (repair) ───────────────────────────────────────────────────
    _emit("repairing")
    raw2 = llm.generate(repair_msgs, model, max_tokens=repair_max_tokens, client=client)
    _, parsed2, parse_exc2 = _try_parse(raw2)

    if parsed2 is None:
        logger.error("JSON parse failed after repair. Giving up.")
        raise ParseError(
            "LLM response could not be parsed as JSON after repair",
            details=str(parse_exc2),
        )

    _emit("validating")
    ok2, result2 = validate_content(manifest, parsed2)
    if not ok2:
        logger.error("Content validation failed after repair. Giving up.")
        raise ParseError(
            "Model returned invalid content after repair",
            details=format_validation_errors(result2),
        )

    return result2


def run(
    manifest: Manifest,
    template_dir: Path | str,
    messages: list[dict],
    model: str,
    out_path: Path | str,
    client=None,
) -> dict:
    """Run the full generate → validate → (repair) → render pipeline.

    Args:
        manifest: Validated Manifest from load_manifest().
        template_dir: Directory containing manifest.template_file.
        messages: OpenAI-format prompt from build_prompt().
        model: Ollama model name.
        out_path: Destination .pptx path. .pptx suffix appended if absent.
        client: Optional injected OllamaClient (for testing; None uses default).

    Returns:
        {"path": Path, "issues": list[str]} — same shape as render().

    Raises:
        ParseError: Model could not produce valid content after one repair attempt.
        OllamaTimeoutError, OllamaConnectionError, OllamaGenerationError: propagated from llm.generate.
        ManipulationError: propagated from render() on I/O failure or manifest/template mismatch.
        ValueError: propagated from render() on corrupt/missing template.
    """
    content = generate_content(manifest, messages, model, client=client)
    return render(manifest, content, out_path, template_dir)
```

Delete the old inline loop body that previously lived inside `run()` (everything between the old `# ── Attempt 1 ──` and the final `return render(...)`); it now lives in `generate_content`.

- [ ] **Step 4: Run new + existing pipeline tests**

Run: `python -m pytest tests/templates_engine/test_pipeline.py -v`
Expected: PASS. All `generate_content` tests pass AND all pre-existing `test_run_*` tests pass unchanged (regression guard: `run` behavior is identical).

- [ ] **Step 5: Run the full collected suite (regression guard for the seam)**

Run: `python -m pytest tests/ -q`
Expected: PASS, same green set as before the change (the CLI uses `pipeline.run`, whose signature and behavior are unchanged).

- [ ] **Step 6: Add the NOTES.md Phase M follow-up**

In `simplicitor/templates_engine/NOTES.md`, under `## Known follow-ups`, append:
```markdown
4. **`pipeline.generate_content` raises `ParseError` for a post-repair *validation* failure** (Phase K).
   When the repair attempt returns parseable JSON that still fails manifest validation, the loop
   raises `ParseError("Model returned invalid content after repair")` rather than a validation-specific
   error. This conflates a schema failure with a parse failure. The Phase K GUI maps the `ParseError`
   that is actually raised today, but the semantics are wrong: a schema failure is not a parse failure.
   Phase M (error-handling audit) target: introduce a distinct validation-exhaustion error, or at least a
   message naming the schema cause. The GUI's single ParseError mapping is NOT evidence the semantics
   are correct — it is a deliberate accommodation of current behavior. (`pipeline.py`, attempt-2 branch.)
```

- [ ] **Step 7: Commit (seam only, no GUI code)**

```bash
git add simplicitor/templates_engine/pipeline.py simplicitor/templates_engine/NOTES.md tests/templates_engine/test_pipeline.py
git commit -m "$(cat <<'EOF'
refactor(phase-k): extract pipeline.generate_content seam

Extract the render-free generate-validate-repair loop into
pipeline.generate_content(); run() now composes generate_content + render.
Backward compatible: run() signature and behavior unchanged, CLI unaffected.
Adds an optional progress(label) hook for the GUI worker. Logs the
validation-exhaustion-as-ParseError semantics defect as a Phase M target.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `TemplateGenerateWorker`

**Files:**
- Create: `simplicitor/app/workers/template_worker.py`
- Test: `tests/test_template_worker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_template_worker.py`:
```python
# tests/test_template_worker.py
# Phase K: Tests for TemplateGenerateWorker.
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.parsers.llm_response_parser import ParseError
from app.services.ollama_client import (
    OllamaConnectionError, OllamaGenerationError, OllamaTimeoutError,
)
from app.workers.template_worker import TemplateGenerateWorker
from templates_engine.manifest import load_manifest

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)
VALID_CONTENT = json.dumps(
    {"slides": [{"type": "title_slide", "fields": {"title": "My Title"}}]}
)
INVALID_CONTENT = json.dumps({"slides": [{"type": "title_slide", "fields": {}}]})


@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


def make_worker(manifest, request="A deck", model="llama3", client=None):
    return TemplateGenerateWorker(manifest, request, model, client or MagicMock())


def test_worker_has_signals(manifest):
    w = make_worker(manifest)
    for name in ("started", "progress", "completed", "failed"):
        assert hasattr(w, name)


def test_worker_completed_emits_validated_dict(qtbot, manifest):
    worker = make_worker(manifest)
    with patch("templates_engine.llm.generate", return_value=VALID_CONTENT):
        with qtbot.waitSignal(worker.completed, timeout=5000) as blocker:
            worker.run()
    content = blocker.args[0]
    assert content["slides"][0]["type"] == "title_slide"
    assert content["slides"][0]["fields"]["title"] == "My Title"


def test_worker_emits_progress_phases(qtbot, manifest):
    worker = make_worker(manifest)
    messages = []
    worker.progress.connect(messages.append)
    with patch("templates_engine.llm.generate",
               side_effect=[INVALID_CONTENT, VALID_CONTENT]):
        with qtbot.waitSignal(worker.completed, timeout=5000):
            worker.run()
    joined = " ".join(messages)
    assert "Generating" in joined
    assert "Fixing" in joined  # the "repairing" phase message


def test_worker_timeout_maps_before_connection(qtbot, manifest):
    worker = make_worker(manifest)
    with patch("templates_engine.pipeline.generate_content",
               side_effect=OllamaTimeoutError("read timeout after 60s")):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert "timed out" in msg.lower()
    assert "60s" not in msg
    assert "stopped responding" not in msg  # not the generic connection message


def test_worker_connection_error_maps(qtbot, manifest):
    worker = make_worker(manifest)
    with patch("templates_engine.pipeline.generate_content",
               side_effect=OllamaConnectionError("HTTPConnectionPool refused")):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert "Ollama" in msg or "AI engine" in msg
    assert "HTTPConnectionPool" not in msg


def test_worker_generation_error_maps(qtbot, manifest):
    worker = make_worker(manifest)
    with patch("templates_engine.pipeline.generate_content",
               side_effect=OllamaGenerationError("status 500 Internal Server Error")):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert "unexpected" in msg.lower() or "try again" in msg.lower()
    assert "500" not in msg


def test_worker_parse_error_maps(qtbot, manifest):
    worker = make_worker(manifest)
    with patch("templates_engine.pipeline.generate_content",
               side_effect=ParseError("Model returned invalid content after repair", details="x")):
        with qtbot.waitSignal(worker.failed, timeout=5000) as blocker:
            worker.run()
    msg = blocker.args[0]
    assert "valid slide structure" in msg.lower()
    assert "after repair" not in msg
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_template_worker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.workers.template_worker'`.

- [ ] **Step 3: Implement the worker**

Create `simplicitor/app/workers/template_worker.py`:
```python
# simplicitor/app/workers/template_worker.py
# Phase K: Template-based PPTX content generation worker.
import logging

from PySide6.QtCore import QObject, Signal

from app.parsers.llm_response_parser import ParseError
from app.services.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaGenerationError,
    OllamaTimeoutError,
)
from templates_engine import pipeline
from templates_engine.manifest import Manifest
from templates_engine.prompt_builder import build_prompt

logger = logging.getLogger(__name__)

_PHASE_MESSAGES = {
    "generating": "Generating slides…",
    "validating": "Checking the result…",
    "repairing": "Fixing the result…",
}


class TemplateGenerateWorker(QObject):
    """Runs the template generate-validate-repair loop on a background QThread.

    Reuses the moveToThread pattern (started/progress/completed/failed). Renders
    nothing — the dialog renders synchronously after the editable preview. Touches
    no widgets: run() only emits signals, and the progress callback only emits a
    signal (queued to the main thread), preserving the no-QWidget-off-thread rule.

    Signals:
        started: emitted when run() begins.
        progress: emitted with a human-readable phase message.
        completed: emitted with the validated content dict {"slides": [...]}.
        failed: emitted with a user-friendly error message on failure.
    """

    started = Signal()
    progress = Signal(str)
    completed = Signal(object)   # validated content dict
    failed = Signal(str)

    def __init__(
        self, manifest: Manifest, user_request: str, model: str, client: OllamaClient
    ) -> None:
        super().__init__()
        self._manifest = manifest
        self._user_request = user_request
        self._model = model
        self._client = client

    def _emit_phase(self, label: str) -> None:
        """Progress callback for pipeline.generate_content. Emits only a signal."""
        self.progress.emit(_PHASE_MESSAGES.get(label, "Working…"))

    def run(self) -> None:
        """Execute the generate-validate-repair loop. Called via QThread.started."""
        self.started.emit()
        messages = build_prompt(self._manifest, self._user_request)
        try:
            content = pipeline.generate_content(
                self._manifest,
                messages,
                self._model,
                client=self._client,
                progress=self._emit_phase,
            )
        except OllamaTimeoutError as exc:  # subclass of OllamaConnectionError: catch FIRST
            logger.error("Ollama timed out during template generation: %s", exc)
            self.failed.emit("The AI engine timed out. It may be busy; please try again.")
            return
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during template generation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error during template generation: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return
        except ParseError as exc:
            logger.error("Template content invalid after repair: %s", exc)
            self.failed.emit(
                "The AI could not produce a valid slide structure after retrying. "
                "Try a simpler request or a different model."
            )
            return

        self.completed.emit(content)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_template_worker.py -v`
Expected: PASS (8 tests). The timeout test proves subclass-before-superclass ordering.

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/workers/template_worker.py tests/test_template_worker.py
git commit -m "$(cat <<'EOF'
feat(phase-k): TemplateGenerateWorker for off-thread content generation

Runs pipeline.generate_content on a background QThread (moveToThread pattern).
Maps Ollama*/ParseError to friendly failed() messages; OllamaTimeoutError is
caught before OllamaConnectionError. Emits phase progress; touches no widgets.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `HardStopDialog`

**Files:**
- Create: `simplicitor/app/widgets/hard_stop_dialog.py`
- Test: `tests/test_template_dialog.py` (shared file; hard-stop section first)

- [ ] **Step 1: Write failing tests**

Create `tests/test_template_dialog.py` with the hard-stop section:
```python
# tests/test_template_dialog.py
# Phase K: Tests for HardStopDialog and TemplateDialog.
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.widgets.hard_stop_dialog import HardStopDialog, CHOICE_BUILTIN, CHOICE_CANCEL
from templates_engine.breakdown import hard_stop_result


def test_hard_stop_shows_verbatim_message(qtbot):
    msg = hard_stop_result()["message"]
    dlg = HardStopDialog(msg, builtin_available=True)
    qtbot.addWidget(dlg)
    labels = [w.text() for w in dlg.findChildren(QLabel)]
    assert any(msg in t for t in labels)


def test_hard_stop_two_buttons_when_builtin_available(qtbot):
    dlg = HardStopDialog("x", builtin_available=True)
    qtbot.addWidget(dlg)
    assert dlg.has_builtin_button() is True
    qtbot.mouseClick(dlg._builtin_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_BUILTIN


def test_hard_stop_cancel_choice(qtbot):
    dlg = HardStopDialog("x", builtin_available=True)
    qtbot.addWidget(dlg)
    qtbot.mouseClick(dlg._cancel_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_CANCEL


def test_hard_stop_no_builtin_button_when_unavailable(qtbot):
    dlg = HardStopDialog("x", builtin_available=False)
    qtbot.addWidget(dlg)
    assert dlg.has_builtin_button() is False
    assert not hasattr(dlg, "_builtin_btn")
    qtbot.mouseClick(dlg._cancel_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_CANCEL
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_template_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.widgets.hard_stop_dialog'`.

- [ ] **Step 3: Implement**

Create `simplicitor/app/widgets/hard_stop_dialog.py`:
```python
# simplicitor/app/widgets/hard_stop_dialog.py
# Phase K: Two-choice modal shown when an uploaded deck cannot be templated.
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)

CHOICE_BUILTIN = "builtin"
CHOICE_CANCEL = "cancel"


class HardStopDialog(QDialog):
    """Modal shown when import_template returns a hard stop.

    Offers exactly two actions when a built-in template is available: use a
    built-in, or cancel and rebuild. When no built-in is available (before
    Phase L) only the cancel/rebuild path is shown — no dead-end button. The
    built-in button appears automatically once built-ins ship.
    """

    def __init__(
        self, message: str, builtin_available: bool, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._choice = CHOICE_CANCEL
        self._builtin_available = builtin_available
        self.setWindowTitle("This deck can't be used as a template")
        self.setMinimumWidth(480)
        self._build_ui(message)
        self.setStyleSheet(f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}")

    def _build_ui(self, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        heading = QLabel("This deck can't be used as a template")
        hf = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        hf.setWeight(QFont.Weight.DemiBold)
        heading.setFont(hf)
        layout.addWidget(heading)

        body = QLabel(message)
        body.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        body.setWordWrap(True)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self._cancel_btn = QPushButton("Cancel and rebuild with proper layouts")
        self._cancel_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        self._cancel_btn.clicked.connect(self._on_cancel)

        if self._builtin_available:
            self._builtin_btn = QPushButton("Use a built-in template")
            self._builtin_btn.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
            self._builtin_btn.clicked.connect(self._on_builtin)
            buttons.addWidget(self._builtin_btn)

        buttons.addWidget(self._cancel_btn)
        layout.addLayout(buttons)

    def _on_builtin(self) -> None:
        self._choice = CHOICE_BUILTIN
        self.accept()

    def _on_cancel(self) -> None:
        self._choice = CHOICE_CANCEL
        self.reject()

    def choice(self) -> str:
        """Return CHOICE_BUILTIN or CHOICE_CANCEL."""
        return self._choice

    def has_builtin_button(self) -> bool:
        """True if the 'use a built-in' button was rendered."""
        return self._builtin_available
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_template_dialog.py -v`
Expected: PASS (4 hard-stop tests).

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/hard_stop_dialog.py tests/test_template_dialog.py
git commit -m "$(cat <<'EOF'
feat(phase-k): HardStopDialog with gated built-in option

Verbatim hard-stop message and exactly two actions. The 'use a built-in'
button is gated on built-in availability so it never dead-ends before Phase L;
it appears automatically when built-ins ship.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `TemplateDialog`

**Files:**
- Create: `simplicitor/app/widgets/template_dialog.py`
- Test: `tests/test_template_dialog.py` (append TemplateDialog section)

- [ ] **Step 1: Append failing tests**

Append to `tests/test_template_dialog.py`:
```python
# --- TemplateDialog -------------------------------------------------------
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pptx import Presentation

from app.widgets.template_dialog import TemplateDialog
from templates_engine import config

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)
VALID = {"slides": [{"type": "title_slide", "fields": {"title": "My Title"}}]}
MISSING_REQUIRED = {"slides": [{"type": "title_slide", "fields": {}}]}


@pytest.fixture
def template_root(tmp_path, monkeypatch):
    """A user templates root with one valid 'deck' template; empty built-in root."""
    root = tmp_path / "user"
    tdir = root / "deck"
    tdir.mkdir(parents=True)
    Presentation().save(str(tdir / "template.pptx"))
    (tdir / "manifest.yaml").write_bytes(FIXTURE_MANIFEST.read_bytes())
    empty_builtin = tmp_path / "builtin_empty"
    empty_builtin.mkdir()
    monkeypatch.setattr(config, "get_user_root", lambda: root)
    monkeypatch.setattr(config, "get_builtin_root", lambda: empty_builtin)
    return root


@pytest.fixture
def dialog(qtbot, tmp_path, template_root):
    settings = SimpleNamespace(generated_dir=str(tmp_path / "out"))
    dlg = TemplateDialog(model="llama3", settings=settings)
    qtbot.addWidget(dlg)
    return dlg


def _select_deck(dlg):
    dlg._refresh_templates()
    dlg._template_list.setCurrentRow(0)
    dlg._on_select_next()


def test_selection_lists_user_template(dialog):
    dialog._refresh_templates()
    names = [
        dialog._template_list.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(dialog._template_list.count())
    ]
    assert names == ["deck"]


def test_select_next_loads_manifest_and_advances(dialog):
    _select_deck(dialog)
    assert dialog._stack.currentWidget() is dialog._confirm_page
    assert dialog._manifest is not None
    assert dialog._manifest.name == "render_test"


def test_generate_requested_emitted_with_manifest_and_request(qtbot, dialog):
    _select_deck(dialog)
    dialog._confirm_prompt.setPlainText("Make a deck")
    with qtbot.waitSignal(dialog.generate_requested, timeout=2000) as blocker:
        dialog._on_generate_clicked()
    assert blocker.args[0] is dialog._manifest
    assert blocker.args[1] == "Make a deck"


def test_completed_populates_preview(dialog):
    _select_deck(dialog)
    dialog.on_generate_completed(VALID)
    assert dialog._stack.currentWidget() is dialog._preview_page
    assert "title_slide" in dialog._preview_edit.toPlainText()


def test_render_valid_edit_writes_file_and_reaches_done(dialog):
    _select_deck(dialog)
    dialog.on_generate_completed(VALID)
    dialog._on_render_clicked()
    assert dialog._stack.currentWidget() is dialog._done_page
    assert Path(dialog._rendered_path).exists()
    assert len(Presentation(dialog._rendered_path).slides) == 1


def test_render_invalid_validation_shows_error_no_file(dialog):
    _select_deck(dialog)
    dialog.on_generate_completed(MISSING_REQUIRED)
    dialog._on_render_clicked()
    assert dialog._stack.currentWidget() is dialog._preview_page
    assert dialog._preview_error.isVisible()
    assert "title" in dialog._preview_error.text()
    assert not dialog._out_path.exists()


def test_render_invalid_json_shows_error_no_file(dialog):
    _select_deck(dialog)
    dialog.on_generate_completed(VALID)
    dialog._preview_edit.setPlainText("{ not valid json")
    dialog._on_render_clicked()
    assert dialog._stack.currentWidget() is dialog._preview_page
    assert "JSON" in dialog._preview_error.text()
    assert not dialog._out_path.exists()


def test_generate_failed_shows_error_returns_to_confirm(dialog):
    _select_deck(dialog)
    dialog.on_generate_started()
    dialog.on_generate_failed(
        "The AI engine stopped responding. Please check Ollama is running."
    )
    assert dialog._stack.currentWidget() is dialog._confirm_page
    assert "Ollama" in dialog._confirm_status.text()


def test_hard_stop_builtin_routes_to_selection(dialog):
    _select_deck(dialog)  # currently on confirm
    dialog._apply_hard_stop_choice("builtin")
    assert dialog._stack.currentWidget() is dialog._selection_page


def test_hard_stop_cancel_rejects_flow(dialog, monkeypatch):
    rejected = []
    monkeypatch.setattr(dialog, "reject", lambda: rejected.append(True))
    dialog._apply_hard_stop_choice("cancel")
    assert rejected == [True]


def test_upload_hard_stop_invokes_prompt(dialog, monkeypatch):
    seen = {}
    monkeypatch.setattr(
        config, "import_template",
        lambda path: {"status": "hard_stop", "message": "NOPE"},
    )
    monkeypatch.setattr(dialog, "_prompt_hard_stop", lambda msg: seen.setdefault("msg", msg) or "cancel")
    monkeypatch.setattr(dialog, "_apply_hard_stop_choice", lambda choice: seen.setdefault("choice", choice))
    dialog._do_import("whatever.pptx")
    assert seen["msg"] == "NOPE"
    assert seen["choice"] == "cancel"


def test_prompt_hard_stop_gates_builtin_on_availability(dialog, monkeypatch):
    captured = {}

    class FakeHS:
        def __init__(self, message, builtin_available, parent=None):
            captured["builtin_available"] = builtin_available

        def exec(self):
            return 0

        def choice(self):
            return CHOICE_CANCEL

    monkeypatch.setattr("app.widgets.template_dialog.HardStopDialog", FakeHS)
    dialog._refresh_templates()  # only a user template, no built-ins
    dialog._prompt_hard_stop("msg")
    assert captured["builtin_available"] is False
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_template_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.widgets.template_dialog'`.

- [ ] **Step 3: Implement**

Create `simplicitor/app/widgets/template_dialog.py`:
```python
# simplicitor/app/widgets/template_dialog.py
# Phase K: Template-based PPTX generation flow (modal state machine).
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from app.config.defaults import (
    APP_FONT_FAMILY, BACKGROUND_COLOR, BODY_TEXT_COLOR, ERROR_COLOR,
    FONT_SIZE_BODY_PT, FONT_SIZE_HEADING_PT,
)
from app.config.settings import Settings
from app.services.file_manipulator import ManipulationError
from app.widgets.hard_stop_dialog import CHOICE_BUILTIN, HardStopDialog
from templates_engine import config
from templates_engine.manifest import Manifest, load_manifest
from templates_engine.render_pptx import render
from templates_engine.validation import format_validation_errors, validate_content

logger = logging.getLogger(__name__)

_PPTX_FILTER = "PowerPoint files (*.pptx)"


class TemplateDialog(QDialog):
    """Modal multi-step template-based PPTX generation flow.

    Pages (QStackedWidget): selection -> confirm -> preview -> done. A hard-stop
    sub-dialog branches off the upload path.

    Worker ownership: this dialog does NOT own the generation worker. To match the
    existing locus (OllamaWorker/GenerateWorker/ManipulateWorker are owned by
    MainWindow), the dialog emits generate_requested and MainWindow creates, owns,
    and tears down the QThread + worker, wiring worker signals to the on_generate_*
    slots here. Bounded local steps (import, render) run synchronously with a wait
    cursor. Close is blocked while a generation is in flight.
    """

    generate_requested = Signal(object, str)  # (Manifest, user_request)

    def __init__(self, model: str, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._model = model
        self._settings = settings
        self._templates: list[dict] = []
        self._selected: dict | None = None
        self._manifest: Manifest | None = None
        self._template_dir: Path | None = None
        self._content: dict | None = None
        self._out_path: Path | None = None
        self._rendered_path: str = ""
        self._import_report: str = ""
        self._generating = False

        self.setWindowTitle("Create from a template")
        self.setMinimumSize(640, 520)
        self._build_ui()
        self.setStyleSheet(f"QDialog {{ background-color: {BACKGROUND_COLOR}; }}")
        self._refresh_templates()

    # ── Fonts ───────────────────────────────────────────────────────────────
    def _heading_font(self) -> QFont:
        f = QFont(APP_FONT_FAMILY, FONT_SIZE_HEADING_PT)
        f.setWeight(QFont.Weight.DemiBold)
        return f

    def _body_font(self) -> QFont:
        return QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)

    # ── Build ─────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self._stack = QStackedWidget()
        root.addWidget(self._stack)
        self._selection_page = self._build_selection_page()
        self._confirm_page = self._build_confirm_page()
        self._preview_page = self._build_preview_page()
        self._done_page = self._build_done_page()
        for page in (self._selection_page, self._confirm_page,
                     self._preview_page, self._done_page):
            self._stack.addWidget(page)
        self._stack.setCurrentWidget(self._selection_page)

    def _build_selection_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        heading = QLabel("Choose a template")
        heading.setFont(self._heading_font())
        v.addWidget(heading)

        self._template_list = QListWidget()
        self._template_list.setFont(self._body_font())
        v.addWidget(self._template_list, stretch=1)

        self._sel_empty = QLabel("No templates yet. Upload a .pptx to begin.")
        self._sel_empty.setFont(self._body_font())
        self._sel_empty.setVisible(False)
        v.addWidget(self._sel_empty)

        self._sel_error = QLabel()
        self._sel_error.setFont(self._body_font())
        self._sel_error.setStyleSheet(f"color: {ERROR_COLOR};")
        self._sel_error.setWordWrap(True)
        self._sel_error.setVisible(False)
        v.addWidget(self._sel_error)

        row = QHBoxLayout()
        upload_btn = QPushButton("Upload a .pptx…")
        upload_btn.setFont(self._body_font())
        upload_btn.clicked.connect(self._on_upload)
        self._sel_next_btn = QPushButton("Next")
        self._sel_next_btn.setFont(self._body_font())
        self._sel_next_btn.clicked.connect(self._on_select_next)
        row.addWidget(upload_btn)
        row.addStretch()
        row.addWidget(self._sel_next_btn)
        v.addLayout(row)
        return page

    def _build_confirm_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        heading = QLabel("Confirm template and describe your deck")
        heading.setFont(self._heading_font())
        v.addWidget(heading)

        self._confirm_summary = QLabel()
        self._confirm_summary.setFont(self._body_font())
        self._confirm_summary.setWordWrap(True)
        v.addWidget(self._confirm_summary)

        self._confirm_report = QLabel()
        self._confirm_report.setFont(QFont(APP_FONT_FAMILY, 8))
        self._confirm_report.setWordWrap(True)
        self._confirm_report.setVisible(False)
        v.addWidget(self._confirm_report)

        prompt_label = QLabel("Describe the presentation you need")
        prompt_label.setFont(self._body_font())
        v.addWidget(prompt_label)
        self._confirm_prompt = QPlainTextEdit()
        self._confirm_prompt.setFont(self._body_font())
        self._confirm_prompt.setMinimumHeight(100)
        v.addWidget(self._confirm_prompt, stretch=1)

        self._confirm_status = QLabel()
        self._confirm_status.setFont(self._body_font())
        self._confirm_status.setWordWrap(True)
        self._confirm_status.setVisible(False)
        v.addWidget(self._confirm_status)

        row = QHBoxLayout()
        self._confirm_back_btn = QPushButton("Back")
        self._confirm_back_btn.setFont(self._body_font())
        self._confirm_back_btn.clicked.connect(
            lambda: self._stack.setCurrentWidget(self._selection_page)
        )
        self._confirm_generate_btn = QPushButton("Generate")
        self._confirm_generate_btn.setFont(self._heading_font())
        self._confirm_generate_btn.clicked.connect(self._on_generate_clicked)
        row.addWidget(self._confirm_back_btn)
        row.addStretch()
        row.addWidget(self._confirm_generate_btn)
        v.addLayout(row)
        return page

    def _build_preview_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        heading = QLabel("Review and edit the content")
        heading.setFont(self._heading_font())
        v.addWidget(heading)

        self._preview_edit = QPlainTextEdit()
        self._preview_edit.setFont(QFont("Consolas", FONT_SIZE_BODY_PT))
        v.addWidget(self._preview_edit, stretch=1)

        self._preview_error = QLabel()
        self._preview_error.setFont(self._body_font())
        self._preview_error.setStyleSheet(f"color: {ERROR_COLOR};")
        self._preview_error.setWordWrap(True)
        self._preview_error.setVisible(False)
        v.addWidget(self._preview_error)

        row = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.setFont(self._body_font())
        back_btn.clicked.connect(lambda: self._stack.setCurrentWidget(self._confirm_page))
        self._render_btn = QPushButton("Render")
        self._render_btn.setFont(self._heading_font())
        self._render_btn.clicked.connect(self._on_render_clicked)
        row.addWidget(back_btn)
        row.addStretch()
        row.addWidget(self._render_btn)
        v.addLayout(row)
        return page

    def _build_done_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(20, 20, 20, 20)
        v.setSpacing(12)

        self._done_label = QLabel()
        self._done_label.setFont(self._heading_font())
        self._done_label.setWordWrap(True)
        v.addWidget(self._done_label)

        row = QHBoxLayout()
        open_btn = QPushButton("Open file")
        open_btn.setFont(self._body_font())
        open_btn.clicked.connect(self._on_open_file)
        close_btn = QPushButton("Close")
        close_btn.setFont(self._body_font())
        close_btn.clicked.connect(self.accept)
        row.addWidget(open_btn)
        row.addStretch()
        row.addWidget(close_btn)
        v.addLayout(row)
        v.addStretch()
        return page

    # ── Selection / upload / import ────────────────────────────────────────────
    def _refresh_templates(self, select_name: str | None = None) -> None:
        try:
            self._templates = config.list_templates()
        except (ValueError, ManipulationError) as exc:
            logger.error("Could not list templates: %s", exc)
            self._templates = []
            self._show_selection_error("Could not read your templates folder.")
        self._template_list.clear()
        for t in self._templates:
            item = QListWidgetItem(f"{t['name']}  ({t['source']})")
            item.setData(Qt.ItemDataRole.UserRole, t["name"])
            self._template_list.addItem(item)
        self._sel_empty.setVisible(not self._templates)
        if select_name:
            for i in range(self._template_list.count()):
                if self._template_list.item(i).data(Qt.ItemDataRole.UserRole) == select_name:
                    self._template_list.setCurrentRow(i)
                    break

    def _on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select a .pptx", "", _PPTX_FILTER)
        if path:
            self._do_import(path)

    def _do_import(self, path: str) -> None:
        self._clear_selection_error()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = config.import_template(path)
        except ValueError as exc:
            logger.error("Template import rejected: %s", exc)
            msg = (
                "A template with that name already exists. Delete or rename it, then upload again."
                if "already exists" in str(exc)
                else "That file is not a usable PowerPoint deck."
            )
            self._show_selection_error(msg)
            return
        except ManipulationError as exc:
            logger.error("Template import write failure: %s", exc)
            self._show_selection_error(
                "Could not save the imported template. Check disk space and permissions."
            )
            return
        finally:
            QApplication.restoreOverrideCursor()

        if result["status"] == "hard_stop":
            choice = self._prompt_hard_stop(result["message"])
            self._apply_hard_stop_choice(choice)
            return

        self._refresh_templates(select_name=result["name"])
        self._select_current(report=result.get("report", ""))

    # ── Hard stop ───────────────────────────────────────────────────────────────
    def _prompt_hard_stop(self, message: str) -> str:
        builtin_available = any(t["source"] == "builtin" for t in self._templates)
        dlg = HardStopDialog(message, builtin_available, parent=self)
        dlg.exec()
        return dlg.choice()

    def _apply_hard_stop_choice(self, choice: str) -> None:
        if choice == CHOICE_BUILTIN:
            self._stack.setCurrentWidget(self._selection_page)
            self._focus_first_builtin()
        else:
            self.reject()  # cancel and rebuild: abandon the flow

    def _focus_first_builtin(self) -> None:
        for i in range(self._template_list.count()):
            name = self._template_list.item(i).data(Qt.ItemDataRole.UserRole)
            t = next((x for x in self._templates if x["name"] == name), None)
            if t and t["source"] == "builtin":
                self._template_list.setCurrentRow(i)
                return

    # ── Confirm ───────────────────────────────────────────────────────────────
    def _on_select_next(self) -> None:
        if self._template_list.currentItem() is None:
            self._show_selection_error("Select a template, or upload a .pptx.")
            return
        self._select_current()

    def _select_current(self, report: str = "") -> None:
        name = self._template_list.currentItem().data(Qt.ItemDataRole.UserRole)
        t = next((x for x in self._templates if x["name"] == name), None)
        if t is None:
            self._show_selection_error("That template could not be found.")
            return
        try:
            manifest = load_manifest(t["manifest_path"])
        except (ValueError, OSError) as exc:
            logger.error("Could not load manifest for '%s': %s", name, exc)
            self._show_selection_error("That template's manifest could not be read.")
            return
        self._selected = t
        self._manifest = manifest
        self._template_dir = Path(t["path"])
        self._import_report = report
        self._confirm_summary.setText(self._manifest_summary(manifest))
        if report:
            self._confirm_report.setText(report)
            self._confirm_report.setVisible(True)
        else:
            self._confirm_report.setVisible(False)
        self._confirm_prompt.clear()
        self._set_confirm_status("", error=False)
        self._stack.setCurrentWidget(self._confirm_page)

    def _manifest_summary(self, manifest: Manifest) -> str:
        lines = [f"Template: {manifest.name}", "", "Slide types:"]
        for name, sdef in manifest.slide_types.items():
            fields = ", ".join(
                f"{f.name} ({f.kind}{'*' if f.required else ''})" for f in sdef.fields
            )
            lines.append(f"  - {name}: {fields or '(no fields)'}")
        return "\n".join(lines)

    def _on_generate_clicked(self) -> None:
        request = self._confirm_prompt.toPlainText().strip()
        if not request:
            self._set_confirm_status(
                "Describe the deck you want, then click Generate.", error=True
            )
            return
        self._set_generating(True)
        self._set_confirm_status("Starting…", error=False)
        self.generate_requested.emit(self._manifest, request)

    # ── Worker slots (called on the main thread by MainWindow connections) ──────
    def on_generate_started(self) -> None:
        self._set_generating(True)

    def on_generate_progress(self, msg: str) -> None:
        self._set_confirm_status(msg, error=False)

    def on_generate_completed(self, content: object) -> None:
        self._set_generating(False)
        self._content = content
        self._out_path = self._build_out_path()
        self._preview_edit.setPlainText(json.dumps(content, indent=2))
        self._clear_preview_error()
        self._stack.setCurrentWidget(self._preview_page)

    def on_generate_failed(self, msg: str) -> None:
        self._set_generating(False)
        self._set_confirm_status(msg, error=True)  # stay on confirm

    def _set_generating(self, flag: bool) -> None:
        self._generating = flag
        self._confirm_generate_btn.setEnabled(not flag)
        self._confirm_back_btn.setEnabled(not flag)
        self._confirm_generate_btn.setText("Generating…" if flag else "Generate")

    # ── Preview / render ────────────────────────────────────────────────────────
    def _on_render_clicked(self) -> None:
        self._clear_preview_error()
        try:
            parsed = json.loads(self._preview_edit.toPlainText())
        except json.JSONDecodeError as exc:
            self._set_preview_error(
                f"That is not valid JSON (line {exc.lineno}, column {exc.colno})."
            )
            return
        ok, result = validate_content(self._manifest, parsed)
        if not ok:
            self._set_preview_error(format_validation_errors(result))
            return
        self._do_render(result)

    def _do_render(self, content: dict) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = render(self._manifest, content, self._out_path, self._template_dir)
        except ManipulationError as exc:
            logger.error("Render failed (manipulation): %s", exc)
            self._set_preview_error(
                "Could not save the presentation, or the template and its manifest "
                "are out of sync."
            )
            return
        except ValueError as exc:
            logger.error("Render failed (template open): %s", exc)
            self._set_preview_error(
                "The template file could not be opened as a PowerPoint file."
            )
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._rendered_path = str(result["path"])
        msg = "Presentation created."
        if result["issues"]:
            msg += f"  ({len(result['issues'])} formatting note(s))"
        self._done_label.setText(msg)
        self._stack.setCurrentWidget(self._done_page)

    def _build_out_path(self) -> Path:
        base = self._selected["name"] if self._selected else "deck"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(self._settings.generated_dir) / f"{base}_{ts}.pptx"

    def _on_open_file(self) -> None:
        if self._rendered_path:
            try:
                os.startfile(self._rendered_path)
            except OSError as exc:
                logger.error("Could not open file %s: %s", self._rendered_path, exc)

    # ── Inline-status helpers ────────────────────────────────────────────────────
    def _show_selection_error(self, msg: str) -> None:
        self._sel_error.setText(msg)
        self._sel_error.setVisible(True)

    def _clear_selection_error(self) -> None:
        self._sel_error.setVisible(False)

    def _set_confirm_status(self, msg: str, error: bool) -> None:
        self._confirm_status.setStyleSheet(
            f"color: {ERROR_COLOR if error else BODY_TEXT_COLOR};"
        )
        self._confirm_status.setText(msg)
        self._confirm_status.setVisible(bool(msg))

    def _set_preview_error(self, msg: str) -> None:
        self._preview_error.setText(msg)
        self._preview_error.setVisible(True)

    def _clear_preview_error(self) -> None:
        self._preview_error.setVisible(False)

    # ── Close discipline (block dismissal during in-flight generation) ──────────
    def reject(self) -> None:
        if self._generating:
            return
        super().reject()

    def closeEvent(self, event) -> None:
        if self._generating:
            event.ignore()
            return
        super().closeEvent(event)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_template_dialog.py -v`
Expected: PASS (all hard-stop + TemplateDialog tests).

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/template_dialog.py tests/test_template_dialog.py
git commit -m "$(cat <<'EOF'
feat(phase-k): TemplateDialog state machine (select/confirm/preview/render)

Modal QStackedWidget flow. Synchronous import (with hard-stop routing) and
render with wait cursor; async generate via generate_requested + on_generate_*
slots. Editable JSON preview re-validated through validate_content (no second
validator). Inline error surfaces; close blocked during generation.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: CreatePanel entry point

**Files:**
- Modify: `simplicitor/app/widgets/create_panel.py`
- Test: `tests/test_template_dialog.py` (append entry-point test)

- [ ] **Step 1: Append failing test**

Append to `tests/test_template_dialog.py`:
```python
# --- CreatePanel entry point ----------------------------------------------
from app.widgets.create_panel import CreatePanel


def test_create_panel_emits_template_requested(qtbot, tmp_path):
    settings = SimpleNamespace(generated_dir=str(tmp_path))
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    panel.set_ollama_connected(True)
    assert panel._from_template_btn.isEnabled()
    with qtbot.waitSignal(panel.template_requested, timeout=2000):
        qtbot.mouseClick(panel._from_template_btn, Qt.MouseButton.LeftButton)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_template_dialog.py -k template_requested -v`
Expected: FAIL with `AttributeError: 'CreatePanel' object has no attribute '_from_template_btn'`.

- [ ] **Step 3: Implement (surgical)**

In `simplicitor/app/widgets/create_panel.py`:

Add the signal next to the existing one (after `generate_requested = Signal(str, str, str)`):
```python
    template_requested = Signal()
```

In `_build_ui`, immediately after the block that adds `self._generate_btn` (after `layout.addWidget(self._generate_btn)`), insert:
```python
        # Secondary action: open the template-based PPTX flow (Phase K)
        self._from_template_btn = QPushButton("From template…")
        self._from_template_btn.setObjectName("from_template_btn")
        self._from_template_btn.setFont(body_font)
        self._from_template_btn.setFixedHeight(32)
        self._from_template_btn.setEnabled(False)
        layout.addWidget(self._from_template_btn)
```

In `_connect_signals`, add:
```python
        self._from_template_btn.clicked.connect(self.template_requested)
```

In `set_ollama_connected`, after `self._update_generate_btn_state()`, add:
```python
        self._from_template_btn.setEnabled(connected)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_template_dialog.py -k template_requested -v`
Expected: PASS.

- [ ] **Step 5: Run the widget regression set**

Run: `python -m pytest tests/test_widgets.py tests/test_template_dialog.py -q`
Expected: PASS (existing CreatePanel widget tests still green).

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/widgets/create_panel.py tests/test_template_dialog.py
git commit -m "$(cat <<'EOF'
feat(phase-k): CreatePanel 'From template...' entry point

Adds a secondary button and template_requested signal, enabled when Ollama is
connected. MainWindow opens the TemplateDialog in response.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: MainWindow wiring, worker ownership, teardown

**Files:**
- Modify: `simplicitor/app/main_window.py`
- Test: `tests/test_main_window_template.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_main_window_template.py`:
```python
# tests/test_main_window_template.py
# Phase K: MainWindow template entry-point wiring + worker teardown.
from types import SimpleNamespace

import pytest

from app.main_window import MainWindow
from app.services.ollama_client import OllamaClient


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    # Keep the connectivity poll cheap and offline.
    monkeypatch.setattr(OllamaClient, "check_connection", lambda self: False)
    settings = SimpleNamespace(
        generated_dir=str(tmp_path / "gen"),
        uploads_dir=str(tmp_path / "up"),
        backups_dir=str(tmp_path / "bak"),
        logs_dir=str(tmp_path / "log"),
    )
    win = MainWindow(settings)
    qtbot.addWidget(win)
    yield win
    win.close()


def test_template_requested_without_model_shows_status_no_dialog(window, monkeypatch):
    opened = []
    monkeypatch.setattr(
        "app.main_window.TemplateDialog",
        lambda *a, **k: opened.append(True),
    )
    window._current_model = ""
    shown = []
    monkeypatch.setattr(
        window._create_panel, "show_status",
        lambda message, is_error=False, **k: shown.append((message, is_error)),
    )
    window._on_template_requested()
    assert opened == []                 # dialog never constructed
    assert shown and shown[0][1] is True  # error status shown


def test_template_requested_with_model_opens_dialog_and_tears_down(window, monkeypatch):
    class FakeDialog:
        def __init__(self, *a, **k):
            self.generate_requested = SimpleNamespace(connect=lambda fn: None)
        def exec(self):
            return 0
    monkeypatch.setattr("app.main_window.TemplateDialog", FakeDialog)
    window._current_model = "llama3"
    window._on_template_requested()
    # No generation was triggered, so no thread should be left running.
    assert getattr(window, "_template_thread", None) is None


def test_teardown_template_thread_is_safe_when_absent(window):
    window._template_thread = None
    window._teardown_template_thread()  # must not raise
    assert window._template_thread is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_main_window_template.py -v`
Expected: FAIL (`AttributeError: 'MainWindow' object has no attribute '_on_template_requested'`).

- [ ] **Step 3: Implement**

In `simplicitor/app/main_window.py`:

Add imports near the existing worker/widget imports:
```python
from app.widgets.template_dialog import TemplateDialog
from app.workers.template_worker import TemplateGenerateWorker
```

In `_connect_signals`, after the existing `self._create_panel.generate_requested.connect(...)` line, add:
```python
        self._create_panel.template_requested.connect(self._on_template_requested)
```

Add the handlers (place them after `_on_generate_failed`):
```python
    # ── Template flow (Phase K) ─────────────────────────────────────────────

    def _on_template_requested(self) -> None:
        """Open the template-based PPTX dialog. Guards on a running model."""
        if not self._current_model:
            logger.warning("Template flow requested but no model selected")
            self._create_panel.show_status(
                "No model is currently running. Please start a model in Ollama.",
                is_error=True,
            )
            return
        dialog = TemplateDialog(self._current_model, self._settings, parent=self)
        dialog.generate_requested.connect(
            lambda manifest, request: self._start_template_worker(dialog, manifest, request)
        )
        self._template_dialog = dialog
        dialog.exec()
        # Dialog dismissed: tear down any worker thread it left behind.
        self._teardown_template_thread()
        self._template_dialog = None
        self._recheck_connection.emit()

    def _start_template_worker(self, dialog: TemplateDialog, manifest, request: str) -> None:
        """Create and start the MainWindow-owned template worker thread."""
        if getattr(self, "_template_thread", None) is not None and self._template_thread.isRunning():
            logger.warning("Template generation already running; ignoring")
            return
        self._template_worker = TemplateGenerateWorker(
            manifest, request, self._current_model, self._ollama_client
        )
        self._template_thread = QThread(self)
        self._template_worker.moveToThread(self._template_thread)

        self._template_thread.started.connect(self._template_worker.run)
        self._template_worker.started.connect(dialog.on_generate_started)
        self._template_worker.progress.connect(dialog.on_generate_progress)
        self._template_worker.completed.connect(dialog.on_generate_completed)
        self._template_worker.failed.connect(dialog.on_generate_failed)
        self._template_worker.completed.connect(self._template_thread.quit)
        self._template_worker.failed.connect(self._template_thread.quit)
        self._template_thread.finished.connect(self._template_worker.deleteLater)
        self._template_thread.finished.connect(self._on_template_thread_finished)

        self._template_thread.start()
        logger.info("Template generation started: model=%s", self._current_model)

    def _on_template_thread_finished(self) -> None:
        """Clear the thread reference once it has finished (avoids stale C++ handle)."""
        self._template_thread = None

    def _teardown_template_thread(self) -> None:
        """Quit + bounded-wait the template thread if still running. Safe if absent.

        A blocking Ollama call cannot be interrupted; the bounded wait matches the
        existing closeEvent pattern. The dialog blocks its own close during an
        in-flight generation, so this normally runs against an idle/finished thread.
        """
        thread = getattr(self, "_template_thread", None)
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(2000)
        self._template_thread = None
```

In `closeEvent`, add the template thread teardown alongside the existing ones (after the `_manipulate_thread` block):
```python
        if getattr(self, "_template_thread", None) is not None:
            self._template_thread.quit()
            self._template_thread.wait(2000)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_main_window_template.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Full suite green**

Run: `python -m pytest tests/ -q`
Expected: PASS (entire collected suite, including the pre-existing tests).

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/main_window.py tests/test_main_window_template.py
git commit -m "$(cat <<'EOF'
feat(phase-k): wire template flow into MainWindow

CreatePanel.template_requested opens TemplateDialog (guarded on a running
model). MainWindow owns the TemplateGenerateWorker thread (matching the
existing worker-ownership locus), wires worker signals to the dialog's
on_generate_* slots, and tears the thread down (quit + bounded wait) on
dialog dismissal and in closeEvent.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review (run against the Phase K objective)

**Spec coverage:**
- Template selection (built-in or upload, uploaded pre-selected): Task 4 selection page + `_refresh_templates(select_name=...)` after import.
- Breakdown hard-stop routing: Task 3 + Task 4 `_do_import`/`_prompt_hard_stop`/`_apply_hard_stop_choice`; gated built-in button.
- Detection-report confirmation: Task 4 confirm page (manifest summary always; import report on upload path only, per ruling 5).
- Async generation off the GUI thread: Task 2 worker + Task 6 MainWindow-owned thread.
- Editable JSON preview with re-validation: Task 4 preview page reuses `validate_content` (no second validator); valid and invalid edits both tested.
- Failure surfacing through existing patterns: Task 2 worker mapping + Task 4 inline error labels + Task 6 status guard.
- Signals carrying generating/validating/repairing/rendering/done/failed: worker `progress` phases (generating/validating/repairing), dialog `on_generate_completed`->preview and `_do_render` (rendering happens synchronously), done page, failed slot.

**Placeholder scan:** none — every step has full code and exact commands.

**Type consistency:** `generate_content` returns `dict`; worker `completed = Signal(object)` carries that dict; dialog `on_generate_completed(content)` and `_do_render(content)` consume the same `{"slides": [...]}` shape that `render` expects; `HardStopDialog.choice()` returns `CHOICE_BUILTIN`/`CHOICE_CANCEL` consumed by `_apply_hard_stop_choice`.

**Conformance:** moveToThread reused verbatim (Task 6 mirrors `_on_generate_requested`); StatusBanner/inline-error pattern; per-module `logging.getLogger(__name__)`; only NOTES.md exception types; no new exception types; assert-vs-raise respected (user input handled with control flow, never assert); no-partial-file discipline untouched (render's atomic temp+rename and import_template's no-partial-folder are unchanged).

**Open risk to flag at review:** `_do_import` maps a duplicate-name `ValueError` by substring match (`"already exists"`). If that path matters in practice, a typed signal from `import_template` would be cleaner; deferred (no new exception types in Phase K).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-02-phase-k-gui-integration.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration. Task 1 (the seam) lands and is reviewed before any GUI task starts.

**2. Inline Execution** - execute tasks in this session with checkpoints for review.

Which approach? (No code until explicit Proceed.)
