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
    assert hasattr(bar, "_title_label")
    assert bar._title_label.text() == "Simplicitor"


def test_top_bar_starts_disconnected(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    assert bar.current_model() == ""
    assert not bar._model_combo.isEnabled()


def test_top_bar_set_connected_populates_models(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.set_connected(["llama3:8b", "mistral:7b"], "llama3:8b")
    assert bar.current_model() == "llama3:8b"
    assert bar._model_combo.isEnabled()
    assert bar._model_combo.count() == 2


def test_top_bar_set_disconnected_clears_models(qtbot) -> None:
    bar = TopBar()
    qtbot.addWidget(bar)
    bar.set_connected(["llama3:8b"], "llama3:8b")
    bar.set_disconnected()
    assert bar.current_model() == ""
    assert not bar._model_combo.isEnabled()


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


from app.main_window import MainWindow


def test_main_window_instantiates(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)


def test_main_window_title_is_simplicitor(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert window.windowTitle() == "Simplicitor"


def test_main_window_minimum_size(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert window.minimumWidth() >= 1024
    assert window.minimumHeight() >= 640


def test_main_window_opens_settings_dialog(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    # Verify the signal is connected (settings_requested → _open_settings)
    assert window._top_bar.settings_requested is not None


def test_main_window_creates_ollama_thread(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert hasattr(window, "_ollama_thread")
    assert hasattr(window, "_ollama_worker")
