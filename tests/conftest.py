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
    from app import main_window

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
        if hasattr(widget, "_close_when_idle"):
            prior_close = kwargs.pop("before_close_func", None)

            def close_and_wait(window):
                if prior_close is not None:
                    prior_close(window)
                window.close()
                qtbot.waitUntil(lambda: all(getattr(window, name, None) is None for name in (
                    "_ollama_thread", "_extraction_thread", "_generate_thread",
                    "_template_thread", "_manipulate_thread")), timeout=15000)

            # pytest-qt otherwise deletes the window even when closeEvent waits
            # for a live worker. Match the application's asynchronous close.
            kwargs["before_close_func"] = close_and_wait
        original_add(widget, **kwargs)
        explicit = widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide)
        if not explicit:
            widget.show()

    monkeypatch.setattr(qtbot, "addWidget", patched_add)
    yield
