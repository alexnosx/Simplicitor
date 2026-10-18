import os
import sys
# Use offscreen rendering so widget tests run without a display (CI, headless Windows)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Windows-specific: the offscreen platform reads fonts from QT_QPA_FONTDIR via
# FreeType. Without it, PDF text layers are empty in tests.
if sys.platform == "win32":
    os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))

import gc

import pytest
from PySide6.QtCore import Qt


@pytest.fixture(autouse=True)
def collect_garbage_on_main_thread():
    """Run Python's cyclic garbage collection only here, on the main thread, after each test.

    Automatic collection can start in any thread that allocates, including a worker
    QThread; destroying a leftover QObject there can deadlock Qt (hosted runs hung in
    MainWindow._on_candidate_ready on 2026-10-13).
    """
    gc.disable()
    yield
    gc.collect()


@pytest.fixture(autouse=True)
def auto_show_widgets(qtbot, monkeypatch):
    """Auto-show top-level widgets registered with qtbot unless they were explicitly hidden.

    Widgets that call hide() or setVisible(False) in their __init__ (e.g. CapabilityBanner)
    have WA_WState_ExplicitShowHide set to True and are left hidden so tests that check
    for an initially-hidden widget still pass.  Widgets that were simply never shown
    (panels, dialogs) are shown so that child-widget isVisible() checks work correctly.
    """
    from app import main_window
    from PySide6.QtWidgets import QDialog, QFileDialog

    def unexpected_dialog(*args, **kwargs):
        pytest.fail("A headless source test opened an unmocked dialog. "
                    "Supply an explicit simulated answer in that test.")

    monkeypatch.setattr(QDialog, "exec", unexpected_dialog)
    for name in ("getOpenFileName", "getOpenFileNames", "getSaveFileName",
                 "getExistingDirectory"):
        monkeypatch.setattr(QFileDialog, name, unexpected_dialog)

    original_client = main_window.OllamaClient

    def offline_discovery_client(*args, **kwargs):
        client = original_client(*args, **kwargs)
        client.check_connection = lambda: False
        client.get_model_params = lambda *a, **k: 0
        return client

    # UI unit tests drive discovery signals themselves. Keep their background
    # polling independent of an actual Ollama installation; client/worker tests
    # still exercise their own real methods and controlled responses.
    monkeypatch.setattr(main_window, "OllamaClient", offline_discovery_client)
    original_add = qtbot.addWidget

    def patched_add(widget, **kwargs):
        thread_names = (
            ("_ollama_thread", "_extraction_thread", "_generate_thread",
             "_template_thread", "_manipulate_thread", "_edit_thread")
            if hasattr(widget, "_close_when_idle") else ())
        if thread_names:
            prior_close = kwargs.pop("before_close_func", None)

            def close_and_wait(window):
                if prior_close is not None:
                    prior_close(window)
                window.close()
                qtbot.waitUntil(lambda: all(getattr(window, name, None) is None
                                            for name in thread_names), timeout=15000)
                window.close()

            # pytest-qt otherwise deletes the window even when closeEvent waits
            # for a live worker. Match the application's asynchronous close.
            kwargs["before_close_func"] = close_and_wait
        original_add(widget, **kwargs)
        explicit = widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide)
        if not explicit:
            widget.show()

    monkeypatch.setattr(qtbot, "addWidget", patched_add)
    yield


@pytest.fixture
def isolated_profile(tmp_path, monkeypatch):
    """Point every per-user folder at tmp_path before Settings or MainWindow exist."""
    home = tmp_path / "home"
    if sys.platform == "darwin":
        monkeypatch.setenv("HOME", str(home))
    for name, path in (("USERPROFILE", home), ("APPDATA", home / "AppData" / "Roaming"),
                       ("LOCALAPPDATA", home / "AppData" / "Local")):
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(name, str(path))
    from app.config.settings import Settings
    config = home / "AppData" / "Roaming" / "Simplicitor"
    config.mkdir(parents=True, exist_ok=True)
    settings = Settings(config)
    for folder in (settings.generated_dir, settings.templates_dir):
        assert str(folder).startswith(str(home))
    return settings
