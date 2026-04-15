# Phase 5: Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete UX polish — dismissible error banners, sanitized user-facing error messages, model change tracking in the Ollama worker, and auto-creation of the generated-files directory.

**Architecture:** Add a reusable `StatusBanner` widget that replaces the plain QLabel status display in both panels. Workers emit sanitized messages; raw exceptions go to the log only. OllamaWorker tracks the running model across polls and emits `model_params_ready` whenever it changes. MainWindow gets a proper `_on_ollama_connected` handler that keeps `_current_model` in sync.

**Tech Stack:** PySide6, Python 3.11+, pytest-qt

---

## What is already complete (no code changes needed)

- Guided prompting: placeholder texts in `PROMPT_PLACEHOLDERS` and `EDIT_PROMPT_PLACEHOLDERS` — done.
- Settings: all four paths, View Logs, Reset to Defaults — done.
- File name generation: sanitized, timestamp, 50-char limit in `_build_output_path` — done.
- Logging: daily rotation, no file content, consistent format — done.
- Threading: QThread + moveToThread pattern, spinners, independent panels — done.
- Prompt preservation on failure: workers never touch UI, prompts never cleared — done.
- Connection drop detection: `_recheck_connection` signal triggers immediate Ollama poll after any failure — done.
- Capability banner: shows/hides on first connection based on `model_params_ready` — partially done (see Task 4 for model-change gap).

## File Structure

**New:**
- `simplicitor/app/widgets/status_banner.py`
- `tests/test_status_banner.py`

**Modified:**
- `simplicitor/app/widgets/create_panel.py` — replace `_status_label` with `_status_banner`
- `simplicitor/app/widgets/edit_panel.py` — replace `_status_label` with `_status_banner`
- `simplicitor/app/workers/generate_worker.py` — split OllamaConnectionError / OllamaGenerationError handling
- `simplicitor/app/workers/manipulate_worker.py` — split OllamaConnectionError / OllamaGenerationError handling
- `simplicitor/app/workers/ollama_worker.py` — track `_last_running_model`, emit on change
- `simplicitor/app/main_window.py` — add `_on_ollama_connected`, auto-mkdir before generation
- `tests/test_widgets.py` — update `_status_label` references → `_status_banner`

---

## Task 1: StatusBanner widget

**Files:**
- Create: `simplicitor/app/widgets/status_banner.py`
- Create: `tests/test_status_banner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_status_banner.py
import pytest
from pytestqt.qtbot import QtBot

from app.widgets.status_banner import StatusBanner


def test_status_banner_hidden_by_default(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    assert not banner.isVisible()


def test_status_banner_shows_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("Operation complete", is_error=False)
    assert banner.isVisible()
    assert "Operation complete" in banner.text()


def test_status_banner_shows_error_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("Something went wrong", is_error=True)
    assert banner.isVisible()
    assert "Something went wrong" in banner.text()


def test_status_banner_hide_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("visible", is_error=False)
    banner.hide_message()
    assert not banner.isVisible()


def test_status_banner_dismiss_button_hides(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("dismiss me", is_error=False)
    banner._dismiss_btn.click()
    assert not banner.isVisible()


def test_status_banner_text_resets_on_new_message(qtbot: QtBot) -> None:
    banner = StatusBanner()
    qtbot.addWidget(banner)
    banner.show_message("first message", is_error=False)
    banner.show_message("second message", is_error=True)
    assert "second message" in banner.text()
    assert "first" not in banner.text()
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd C:\Repos\Simplicitor
python -m pytest tests/test_status_banner.py -v
```

Expected: `ModuleNotFoundError` — `status_banner` doesn't exist yet.

- [ ] **Step 3: Implement the widget**

Create `simplicitor/app/widgets/status_banner.py`:

