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


from app.widgets.create_panel import CreatePanel
from app.config.settings import Settings


def test_create_panel_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)


def test_create_panel_generate_button_disabled_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    assert not panel._generate_btn.isEnabled()


def test_create_panel_has_three_file_types(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    assert panel._type_combo.count() == 3


def test_create_panel_prompt_empty_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    assert panel._prompt_edit.toPlainText() == ""


def test_create_panel_emits_generate_requested(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    # Manually enable button to test signal emission (normally enabled by Ollama in Phase 2)
    panel._generate_btn.setEnabled(True)
    panel._prompt_edit.setPlainText("test prompt")
    with qtbot.waitSignal(panel.generate_requested, timeout=1000) as blocker:
        panel._generate_btn.click()
    assert blocker.args[2] == "test prompt"  # (file_type, save_path, prompt)
