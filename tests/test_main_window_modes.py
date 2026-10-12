# tests/test_main_window_modes.py
import pytest


@pytest.fixture
def window(qtbot, isolated_profile):
    from app.main_window import MainWindow
    win = MainWindow(isolated_profile)
    qtbot.addWidget(win)
    return win


def test_two_modes_switch_and_return(window):
    from app.widgets.create_screen import CreateScreen
    from app.widgets.edit_placeholder import EditPlaceholder
    assert isinstance(window._modes.currentWidget(), CreateScreen)
    window._top_bar._edit_mode_btn.click()
    assert isinstance(window._modes.currentWidget(), EditPlaceholder)
    window._edit_page._create_btn.click()
    assert isinstance(window._modes.currentWidget(), CreateScreen) and window._top_bar.mode() == "create"


def test_generation_starts_exactly_one_request(window, monkeypatch):
    started = []
    monkeypatch.setattr(window, "_on_generate_requested", lambda *args: started.append(args))
    window._connect_create_screen()
    screen = window._create_screen
    screen.set_model("qwen3:8b")
    screen.set_ollama_connected(True)
    screen._prompt_edit.setPlainText("Summary")
    screen._primary_btn.click()
    assert len(started) == 1


def test_proposal_waits_for_inspection(window, tmp_path, monkeypatch):
    starts = []
    monkeypatch.setattr(window, "_start_extraction", lambda action, setup, **kw: starts.append(action))
    window._connect_create_screen()
    screen = window._create_screen
    screen.set_model("qwen3:8b")
    screen.set_ollama_connected(True)
    screen._prompt_edit.setPlainText("Invoice number")
    source = tmp_path / "invoice.docx"
    source.write_bytes(b"x")
    screen.set_paths((source,))
    assert starts == ["inspect"]
    assert not screen._primary_btn.isEnabled()
    screen.show_inspection(())
    screen._primary_btn.click()
    assert starts == ["inspect", "propose"]


def test_busy_blocks_mode_switch(window):
    window._create_screen.set_busy(True)
    assert not window._top_bar._edit_mode_btn.isEnabled()
    assert not window._top_bar._settings_btn.isEnabled()
    window._show_mode("edit")
    assert window._modes.currentWidget() is window._create_screen
    window._create_screen.set_busy(False)
    assert window._top_bar._edit_mode_btn.isEnabled()
    assert window._top_bar._settings_btn.isEnabled()


def test_step_labels_fit_at_screenshot_size(window, qapp, tmp_path, monkeypatch):
    from docx import Document
    from PySide6.QtGui import QFont
    from app.config.defaults import APP_FONT_FAMILY, FONT_SIZE_BODY_PT

    original_font = qapp.font()
    try:
        qapp.setFont(QFont(APP_FONT_FAMILY, FONT_SIZE_BODY_PT))
        window.resize(1280, 800)
        source = tmp_path / "source.docx"
        Document().save(source)
        monkeypatch.setattr(window, "_start_extraction", lambda *a, **kw: None)
        window._create_screen.set_paths((source,))
        steps = window._create_screen._steps
        steps.set_steps(["Describe", "Choose columns", "Review and save"])
        for index in range(3):
            steps.set_current(index)
            qapp.processEvents()
            label = steps._labels[index]
            assert label.width() >= label.fontMetrics().horizontalAdvance(label.text()) + 4
    finally:
        qapp.setFont(original_font)


def test_idle_cancel_is_a_compact_button(window):
    assert window._create_screen._cancel_btn.width() < 200


@pytest.mark.parametrize("mode", ["create", "edit"])
def test_mode_text_has_room_for_button_padding(window, qapp, mode):
    window._show_mode(mode)
    qapp.processEvents()
    button = (window._top_bar._edit_mode_btn if mode == "edit"
              else window._top_bar._create_mode_btn)
    assert button.width() >= button.fontMetrics().horizontalAdvance(button.text()) + 24


@pytest.mark.parametrize("accepted", [True, False])
def test_settings_changes_model_only_on_save(window, monkeypatch, accepted):
    from PySide6.QtWidgets import QDialog
    import app.main_window as main_window

    window._on_ollama_connected(["qwen3:8b", "llama3.1:8b"], "qwen3:8b")

    class Dialog:
        def __init__(self, settings, parent, models, current_model):
            assert models == ["qwen3:8b", "llama3.1:8b"]
            assert current_model == "qwen3:8b"

        def exec(self):
            return QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected

        def selected_model(self):
            return "llama3.1:8b"

    monkeypatch.setattr(main_window, "SettingsDialog", Dialog)
    window._open_settings()
    expected = "llama3.1:8b" if accepted else "qwen3:8b"
    assert window._current_model == expected
    assert window._create_screen._model == expected


@pytest.mark.parametrize("cancel", [False, True])
def test_pending_extract_survives_the_inspection_thread(window, monkeypatch, tmp_path, cancel):
    from PySide6.QtCore import QObject, Signal, Slot
    from extraction.models import ColumnSpec, SourceDocument, SourceUnit
    import app.main_window as main_window
    source = tmp_path / "invoice.docx"
    source.write_bytes(b"x")
    document = SourceDocument("source-1", source.resolve(), source.name,
                              (SourceUnit("source-1#p:0", "Invoice number: 1", "paragraph", 0, "source-1#p:0"),), 1, ())
    actions = []

    class FakeWorker(QObject):
        progress = Signal(str)
        inspection_ready = Signal(object)
        columns_ready = Signal(object)
        candidate_ready = Signal(object, object)
        saved = Signal(str)
        failed = Signal(str, object)
        cancelled = Signal()
        finished = Signal()

        def __init__(self, action, setup, client, **kwargs):
            super().__init__()
            self.action = action
            actions.append(action)

        def cancel(self):
            pass

        @Slot()
        def run(self):
            if self.action == "inspect":
                self.inspection_ready.emit((document,))
            self.finished.emit()

    monkeypatch.setattr(main_window, "ExtractionWorker", FakeWorker)
    screen = window._create_screen
    screen.set_model("qwen3:8b")
    screen.set_ollama_connected(True)
    screen._prompt_edit.setPlainText("Invoice number")
    # Simulate an inspection failure before manual column entry. Confirmation
    # requests a fresh real inspection, then resumes only after its thread clears.
    start_extraction = window._start_extraction
    monkeypatch.setattr(window, "_start_extraction", lambda *a, **kw: None)
    screen.set_paths((source,))
    screen.inspection_finished()
    screen.set_columns((ColumnSpec("c1", "Invoice number", "The invoice number", "text"),))
    monkeypatch.setattr(window, "_start_extraction", start_extraction)
    screen._extract_btn.click()
    if cancel:
        screen._cancel_btn.click()
        assert not screen._cancel_btn.isEnabled()
    from PySide6.QtTest import QTest
    for _ in range(100):
        if window._extraction_thread is None:
            break
        QTest.qWait(50)
    assert actions[0] == "inspect" and actions.count("extract") == (0 if cancel else 1)