```python
# simplicitor/app/widgets/status_banner.py
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from app.config.defaults import (
    APP_FONT_FAMILY,
    BODY_TEXT_COLOR,
    ERROR_COLOR,
    FONT_SIZE_BODY_PT,
    SUCCESS_COLOR,
    WHITE,
)


class StatusBanner(QWidget):
    """Dismissible inline banner for success and error status messages.

    Shows a colored left strip + message text + dismiss (✕) button.
    Hidden by default. Call show_message() to display.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        self.setMaximumHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(0)

        self._strip = QFrame()
        self._strip.setFixedWidth(4)
        self._strip.setObjectName("status_strip")
        layout.addWidget(self._strip)

        body_font = QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT)
        self._text_label = QLabel()
        self._text_label.setFont(body_font)
        self._text_label.setContentsMargins(8, 4, 8, 4)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        self._text_label.setWordWrap(True)
        layout.addWidget(self._text_label, stretch=1)

        self._dismiss_btn = QPushButton("\u2715")
        self._dismiss_btn.setObjectName("status_dismiss_btn")
        self._dismiss_btn.setFont(body_font)
        self._dismiss_btn.setFixedSize(24, 24)
        self._dismiss_btn.clicked.connect(self.hide)
        layout.addWidget(self._dismiss_btn)

        self.setStyleSheet(
            f"StatusBanner {{ background-color: {WHITE}; }}"
            "QFrame#status_strip { border: none; }"
            f"QPushButton#status_dismiss_btn {{ border: none; background-color: transparent; "
            f"color: {BODY_TEXT_COLOR}; }}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def show_message(self, message: str, is_error: bool = False) -> None:
        """Display the banner with a message.

        Args:
            message: Text to show in the banner.
            is_error: True for red (error), False for green (success).
        """
        color = ERROR_COLOR if is_error else SUCCESS_COLOR
        self._strip.setStyleSheet(f"QFrame {{ background-color: {color}; }}")
        self._text_label.setText(message)
        self.show()

    def hide_message(self) -> None:
        """Hide the banner."""
        self.hide()

    def text(self) -> str:
        """Return the current banner message text."""
        return self._text_label.text()
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/test_status_banner.py -v
```

Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/status_banner.py tests/test_status_banner.py
git commit -m "feat: add dismissible StatusBanner widget for error/success messages"
```

---

## Task 2: Replace status label in CreatePanel

**Files:**
- Modify: `simplicitor/app/widgets/create_panel.py`
- Modify: `tests/test_widgets.py` (update 2 assertion blocks referencing `_status_label`)

- [ ] **Step 1: Identify all references to `_status_label` in test_widgets.py for CreatePanel context**

Lines 428-429 and 438-439 in `tests/test_widgets.py` access `window._create_panel._status_label`.

Note: no direct `show_status` tests exist for CreatePanel (only EditPanel has them at lines 681-705).

- [ ] **Step 2: Update `create_panel.py` — remove `_status_label`, add `_status_banner`**

In `_build_ui()`, find the status label block:
```python
# OLD (lines to remove):
        # Status label (hidden until needed)
        self._status_label = QLabel()
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
```

Replace with:
```python
        # Status banner (dismissible, hidden until needed)
        self._status_banner = StatusBanner()
        layout.addWidget(self._status_banner)
```

Add import at top of `create_panel.py`:
```python
from app.widgets.status_banner import StatusBanner
```

Update `show_status()`:
```python
    def show_status(self, message: str, is_error: bool = False) -> None:
        """Show a status message below the Generate button.

        Args:
            message: The message text to display.
            is_error: If True, display message in error color; otherwise success color.
        """
        self._status_banner.show_message(message, is_error)
```

Update `clear_status()`:
```python
    def clear_status(self) -> None:
        """Hide the status banner."""
        self._status_banner.hide_message()
```

- [ ] **Step 3: Update test_widgets.py — MainWindow generate tests**

At lines 428-429, change:
```python
# OLD:
    assert window._create_panel._status_label.isVisible()
    assert "report.docx" in window._create_panel._status_label.text()
# NEW:
    assert window._create_panel._status_banner.isVisible()
    assert "report.docx" in window._create_panel._status_banner.text()
```

At lines 438-439, change:
```python
# OLD:
    assert window._create_panel._status_label.isVisible()
    assert "AI generation failed" in window._create_panel._status_label.text()
# NEW:
    assert window._create_panel._status_banner.isVisible()
    assert "AI generation failed" in window._create_panel._status_banner.text()
```

- [ ] **Step 4: Run the full test suite to verify no regressions**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass (≥311 + 6 new = 317+).

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/create_panel.py tests/test_widgets.py
git commit -m "refactor: replace status QLabel with dismissible StatusBanner in CreatePanel"
```

---

## Task 3: Replace status label in EditPanel

