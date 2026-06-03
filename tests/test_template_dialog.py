# tests/test_template_dialog.py
# Phase K Task 4a: TemplateDialog scaffold (SELECTION + CONFIRM).
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from pptx import Presentation

from app.services.file_manipulator import ManipulationError
from app.widgets.hard_stop_dialog import CHOICE_BUILTIN, CHOICE_CANCEL
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


# --- 4b: upload + import + hard-stop routing ------------------------------

def test_on_upload_calls_do_import_with_chosen_path(dialog, monkeypatch):
    monkeypatch.setattr(
        "app.widgets.template_dialog.QFileDialog.getOpenFileName",
        lambda *a, **k: ("/picked/file.pptx", "PowerPoint files (*.pptx)"),
    )
    called = {}
    monkeypatch.setattr(dialog, "_do_import", lambda p: called.setdefault("path", p))
    dialog._on_upload()
    assert called["path"] == "/picked/file.pptx"


def test_on_upload_cancelled_does_nothing(dialog, monkeypatch):
    monkeypatch.setattr(
        "app.widgets.template_dialog.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )
    called = {}
    monkeypatch.setattr(dialog, "_do_import", lambda p: called.setdefault("path", p))
    dialog._on_upload()
    assert called == {}


def test_import_bad_file_stays_selection_with_message(dialog, monkeypatch):
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(side_effect=ValueError("corrupt zip internal /secret/path")),
    )
    dialog._do_import("bad.pptx")
    assert dialog._stack.currentWidget() is dialog._selection_page
    assert dialog._sel_error.isVisible()
    assert "not a usable PowerPoint" in dialog._sel_error.text()
    assert "secret" not in dialog._sel_error.text()


def test_import_manipulation_error_stays_selection(dialog, monkeypatch):
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(side_effect=ManipulationError("disk full /secret/path")),
    )
    dialog._do_import("x.pptx")
    assert dialog._stack.currentWidget() is dialog._selection_page
    assert "Could not save" in dialog._sel_error.text()
    assert "secret" not in dialog._sel_error.text()


def test_import_exists_shows_message_stays_selection(dialog, monkeypatch):
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(return_value={"status": "exists", "name": "deck"}),
    )
    dialog._do_import("x.pptx")
    assert dialog._stack.currentWidget() is dialog._selection_page
    assert "already exists" in dialog._sel_error.text()
    assert "deck" in dialog._sel_error.text()


def test_import_ok_advances_to_confirm_with_report(dialog, template_root, monkeypatch):
    # Second valid template on disk so refresh/select find it after the mocked import.
    second = template_root / "newdeck"
    second.mkdir()
    Presentation().save(str(second / "template.pptx"))
    (second / "manifest.yaml").write_bytes(FIXTURE_MANIFEST.read_bytes())
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(return_value={
            "status": "ok", "name": "newdeck",
            "report": "DETECTION-REPORT", "lint_warnings": [],
        }),
    )
    dialog._do_import("x.pptx")
    assert dialog._stack.currentWidget() is dialog._confirm_page
    assert dialog._confirm_report.isVisible()
    assert dialog._confirm_report.text() == "DETECTION-REPORT"
    names = [
        dialog._template_list.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(dialog._template_list.count())
    ]
    assert "newdeck" in names


def test_import_hard_stop_invokes_prompt_and_routes(dialog, monkeypatch):
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(return_value={"status": "hard_stop", "message": "NOPE-DECK"}),
    )
    seen = {}
    monkeypatch.setattr(dialog, "_prompt_hard_stop",
                        lambda msg: seen.update({"msg": msg}) or CHOICE_CANCEL)
    monkeypatch.setattr(dialog, "_apply_hard_stop_choice",
                        lambda c: seen.setdefault("choice", c))
    dialog._do_import("x.pptx")
    assert seen["msg"] == "NOPE-DECK"
    assert seen["choice"] == CHOICE_CANCEL


def test_apply_hard_stop_cancel_rejects(dialog, monkeypatch):
    rejected = []
    monkeypatch.setattr(dialog, "reject", lambda: rejected.append(True))
    dialog._apply_hard_stop_choice(CHOICE_CANCEL)
    assert rejected == [True]


def test_apply_hard_stop_builtin_returns_to_selection_with_focus(dialog):
    from PySide6.QtWidgets import QListWidgetItem
    dialog._templates = dialog._templates + [
        {"name": "corp", "source": "builtin", "path": "x",
         "manifest_path": "x", "template_pptx": "x"}
    ]
    item = QListWidgetItem("corp  (builtin)")
    item.setData(Qt.ItemDataRole.UserRole, "corp")
    dialog._template_list.addItem(item)
    dialog._stack.setCurrentWidget(dialog._confirm_page)
    dialog._apply_hard_stop_choice(CHOICE_BUILTIN)
    assert dialog._stack.currentWidget() is dialog._selection_page
    cur = dialog._template_list.currentItem()
    assert cur is not None and cur.data(Qt.ItemDataRole.UserRole) == "corp"


def test_prompt_hard_stop_builtin_available_reflects_templates(dialog, monkeypatch):
    captured = {}

    class FakeHS:
        def __init__(self, message, builtin_available, parent=None):
            captured["ba"] = builtin_available

        def exec(self):
            return 0

        def choice(self):
            return CHOICE_CANCEL

    monkeypatch.setattr("app.widgets.template_dialog.HardStopDialog", FakeHS)
    dialog._refresh_templates()  # only a user template => no built-ins
    dialog._prompt_hard_stop("m")
    assert captured["ba"] is False
    dialog._templates = dialog._templates + [{"name": "corp", "source": "builtin"}]
    dialog._prompt_hard_stop("m")
    assert captured["ba"] is True


def test_import_unexpected_status_shows_error_stays_selection(dialog, monkeypatch):
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(return_value={"status": "wat"}),
    )
    dialog._do_import("x.pptx")
    assert dialog._stack.currentWidget() is dialog._selection_page
    assert "Unexpected error" in dialog._sel_error.text()


def test_do_import_hard_stop_cancel_end_to_end(dialog, monkeypatch):
    # Exercises the real _prompt_hard_stop -> _apply_hard_stop_choice chain;
    # only HardStopDialog (modal) and reject are stubbed.
    monkeypatch.setattr(
        config, "import_template",
        MagicMock(return_value={"status": "hard_stop", "message": "NOPE"}),
    )

    class FakeHS:
        def __init__(self, message, builtin_available, parent=None):
            self._message = message

        def exec(self):
            return 0

        def choice(self):
            return CHOICE_CANCEL

    monkeypatch.setattr("app.widgets.template_dialog.HardStopDialog", FakeHS)
    rejected = []
    monkeypatch.setattr(dialog, "reject", lambda: rejected.append(True))
    dialog._do_import("x.pptx")
    assert rejected == [True]
