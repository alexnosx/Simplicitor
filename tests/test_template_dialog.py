# tests/test_template_dialog.py
# Phase K Task 4a: TemplateDialog scaffold (SELECTION + CONFIRM).
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from pptx import Presentation

from app.widgets.template_dialog import TemplateDialog
from templates_engine import config

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)


@pytest.fixture
def template_root(tmp_path, monkeypatch):
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
    dlg = TemplateDialog(settings=settings)
    qtbot.addWidget(dlg)
    return dlg


def _select_deck(dlg):
    dlg._refresh_templates()
    dlg._template_list.setCurrentRow(0)
    dlg._on_select_next()


def test_selection_lists_user_template(dialog):
    names = [
        dialog._template_list.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(dialog._template_list.count())
    ]
    assert names == ["deck"]


def test_select_advances_to_confirm_and_loads_manifest(dialog):
    _select_deck(dialog)
    assert dialog._stack.currentWidget() is dialog._confirm_page
    assert dialog._manifest is not None
    assert dialog._manifest.name == "render_test"


def test_confirm_shows_manifest_summary(dialog):
    _select_deck(dialog)
    summary = dialog._confirm_summary.text()
    assert "title_slide" in summary
    assert "content_slide" in summary
    assert "title" in summary          # a field name from the manifest
    assert "*" in summary              # required-field marker


def test_generate_requested_emitted_with_manifest_and_request(qtbot, dialog):
    _select_deck(dialog)
    dialog._confirm_prompt.setPlainText("Make a deck")
    with qtbot.waitSignal(dialog.generate_requested, timeout=2000) as blocker:
        dialog._on_generate_clicked()
    assert blocker.args[0] is dialog._manifest
    assert blocker.args[1] == "Make a deck"


def test_empty_prompt_does_not_emit(qtbot, dialog):
    _select_deck(dialog)
    dialog._confirm_prompt.setPlainText("   ")
    emitted = []
    dialog.generate_requested.connect(lambda *a: emitted.append(a))
    dialog._on_generate_clicked()
    assert emitted == []
    assert dialog._confirm_status.isVisible()


def test_reject_blocked_while_generating(dialog):
    dialog._generating = True
    rejected = []
    dialog.rejected.connect(lambda: rejected.append(True))
    dialog.reject()
    assert rejected == []
    dialog._generating = False
    dialog.reject()
    assert rejected == [True]


def test_close_event_ignored_while_generating(dialog):
    dialog._generating = True
    ev = QCloseEvent()
    dialog.closeEvent(ev)
    assert not ev.isAccepted()

    dialog._generating = False
    ev2 = QCloseEvent()
    dialog.closeEvent(ev2)
    assert ev2.isAccepted()