**Files:**
- Modify: `simplicitor/app/widgets/edit_panel.py`
- Modify: `tests/test_widgets.py` (update 5 assertion blocks)

- [ ] **Step 1: Update `edit_panel.py` — remove `_status_label`, add `_status_banner`**

In `_build_ui()`, find the status label block:
```python
# OLD (remove this block):
        # Status label (hidden until needed)
        self._status_label = QLabel()
        self._status_label.setFont(body_font)
        self._status_label.setVisible(False)
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)
```

Replace with:
```python
        # Status banner (dismissible, hidden until needed)
        self._status_banner = StatusBanner()
        layout.addWidget(self._status_banner)
```

Add import at top of `edit_panel.py`:
```python
from app.widgets.status_banner import StatusBanner
```

Update `show_status()`:
```python
    def show_status(self, message: str, is_error: bool = False) -> None:
        """Show a status message below the Save button.

        Args:
            message: The message to display.
            is_error: True for red text (error), False for green (success).
        """
        self._status_banner.show_message(message, is_error)
```

Update `clear_status()`:
```python
    def clear_status(self) -> None:
        """Hide the status banner."""
        self._status_banner.hide_message()
```

- [ ] **Step 2: Update test_widgets.py — EditPanel direct status tests (lines 681-705)**

```python
# test_edit_panel_show_status_green (lines 686-687):
# OLD:
    assert panel._status_label.isVisible()
    assert "Done!" in panel._status_label.text()
# NEW:
    assert panel._status_banner.isVisible()
    assert "Done!" in panel._status_banner.text()

# test_edit_panel_show_status_red (lines 695-696):
# OLD:
    assert panel._status_label.isVisible()
    assert "Something broke" in panel._status_label.text()
# NEW:
    assert panel._status_banner.isVisible()
    assert "Something broke" in panel._status_banner.text()

# test_edit_panel_clear_status (line 705):
# OLD:
    assert not panel._status_label.isVisible()
# NEW:
    assert not panel._status_banner.isVisible()
```

- [ ] **Step 3: Update test_widgets.py — MainWindow manipulate tests (lines 740-751)**

```python
# test_main_window_on_save_completed_shows_status (lines 740-741):
# OLD:
    assert window._edit_panel._status_label.isVisible()
    assert "result.docx" in window._edit_panel._status_label.text()
# NEW:
    assert window._edit_panel._status_banner.isVisible()
    assert "result.docx" in window._edit_panel._status_banner.text()

# test_main_window_on_save_failed_shows_error (lines 750-751):
# OLD:
    assert window._edit_panel._status_label.isVisible()
    assert "Could not read" in window._edit_panel._status_label.text()
# NEW:
    assert window._edit_panel._status_banner.isVisible()
    assert "Could not read" in window._edit_panel._status_banner.text()
```

- [ ] **Step 4: Run the full test suite**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add simplicitor/app/widgets/edit_panel.py tests/test_widgets.py
git commit -m "refactor: replace status QLabel with dismissible StatusBanner in EditPanel"
```

---

## Task 4: Sanitize worker error messages

**Files:**
- Modify: `simplicitor/app/workers/generate_worker.py`
- Modify: `simplicitor/app/workers/manipulate_worker.py`
- Modify: `tests/test_generate_worker.py` or `tests/test_workers.py` (update error-message assertions)

**Context:** Currently both workers include raw exception strings in emitted failure messages (e.g., `f"AI generation failed: {exc}"`). An `OllamaConnectionError` wraps a `requests.RequestException` which can contain HTTP connection pool details. These must not reach the user.

- [ ] **Step 1: Write failing tests for sanitized messages**

Add to the generate worker test file (find the test for connection errors and update the expected message):

```python
# In tests/test_generate_worker.py (or whichever file tests GenerateWorker)
# Find tests that assert on the "failed" signal message and update:

def test_generate_worker_connection_error_message_is_user_friendly(qtbot, tmp_path):
    """OllamaConnectionError must not expose raw HTTP details to the user."""
    from unittest.mock import MagicMock, patch
    from app.workers.generate_worker import GenerateWorker
    from app.services.ollama_client import OllamaConnectionError, OllamaClient

    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = OllamaConnectionError(
        "HTTPConnectionPool(host='localhost', port=11434): Max retries exceeded"
    )

    worker = GenerateWorker("Word (.docx)", str(tmp_path / "out.docx"), "test", "llama3", client)
    failed_messages = []
    worker.failed.connect(failed_messages.append)

    worker.run()

    assert len(failed_messages) == 1
    msg = failed_messages[0]
    assert "HTTPConnectionPool" not in msg
    assert "Max retries" not in msg
    assert "AI engine" in msg.lower() or "ollama" in msg.lower() or "not respond" in msg.lower()


