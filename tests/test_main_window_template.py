# tests/test_main_window_template.py
# MainWindow template-flow wiring: picker -> loaded state -> template-aware Generate.
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.main_window import MainWindow
from app.services.ollama_client import OllamaClient
from templates_engine.manifest import load_manifest

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)

WORD = "Word (.docx)"
PPTX = "PowerPoint (.pptx)"


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    # Keep the connectivity poll cheap and offline.
    monkeypatch.setattr(OllamaClient, "check_connection", lambda self: False)
    settings = Settings(tmp_path)
    # Keep the picker-open seeding hermetic: the default templates_dir points at the
    # real ~/Documents, which _on_template_requested now seeds.
    settings.set("templates_dir", str(tmp_path / "templates"))
    win = MainWindow(settings)
    qtbot.addWidget(win)
    yield win
    win.close()


# --- picker open ------------------------------------------------------------

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


def test_template_requested_with_model_opens_picker(window, monkeypatch):
    seen = {}

    class FakeDialog:
        def __init__(self, templates_dir, parent=None):
            seen["constructed"] = True
            seen["templates_dir"] = templates_dir
            self.template_selected = MagicMock()

        def exec(self):
            seen["exec"] = True
            return 0

    monkeypatch.setattr("app.main_window.TemplateDialog", FakeDialog)
    window._current_model = "llama3"
    window._on_template_requested()
    assert seen.get("constructed") and seen.get("exec")
    assert seen["templates_dir"] == window._settings.templates_dir  # picker uses the setting
    assert window._loaded_template is None  # opening alone does not load a template


def test_template_requested_seeds_defaults_into_configured_folder(window, tmp_path, monkeypatch):
    """Changing the Templates folder in Settings after startup must not dead-end the
    picker: opening it re-seeds the curated defaults into the configured folder."""
    from templates_engine.config import DEFAULT_TEMPLATE_NAMES, list_library

    fresh_root = tmp_path / "fresh_templates"  # folder changed in Settings; never seeded
    window._settings.set("templates_dir", str(fresh_root))

    class FakeDialog:
        def __init__(self, templates_dir, parent=None):
            self.template_selected = MagicMock()

        def exec(self):
            return 0

    monkeypatch.setattr("app.main_window.TemplateDialog", FakeDialog)
    window._current_model = "llama3"
    window._on_template_requested()
    names = {t["name"] for t in list_library(fresh_root)}
    assert names == set(DEFAULT_TEMPLATE_NAMES)

    window._on_template_requested()  # idempotency smoke: re-open must not raise
    names_after = {t["name"] for t in list_library(fresh_root)}
    assert names_after == set(DEFAULT_TEMPLATE_NAMES)


# --- loaded-template state --------------------------------------------------

def test_template_selected_stores_and_relabels(window):
    manifest = load_manifest(FIXTURE_MANIFEST)
    window._on_template_selected(manifest, "C:/tmpl/deck", "deck")
    assert window._loaded_template["name"] == "deck"
    assert window._loaded_template["manifest"] is manifest
    assert window._create_panel._from_template_btn.text() == "From Template: selected"


def test_file_type_off_pptx_clears_loaded_template(window):
    window._loaded_template = {"manifest": object(), "dir": "d", "name": "deck"}
    window._create_panel.set_template_loaded(True)
    window._on_file_type_changed(WORD)
    assert window._loaded_template is None
    assert "From template" in window._create_panel._from_template_btn.text()
    assert window._create_panel._from_template_btn.text() != "From Template: selected"


def test_file_type_pptx_keeps_loaded_template(window):
    sentinel = {"manifest": object(), "dir": "d", "name": "deck"}
    window._loaded_template = sentinel
    window._on_file_type_changed(PPTX)
    assert window._loaded_template is sentinel


# --- Generate routing -------------------------------------------------------

