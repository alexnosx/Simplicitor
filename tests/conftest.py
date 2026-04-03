import os
# Use offscreen rendering so widget tests run without a display (CI, headless Windows)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt


@pytest.fixture(autouse=True)
def auto_show_widgets(qtbot, monkeypatch):
    """Auto-show top-level widgets registered with qtbot unless they were explicitly hidden.

    Widgets that call hide() or setVisible(False) in their __init__ (e.g. CapabilityBanner)
    have WA_WState_ExplicitShowHide set to True and are left hidden so tests that check
    for an initially-hidden widget still pass.  Widgets that were simply never shown
    (panels, dialogs) are shown so that child-widget isVisible() checks work correctly.
    """
    original_add = qtbot.addWidget

    def patched_add(widget, **kwargs):
        original_add(widget, **kwargs)
        explicit = widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide)
        if not explicit:
            widget.show()

    monkeypatch.setattr(qtbot, "addWidget", patched_add)
    yield