def test_generate_worker_generation_error_message_is_user_friendly(qtbot, tmp_path):
    """OllamaGenerationError must not expose HTTP status codes to the user."""
    from unittest.mock import MagicMock, patch
    from app.workers.generate_worker import GenerateWorker
    from app.services.ollama_client import OllamaGenerationError, OllamaClient

    client = MagicMock(spec=OllamaClient)
    client.generate.side_effect = OllamaGenerationError(
        "Ollama returned status 500: Internal Server Error"
    )

    worker = GenerateWorker("Word (.docx)", str(tmp_path / "out.docx"), "test", "llama3", client)
    failed_messages = []
    worker.failed.connect(failed_messages.append)

    worker.run()

    assert len(failed_messages) == 1
    msg = failed_messages[0]
    assert "500" not in msg
    assert "Internal Server Error" not in msg
```

- [ ] **Step 2: Run to verify tests fail**

```
python -m pytest tests/ -k "user_friendly" -v
```

Expected: FAIL — current messages expose raw exception strings.

- [ ] **Step 3: Update `generate_worker.py` — split error handling**

Find the Ollama generate call (around line 91-95):
```python
# OLD:
        try:
            llm_response = self._client.generate(self.model, self.prompt, system_prompt)
        except (OllamaConnectionError, OllamaGenerationError) as exc:
            logger.error("Ollama generation failed: %s", exc)
            self.failed.emit(f"AI generation failed: {exc}")
            return
```

Replace with:
```python
        try:
            llm_response = self._client.generate(self.model, self.prompt, system_prompt)
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during generation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return
```

Also update the retry block (around line 113-119):
```python
# OLD:
            except (OllamaConnectionError, OllamaGenerationError) as retry_exc:
                logger.error("Retry Ollama call failed: %s", retry_exc)
                self.failed.emit(
                    "AI generation failed after retry. Please check Ollama is running."
                )
                return
```

Replace with:
```python
            except (OllamaConnectionError, OllamaGenerationError) as retry_exc:
                logger.error("Retry Ollama call failed: %s", retry_exc)
                self.failed.emit(
                    "The AI engine stopped responding. Please check Ollama is running."
                )
                return
```

- [ ] **Step 4: Update `manipulate_worker.py` — split error handling**

Find the Ollama generate call (around line 110-113):
```python
# OLD:
        try:
            llm_response = self._client.generate(self.model, user_prompt, system_prompt)
        except (OllamaConnectionError, OllamaGenerationError) as exc:
            logger.error("Ollama call failed: %s", exc)
            self.failed.emit(f"AI processing failed: {exc}")
            return
```

Replace with:
```python
        try:
            llm_response = self._client.generate(self.model, user_prompt, system_prompt)
        except OllamaConnectionError as exc:
            logger.error("Ollama connection lost during manipulation: %s", exc)
            self.failed.emit(
                "The AI engine stopped responding. Please check Ollama is running."
            )
            return
        except OllamaGenerationError as exc:
            logger.error("Ollama generation error: %s", exc)
            self.failed.emit("The AI returned an unexpected response. Please try again.")
            return
```

- [ ] **Step 5: Run the new tests to verify they pass**

```
python -m pytest tests/ -k "user_friendly" -v
```

Expected: PASS.

- [ ] **Step 6: Run full test suite**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass. (Note: any existing test that asserts `"AI generation failed"` in a message produced by the *worker* will need updating to the new message text. Tests that pass the string directly to `_on_generate_failed` are unaffected since that handler just forwards the string unchanged.)

- [ ] **Step 7: Commit**

```bash
git add simplicitor/app/workers/generate_worker.py simplicitor/app/workers/manipulate_worker.py tests/
git commit -m "fix: sanitize worker error messages — raw exceptions go to log, not user"
```

---

## Task 5: OllamaWorker model change detection

**Files:**
- Modify: `simplicitor/app/workers/ollama_worker.py`
- Modify: `tests/test_ollama_worker.py` (add model-change tests)

**Context:** `model_params_ready` currently fires only on the `disconnected → connected` transition. If the user loads a different model while the app is already connected, the capability banner and `set_model_small` flag in CreatePanel are never updated.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_ollama_worker.py`:

