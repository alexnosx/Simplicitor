# tests/test_widgets.py
# conftest.py sets QT_QPA_PLATFORM=offscreen for headless rendering
import pytest
from app.widgets.status_bar import TopBar


def test_top_bar_instantiates(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)


def test_top_bar_has_title(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    # The title label exists and displays the app name
    assert hasattr(bar, "_title_label")
    assert bar._title_label.text() == "Simplicitor"


def test_top_bar_settings_signal_emits(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.settings_requested, timeout=1000):
        bar._settings_btn.click()
