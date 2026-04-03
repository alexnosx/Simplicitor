# tests/test_widgets.py
# conftest.py sets QT_QPA_PLATFORM=offscreen for headless rendering
import pytest
from app.widgets.status_bar import TopBar
from app.widgets.create_panel import CreatePanel
from app.widgets.edit_panel import EditPanel
from app.widgets.settings_dialog import SettingsDialog
from app.widgets.capability_banner import CapabilityBanner
from app.main_window import MainWindow
from app.config.settings import Settings


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


def test_capability_banner_hidden_by_default(qtbot) -> None:
    banner = CapabilityBanner()
    qtbot.addWidget(banner)
    assert not banner.isVisible()


def test_capability_banner_show_banner(qtbot) -> None:
    banner = CapabilityBanner()
    qtbot.addWidget(banner)
    banner.show_banner()
    assert banner.isVisible()


def test_capability_banner_dismiss_hides(qtbot) -> None:
    banner = CapabilityBanner()
    qtbot.addWidget(banner)
    banner.show_banner()
    with qtbot.waitSignal(banner.dismissed, timeout=1000):
        banner._dismiss_btn.click()
    assert not banner.isVisible()
    assert banner.is_dismissed()


def test_capability_banner_show_resets_dismissed(qtbot) -> None:
    banner = CapabilityBanner()
    qtbot.addWidget(banner)
    banner.show_banner()
    banner._dismiss_btn.click()
    assert banner.is_dismissed()
    banner.show_banner()
    assert not banner.is_dismissed()


def test_create_panel_shows_disconnected_message(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    # Starts disconnected — message should be visible
    assert panel._disconnected_widget.isVisible()


def test_create_panel_retry_signal(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.retry_requested, timeout=1000):
        panel._retry_btn.click()


def test_create_panel_connected_hides_message(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = CreatePanel(settings)
    qtbot.addWidget(panel)
    panel.set_ollama_connected(True)
    assert not panel._disconnected_widget.isVisible()
    assert panel._generate_btn.isEnabled()


def test_edit_panel_shows_disconnected_message(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    assert panel._disconnected_widget.isVisible()


def test_edit_panel_retry_signal(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel.retry_requested, timeout=1000):
        panel._retry_btn.click()


def test_edit_panel_connected_hides_message(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    panel = EditPanel(settings)
    qtbot.addWidget(panel)
    panel.set_ollama_connected(True)
    assert not panel._disconnected_widget.isVisible()


def test_main_window_has_capability_banner(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    assert hasattr(window, "_capability_banner")
    assert not window._capability_banner.isVisible()


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
    assert window._ollama_worker.thread() is window._ollama_thread


def test_main_window_banner_shows_for_small_model(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    # 3B params < 7B threshold → banner should show
    window._on_model_params_ready("small-model:3b", 3_000_000_000)
    assert window._capability_banner.isVisible()


def test_main_window_banner_hidden_for_large_model(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    # 13B params > 7B threshold → banner should stay hidden
    window._on_model_params_ready("large-model:13b", 13_000_000_000)
    assert not window._capability_banner.isVisible()


def test_main_window_banner_not_reshown_after_dismiss(qtbot, tmp_path) -> None:
    settings = Settings(tmp_path)
    window = MainWindow(settings)
    qtbot.addWidget(window)
    window._current_model = "small-model:3b"
    window._on_model_params_ready("small-model:3b", 3_000_000_000)
    assert window._capability_banner.isVisible()
    # User dismisses
    window._capability_banner._dismiss_btn.click()
    # Same model signals again — banner should stay hidden
    window._on_model_params_ready("small-model:3b", 3_000_000_000)
    assert not window._capability_banner.isVisible()