```python
def test_ollama_worker_emits_params_on_model_change_while_connected():
    """model_params_ready must fire when the running model changes mid-session."""
    from unittest.mock import MagicMock, patch
    from app.workers.ollama_worker import OllamaWorker
    from app.services.ollama_client import OllamaClient

    client = MagicMock(spec=OllamaClient)
    client.check_connection.return_value = True
    client.get_models.return_value = ["modelA", "modelB"]
    client.get_running_model.side_effect = ["modelA", "modelA", "modelB"]
    client.get_model_params.return_value = 7_000_000_000

    worker = OllamaWorker(client)
    params_signals = []
    worker.model_params_ready.connect(lambda name, count: params_signals.append((name, count)))

    worker._poll()  # first poll: disconnected → connected, modelA running
    worker._poll()  # second poll: still connected, still modelA — no new signal
    worker._poll()  # third poll: still connected, now modelB running — should emit

    # First poll emits (first connection), third poll emits (model changed)
    assert len(params_signals) == 2
    assert params_signals[0][0] == "modelA"
    assert params_signals[1][0] == "modelB"


def test_ollama_worker_no_duplicate_params_on_stable_model():
    """model_params_ready must NOT fire on every poll when the model is unchanged."""
    from unittest.mock import MagicMock
    from app.workers.ollama_worker import OllamaWorker
    from app.services.ollama_client import OllamaClient

    client = MagicMock(spec=OllamaClient)
    client.check_connection.return_value = True
    client.get_models.return_value = ["modelA"]
    client.get_running_model.return_value = "modelA"
    client.get_model_params.return_value = 7_000_000_000

    worker = OllamaWorker(client)
    params_signals = []
    worker.model_params_ready.connect(lambda name, count: params_signals.append((name, count)))

    worker._poll()  # first: emit (first connection)
    worker._poll()  # second: same model, no emit
    worker._poll()  # third: same model, no emit

    assert len(params_signals) == 1


def test_ollama_worker_emits_empty_params_when_model_unloaded():
    """When running model goes from something to empty, emit model_params_ready('', 0)."""
    from unittest.mock import MagicMock
    from app.workers.ollama_worker import OllamaWorker
    from app.services.ollama_client import OllamaClient

    client = MagicMock(spec=OllamaClient)
    client.check_connection.return_value = True
    client.get_models.return_value = ["modelA"]
    client.get_running_model.side_effect = ["modelA", ""]
    client.get_model_params.return_value = 7_000_000_000

    worker = OllamaWorker(client)
    params_signals = []
    worker.model_params_ready.connect(lambda name, count: params_signals.append((name, count)))

    worker._poll()  # first: modelA running, emit
    worker._poll()  # second: no model running, emit ("", 0)

    assert len(params_signals) == 2
    assert params_signals[1] == ("", 0)
```

- [ ] **Step 2: Run to verify tests fail**

```
python -m pytest tests/test_ollama_worker.py -k "model_change or duplicate or unloaded" -v
```

Expected: FAIL.

- [ ] **Step 3: Update `ollama_worker.py`**

Add `_last_running_model` to `__init__`:
```python
    def __init__(self, client: OllamaClient) -> None:
        super().__init__()
        self._client = client
        self._timer: QTimer | None = None
        self._was_connected: bool = False
        self._last_running_model: str = ""
```

