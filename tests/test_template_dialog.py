# tests/test_template_dialog.py
# TemplateDialog is a picker of built-in templates: SELECTION + CONFIRM, emits
# template_selected on "Next".
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton
from pptx import Presentation

from app.widgets.template_dialog import TemplateDialog
from templates_engine import config

FIXTURE_MANIFEST = (
    Path(__file__).parent / "templates_engine" / "fixtures" / "render_manifest.yaml"
)


def _write_template(root: Path, name: str) -> None:
    tdir = root / name
    tdir.mkdir(parents=True)
    Presentation().save(str(tdir / "template.pptx"))
    (tdir / "manifest.yaml").write_bytes(FIXTURE_MANIFEST.read_bytes())


@pytest.fixture
def template_root(tmp_path, monkeypatch):
    """One built-in template and one template a user imported before 2.2.0."""
    root = tmp_path / "library"
    _write_template(root, "business_pitch")
    _write_template(root, "my_upload")
    empty_builtin = tmp_path / "builtin_empty"
    empty_builtin.mkdir()
    monkeypatch.setattr(config, "get_builtin_root", lambda: empty_builtin)
    return root


@pytest.fixture
def dialog(qtbot, template_root):
    dlg = TemplateDialog(templates_dir=str(template_root))
    qtbot.addWidget(dlg)
    return dlg


def _select_deck(dlg):
    dlg._refresh_templates()
    dlg._template_list.setCurrentRow(0)
    dlg._on_select_next()


# --- selection + confirm ---------------------------------------------------

def test_selection_lists_only_built_in_templates(dialog, template_root):
    names = [
        dialog._template_list.item(i).data(Qt.ItemDataRole.UserRole)
        for i in range(dialog._template_list.count())
    ]
    assert names == ["business_pitch"]
    assert dialog._template_list.item(0).text() == "business_pitch"
    assert (template_root / "my_upload" / "template.pptx").exists()  # left on disk


def test_selection_offers_no_upload(dialog):
    labels = [button.text() for button in dialog.findChildren(QPushButton)]
    assert not any("upload" in label.lower() for label in labels)
    assert not hasattr(dialog, "_on_upload")


def test_empty_picker_names_the_missing_built_ins(qtbot, tmp_path):
    _write_template(tmp_path / "library", "my_upload")
    dlg = TemplateDialog(templates_dir=str(tmp_path / "library"))
    qtbot.addWidget(dlg)
    assert dlg._template_list.count() == 0
    assert not dlg._sel_empty.isHidden()
    assert dlg._sel_empty.text() == "No built-in templates found."


def test_next_without_a_selection_asks_for_one(dialog):
    dialog._template_list.setCurrentRow(-1)
    dialog._on_select_next()
    assert dialog._stack.currentWidget() is dialog._selection_page
    assert not dialog._sel_error.isHidden()
    assert dialog._sel_error.text() == "Select a template."


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


def test_confirm_page_has_no_prompt_box(dialog):
    """The second prompt was removed; the main Create prompt is the only one."""
    assert not hasattr(dialog, "_confirm_prompt")


def test_confirm_next_emits_template_selected_and_accepts(qtbot, dialog):
    _select_deck(dialog)
    accepted = []
    dialog.accepted.connect(lambda: accepted.append(True))
    with qtbot.waitSignal(dialog.template_selected, timeout=2000) as blocker:
        dialog._confirm_next_btn.click()
    assert blocker.args[0] is dialog._manifest
    assert blocker.args[1] == dialog._template_dir
    assert blocker.args[2] == "business_pitch"
    assert accepted == [True]


def test_confirm_next_noop_without_selection(qtbot, dialog):
    emitted = []
    dialog.template_selected.connect(lambda *a: emitted.append(a))
    dialog._on_confirm_next()  # no template selected yet
    assert emitted == []


def test_headless_dialog_without_an_explicit_answer_fails(qtbot):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog

    popup = QDialog()
    qtbot.addWidget(popup)
    QTimer.singleShot(20, popup.reject)  # Bounded RED: never wait for a person.
    with pytest.raises(pytest.fail.Exception, match="unmocked dialog"):
        popup.exec()
