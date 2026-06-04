# tests/test_main_window_template.py
# Phase K Task 6: MainWindow template-flow wiring.
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.main_window import MainWindow
from app.parsers.llm_response_parser import ParseError
from app.services.ollama_client import OllamaClient
from app.widgets.template_dialog import TemplateDialog
from templates_engine.manifest import load_manifest

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)
CONTENT = {"slides": [{"type": "title_slide", "fields": {"title": "X"}}]}


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    # Keep the connectivity poll cheap and offline.
    monkeypatch.setattr(OllamaClient, "check_connection", lambda self: False)
    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.close()


def test_template_requested_without_model_does_not_open(window, monkeypatch):
    opened = []
    monkeypatch.setattr("app.main_window.TemplateDialog", lambda *a, **k: opened.append(True))
    window._current_model = ""
    shown = []
    monkeypatch.setattr(
        window._create_panel, "show_status",
        lambda message, is_error=False, **k: shown.append((message, is_error)),
    )
    window._on_template_requested()
    assert opened == []                     # dialog never constructed
    assert shown and shown[0][1] is True    # error affordance surfaced


def test_template_requested_with_model_opens_dialog(window, monkeypatch):
    seen = {}

    class FakeDialog:
        def __init__(self, settings, parent=None):
            seen["constructed"] = True
            self.generate_requested = MagicMock()

        def exec(self):
            seen["exec"] = True
            return 0

    monkeypatch.setattr("app.main_window.TemplateDialog", FakeDialog)
    window._current_model = "llama3"
    window._on_template_requested()
    assert seen.get("constructed") and seen.get("exec")
    assert getattr(window, "_template_thread", None) is None  # no generation triggered


def test_worker_routes_completed_to_dialog(window, qtbot, monkeypatch):
    # Real worker + real dialog + MainWindow-owned thread; mock generate_content at the boundary.
    manifest = load_manifest(FIXTURE_MANIFEST)
    dialog = TemplateDialog(window._settings)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "templates_engine.pipeline.generate_content", MagicMock(return_value=CONTENT)
    )
    window._current_model = "llama3"
    window._start_template_worker(dialog, manifest, "make a deck")
    qtbot.waitUntil(lambda: dialog._stack.currentWidget() is dialog._preview_page, timeout=5000)
    assert "title_slide" in dialog._preview_edit.toPlainText()
    assert dialog._generating is False   # on_generate_completed cleared the generating flag
    window._teardown_template_thread()
    assert window._template_thread is None


def test_worker_routes_failed_to_dialog(window, qtbot, monkeypatch):
    manifest = load_manifest(FIXTURE_MANIFEST)
    dialog = TemplateDialog(window._settings)
    qtbot.addWidget(dialog)
    dialog._stack.setCurrentWidget(dialog._confirm_page)  # generation starts from CONFIRM
    monkeypatch.setattr(
        "templates_engine.pipeline.generate_content",
        MagicMock(side_effect=ParseError("invalid after repair", details="x")),
    )
    window._current_model = "llama3"
    window._start_template_worker(dialog, manifest, "make a deck")
    qtbot.waitUntil(
        lambda: dialog._confirm_status.isVisible()
        and "valid slide structure" in dialog._confirm_status.text(),
        timeout=5000,
    )
    assert dialog._stack.currentWidget() is dialog._confirm_page  # stayed on CONFIRM
    window._teardown_template_thread()


def test_template_thread_torn_down_on_close(window, qtbot, monkeypatch):
    manifest = load_manifest(FIXTURE_MANIFEST)
    dialog = TemplateDialog(window._settings)
    qtbot.addWidget(dialog)
    monkeypatch.setattr(
        "templates_engine.pipeline.generate_content", MagicMock(return_value=CONTENT)
    )
    window._current_model = "llama3"
    window._start_template_worker(dialog, manifest, "x")
    qtbot.waitUntil(lambda: getattr(window, "_template_thread", None) is None, timeout=5000)
    window.close()  # closeEvent must be safe with a finished/cleared thread
    assert getattr(window, "_template_thread", None) is None


def test_teardown_template_thread_safe_when_absent(window):
    window._template_thread = None
    window._teardown_template_thread()   # must not raise
    assert window._template_thread is None