def test_generate_routes_to_template_when_loaded_and_pptx(window, tmp_path, monkeypatch):
    calls = {"template": [], "freeform": []}
    monkeypatch.setattr(window, "_start_template_generation",
                        lambda out, prompt: calls["template"].append((out, prompt)))
    monkeypatch.setattr(window, "_start_freeform_generation",
                        lambda ft, out, prompt: calls["freeform"].append(ft))
    window._current_model = "llama3"
    window._loaded_template = {"manifest": object(), "dir": str(tmp_path), "name": "deck"}
    window._on_generate_requested(PPTX, str(tmp_path), "make a deck")
    assert len(calls["template"]) == 1
    assert calls["freeform"] == []
    assert calls["template"][0][1] == "make a deck"


def test_generate_routes_to_freeform_when_loaded_but_not_pptx(window, tmp_path, monkeypatch):
    calls = {"template": 0, "freeform": []}
    monkeypatch.setattr(window, "_start_template_generation",
                        lambda out, prompt: calls.__setitem__("template", calls["template"] + 1))
    monkeypatch.setattr(window, "_start_freeform_generation",
                        lambda ft, out, prompt: calls["freeform"].append(ft))
    window._current_model = "llama3"
    window._loaded_template = {"manifest": object(), "dir": str(tmp_path), "name": "deck"}
    window._on_generate_requested(WORD, str(tmp_path), "make a doc")
    assert calls["template"] == 0
    assert calls["freeform"] == [WORD]


def test_generate_routes_to_freeform_when_not_loaded(window, tmp_path, monkeypatch):
    calls = {"template": 0, "freeform": []}
    monkeypatch.setattr(window, "_start_template_generation",
                        lambda out, prompt: calls.__setitem__("template", calls["template"] + 1))
    monkeypatch.setattr(window, "_start_freeform_generation",
                        lambda ft, out, prompt: calls["freeform"].append(ft))
    window._current_model = "llama3"
    window._loaded_template = None
    window._on_generate_requested(PPTX, str(tmp_path), "make a deck")
    assert calls["template"] == 0
    assert calls["freeform"] == [PPTX]


# --- template result handlers ----------------------------------------------

def test_template_completed_shows_file_and_clears_loaded(window):
    window._loaded_template = {"manifest": object(), "dir": "d", "name": "deck"}
    window._create_panel.set_template_loaded(True)
    window._generating = True
    window._on_template_completed("C:/out/deck.pptx", [])
    assert window._loaded_template is None
    assert window._generating is False
    assert window._create_panel._status_banner.isVisible()
    assert "File created successfully" in window._create_panel._status_banner.text()
    assert window._create_panel._open_file_btn.isVisible()
    assert window._create_panel._from_template_btn.text() != "From Template: selected"


def test_template_completed_notes_formatting_issues(window):
    window._loaded_template = {"manifest": object(), "dir": "d", "name": "deck"}
    window._generating = True
    window._on_template_completed("C:/out/deck.pptx", ["a", "b"])
    assert "2 formatting note" in window._create_panel._status_banner.text()


def test_template_failed_keeps_loaded(window):
    sentinel = {"manifest": object(), "dir": "d", "name": "deck"}
    window._loaded_template = sentinel
    window._generating = True
    window._on_template_failed("The AI engine stopped responding. Please check Ollama is running.")
    assert window._loaded_template is sentinel   # kept for retry
    assert window._generating is False
    assert window._create_panel._status_banner.isVisible()
    assert "Ollama" in window._create_panel._status_banner.text()


# --- end-to-end through the real worker + thread (pipeline mocked) ----------

def test_template_generate_end_to_end_clears_loaded(window, qtbot, tmp_path, monkeypatch):
    manifest = load_manifest(FIXTURE_MANIFEST)
    out = tmp_path / "deck.pptx"
    monkeypatch.setattr(
        "templates_engine.pipeline.run",
        MagicMock(return_value={"path": str(out), "issues": []}),
    )
    window._current_model = "llama3"
    window._loaded_template = {"manifest": manifest, "dir": str(tmp_path), "name": "deck"}
    window._create_panel.set_template_loaded(True)
    window._on_generate_requested(PPTX, str(tmp_path), "make a deck")
    qtbot.waitUntil(lambda: window._loaded_template is None, timeout=5000)
    assert window._create_panel._open_file_btn.isVisible()
    assert "From template" in window._create_panel._from_template_btn.text()
