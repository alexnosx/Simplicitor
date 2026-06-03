# tests/test_hard_stop_dialog.py
# Phase K: Tests for HardStopDialog.
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from app.widgets.hard_stop_dialog import HardStopDialog, CHOICE_BUILTIN, CHOICE_CANCEL
from templates_engine.breakdown import hard_stop_result


def test_hard_stop_renders_verbatim_message(qtbot):
    msg = hard_stop_result()["message"]
    dlg = HardStopDialog(msg, builtin_available=True)
    qtbot.addWidget(dlg)
    labels = [w.text() for w in dlg.findChildren(QLabel)]
    assert any(msg in t for t in labels), "verbatim hard-stop message must render"


@pytest.mark.parametrize("builtin_list, expect_builtin_btn", [
    ([], False),
    ([{"name": "corporate", "source": "builtin"}], True),
])
def test_hard_stop_gates_builtin_button_on_builtin_list(qtbot, builtin_list, expect_builtin_btn):
    # The caller derives availability from the built-in template list; inject both states.
    dlg = HardStopDialog("reason", builtin_available=bool(builtin_list))
    qtbot.addWidget(dlg)
    assert dlg.has_builtin_button() is expect_builtin_btn
    if not expect_builtin_btn:
        assert not hasattr(dlg, "_builtin_btn")


def test_hard_stop_builtin_button_returns_builtin_choice(qtbot):
    dlg = HardStopDialog("reason", builtin_available=True)
    qtbot.addWidget(dlg)
    qtbot.mouseClick(dlg._builtin_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_BUILTIN


def test_hard_stop_cancel_button_returns_cancel_choice(qtbot):
    dlg = HardStopDialog("reason", builtin_available=True)
    qtbot.addWidget(dlg)
    qtbot.mouseClick(dlg._cancel_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_CANCEL


def test_hard_stop_cancel_only_when_no_builtin(qtbot):
    dlg = HardStopDialog("reason", builtin_available=False)
    qtbot.addWidget(dlg)
    assert dlg.has_builtin_button() is False
    qtbot.mouseClick(dlg._cancel_btn, Qt.MouseButton.LeftButton)
    assert dlg.choice() == CHOICE_CANCEL
