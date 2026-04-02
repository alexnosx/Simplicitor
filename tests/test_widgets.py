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


from app.widgets.edit_panel import EditPanel


def test_edit_panel_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)


def test_edit_panel_save_button_disabled_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert not panel._save_btn.isEnabled()


def test_edit_panel_prompt_empty_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert panel._prompt_edit.toPlainText() == ""


def test_edit_panel_file_list_empty_by_default(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert panel._file_list.count() == 0


from app.widgets.settings_dialog import SettingsDialog


def test_settings_dialog_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)


def test_settings_dialog_shows_current_paths(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    settings.set("generated_dir", "/my/generated")
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)
    assert dialog._generated_edit.text() == "/my/generated"


def test_settings_dialog_save_updates_settings(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    dialog = SettingsDialog(settings)
    qtbot.addWidget(dialog)
    dialog._generated_edit.setText("/new/path")
    dialog._on_save()
    assert settings.generated_dir == "/new/path"