Replace the `_poll()` method body (the `if is_connected:` branch):
```python
    def _poll(self) -> None:
        """Check Ollama connectivity and emit the appropriate signal.

        Emits ``model_params_ready`` on first connection and whenever the
        running model changes (including when it goes to empty string).
        Never raises.
        """
        try:
            is_connected = self._client.check_connection()

            if is_connected:
                models: list[str] = self._client.get_models()
                running_model: str = self._client.get_running_model()

                model_changed = running_model != self._last_running_model
                first_connection = not self._was_connected

                if first_connection or model_changed:
                    if running_model:
                        try:
                            param_count: int = self._client.get_model_params(running_model)
                            self.model_params_ready.emit(running_model, param_count)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning("Could not fetch model params: %s", exc)
                    else:
                        # Model was unloaded — signal 0 params so banner hides
                        self.model_params_ready.emit("", 0)
                    self._last_running_model = running_model

                self._was_connected = True
                self.connected.emit(models, running_model)
            else:
                self._was_connected = False
                self._last_running_model = ""
                self.disconnected.emit()

        except Exception as exc:  # pragma: no cover — defensive catch-all
            logger.warning("OllamaWorker._poll() raised an unexpected exception: %s", exc)
            self._was_connected = False
            self._last_running_model = ""
            self.disconnected.emit()
```

- [ ] **Step 4: Run the new tests**

```
python -m pytest tests/test_ollama_worker.py -v
```

Expected: all pass.

- [ ] **Step 5: Run full suite**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add simplicitor/app/workers/ollama_worker.py tests/test_ollama_worker.py
git commit -m "fix: emit model_params_ready when running model changes while connected"
```

---

## Task 6: MainWindow — `_on_ollama_connected` + auto-mkdir

**Files:**
- Modify: `simplicitor/app/main_window.py`
- Modify: `tests/test_widgets.py` (add 2 tests)

**Context:** Two gaps:
1. `_current_model` is only updated via `_on_model_params_ready` (first connection) and `_on_model_changed` (TopBar combo — but signals are blocked when TopBar updates automatically). If the model changes while connected, `_current_model` is stale. Fix: update `_current_model` directly in the `connected` signal handler.
2. If the user's configured `generated_dir` doesn't exist yet, the generator fails with an OSError. Fix: `mkdir` before starting the worker.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_widgets.py`:

```python
def test_main_window_current_model_updated_on_connected(qtbot, tmp_path) -> None:
    """_current_model must be updated from the connected signal, not just model_params_ready."""
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)

    # Simulate connected signal with a running model
    window._on_ollama_connected(["gemma3"], "gemma3")
    assert window._current_model == "gemma3"


def test_main_window_generate_creates_output_dir(qtbot, tmp_path) -> None:
    """_on_generate_requested must create the output directory if it doesn't exist."""
    from unittest.mock import patch, MagicMock
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    window._current_model = "llama3"

    new_dir = tmp_path / "nonexistent" / "subdir"
    assert not new_dir.exists()

    # Patch QThread.start to prevent actual worker execution
    with patch.object(window, '_generate_thread', create=True) as mock_thread:
        mock_thread.isRunning.return_value = False
        with patch('app.main_window.QThread') as MockQThread:
            MockQThread.return_value.isRunning.return_value = False
            window._on_generate_requested("Word (.docx)", str(new_dir), "test prompt")

    assert new_dir.exists()
```

- [ ] **Step 2: Run to verify tests fail**

```
python -m pytest tests/test_widgets.py -k "current_model_updated or generate_creates" -v
```

Expected: FAIL.

- [ ] **Step 3: Add `_on_ollama_connected` to `main_window.py`**

In `_start_ollama_worker()`, find the two lambda connections for CreatePanel and EditPanel:
```python
        # OLD — remove these two:
        self._ollama_worker.connected.connect(
            lambda models, _: self._create_panel.set_ollama_connected(True)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._create_panel.set_ollama_connected(False)
        )
        # ...
        # Connectivity → EditPanel
        self._ollama_worker.connected.connect(
            lambda models, _: self._edit_panel.set_ollama_connected(True)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._edit_panel.set_ollama_connected(False)
        )
```

Replace the two `connected` lambdas with a single proper connection:
```python
        # Connectivity → panels (use named method to also track _current_model)
        self._ollama_worker.connected.connect(self._on_ollama_connected)
        self._ollama_worker.disconnected.connect(
            lambda: self._create_panel.set_ollama_connected(False)
        )
        self._ollama_worker.disconnected.connect(
            lambda: self._edit_panel.set_ollama_connected(False)
        )
```

Add the new slot method in the `# ── Slots` section (after `_on_banner_dismissed`):
```python
    def _on_ollama_connected(self, models: list[str], current_model: str) -> None:
        """Handle Ollama connected signal — update panels and track the running model.

        Args:
            models: Full list of installed model names.
            current_model: The model currently loaded in Ollama, or "" if none.
        """
        self._create_panel.set_ollama_connected(True)
        self._edit_panel.set_ollama_connected(True)
        if current_model:
            self._current_model = current_model
```

Also update the docstring on `_connect_signals` / `_start_ollama_worker` to note this replaces the two `connected` lambdas.

- [ ] **Step 4: Add auto-mkdir to `_on_generate_requested`**

Find `_on_generate_requested` in `main_window.py`. After the early-exit guard for no model and the running-thread guard, find:

```python
        effective_save_dir = save_dir or self._settings.generated_dir
        output_path = self._build_output_path(file_type, effective_save_dir, prompt)
```

Replace with:
```python
        effective_save_dir = save_dir or self._settings.generated_dir
        try:
            Path(effective_save_dir).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.error("Cannot create output directory %s: %s", effective_save_dir, exc)
            self._create_panel.show_status(
                "Cannot create the output folder. Check the path is valid and you have write permission.",
                is_error=True,
            )
            return
        output_path = self._build_output_path(file_type, effective_save_dir, prompt)
```

Make sure `Path` is already imported — it comes from `pathlib` which should already be in the imports. If not, add `from pathlib import Path`.

- [ ] **Step 5: Run the new tests**

```
python -m pytest tests/test_widgets.py -k "current_model_updated or generate_creates" -v
```

Expected: PASS.

- [ ] **Step 6: Run full suite**

```
python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add simplicitor/app/main_window.py tests/test_widgets.py
git commit -m "fix: track current model from connected signal; auto-create generated_dir before write"
```

---

## Task 7: Final verification

**Files:** None (read-only audit)

- [ ] **Step 1: Run the complete test suite and confirm count**

```
python -m pytest tests/ -v 2>&1 | tail -5
```

Expected: all tests pass. Count should be ≥ 311 + 6 (StatusBanner) + 3 (OllamaWorker model change) + 2 (connection errors) + 2 (MainWindow) = 324+.

- [ ] **Step 2: Launch the app and do a manual walkthrough**

```
cd C:\Repos\Simplicitor\simplicitor
python main.py
```

Verify:
- With Ollama disconnected: red dot, retry buttons show in both panels, no crashes.
- Start Ollama: auto-connects within 5s, green dot, model shown.
- Generate a Word doc: spinner on button, then success banner with X dismiss button appears.
- Click X: banner dismisses.
- Disconnect Ollama mid-generation (kill Ollama process): error banner appears, indicator goes red promptly, prompt text is preserved.
- Load a small model (<7B): info banner appears above panels, can be dismissed.
- Load a larger model: info banner hides.
- Open Settings → change paths → Reset to Defaults → save works.

- [ ] **Step 3: Commit any final adjustments**

```bash
git add -p
git commit -m "chore: phase 5 polish complete — verify manual walkthrough"
```

---

## Self-Review

**Spec coverage check:**

| Phase 5 task | Covered by |
|---|---|
| Error UX audit: dismissible banners | Tasks 1-3 |
| Error UX audit: no stack traces / HTTP codes | Task 4 |
| Connection drop mid-operation | Already implemented (`_recheck_connection`); prompt preserved by design |
| Model capability banner on model switch | Task 5 |
| Inline tip for complex prompts on sub-7B | Already implemented in CreatePanel |
| Guided prompting placeholders | Already implemented |
| Settings: all four paths, View Logs, Reset | Already implemented |
| Directories auto-created if missing | Task 6 (generated_dir); others already auto-created |
| File name generation: sanitize, timestamp | Already implemented in `_build_output_path` |
| Threading audit | Already correct; no changes needed |
| Logging audit | Already correct; no changes needed |

**Placeholder scan:** No TBD, TODO, or "similar to task N" references. All code blocks are complete.

**Type consistency:**
- `StatusBanner.show_message(message: str, is_error: bool = False)` — used consistently in Tasks 2 and 3.
- `StatusBanner.hide_message()` — used in `clear_status()` in both panels.
- `StatusBanner.text() -> str` — used in test assertions in Tasks 2 and 3.
- `OllamaWorker._last_running_model: str` — initialized in `__init__`, reset on disconnect, updated in `_poll()`.
- `MainWindow._on_ollama_connected(models: list[str], current_model: str)` — signature matches `OllamaWorker.connected = Signal(list, str)`.
