"""Edit wiring uses workers, rejects stale replies and preserves the accepted-save boundary."""
import json
from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog

from editing import reading_view, save
from tests.test_edit_screen import candidate_for, make_opened


@pytest.fixture
def window(qtbot, isolated_profile, tmp_path):
    from app.main_window import MainWindow
    win = MainWindow(isolated_profile)
    # This fixture drives discovery explicitly; the global offline poll must not
    # clear the synthetic model during an edit-request test.
    win._ollama_worker.disconnected.disconnect(win._on_ollama_disconnected)
    qtbot.addWidget(win)
    win._show_mode("edit")
    opened = make_opened(tmp_path)
    win._edit_page.show_opened(opened, reading_view.build(opened))
    win._on_ollama_connected(["synthetic:8b"], "synthetic:8b")
    return win


def test_propose_sends_selection_description_attempt_and_styles(window, qtbot):
    calls = []

    class Client:
        def generate(self, model, prompt, system, **kwargs):
            calls.append((model, json.loads(prompt), kwargs))
            return json.dumps({"paragraphs": ["Invoices are payable within 45 days of receipt."]})

    window._ollama_client = Client()
    page = window._edit_page
    page.select_paragraph(1)
    assert page._selection == (1, 1)
    assert page._edit_part_btn.isEnabled()
    page._edit_part_btn.click()
    page._description.setPlainText("Change 30 days to 45 days.")
    page._attempt = 2
    assert page._propose_btn.isEnabled(), (page._model_ready, page._busy, window._current_model)
    page._propose_btn.click()
    setup = window._edit_worker.setup
    assert (setup.first, setup.last, setup.instruction, setup.attempt) == (1, 1, "Change 30 days to 45 days.", 2)
    assert setup.styles == {b.index: b.style for b in page._view if b.kind == "paragraph"}
    qtbot.waitUntil(lambda: window._edit_thread is None, timeout=5000)
    assert page._candidate is not None and calls[0][0] == "synthetic:8b"
    assert "instruction" in calls[0][1]


def test_save_starts_the_worker_without_reading_the_destination(window, qtbot, monkeypatch, tmp_path, qapp):
    page = window._edit_page
    page.show_proposal(*candidate_for(page._opened))
    page._use_btn.click()
    candidate = page._candidate
    observed = []

    def unreadable(path):
        observed.append(QThread.currentThread() == qapp.thread())
        raise OSError("synthetic destination read failure")

    monkeypatch.setattr(save, "destination_state", unreadable)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: ("", ""))
    window._on_edit_save_requested(tmp_path / "copy.docx")
    qtbot.waitUntil(lambda: window._edit_thread is None, timeout=5000)
    assert observed == [False]
    assert page._candidate is candidate and page._pages.currentWidget() is page._save_page
    assert "cannot be read" in page._error.text()


@pytest.mark.parametrize("outcome", ["retry", "destination"])
def test_retry_and_destination_reopen_save_as_after_worker_settles(window, qtbot, monkeypatch, outcome):
    page = window._edit_page
    page.show_proposal(*candidate_for(page._opened))
    page._use_btn.click()
    picks = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **kw: (picks.append(window._edit_thread) or "", ""))
    window._on_edit_failed("Choose where to save again.", outcome)
    qtbot.waitUntil(lambda: len(picks) == 1, timeout=1000)
    assert picks == [None] and page._candidate is not None


def test_switching_to_create_with_work_asks_first(window, monkeypatch):
    page = window._edit_page
    page.select_paragraph(1)
    monkeypatch.setattr(page, "confirm_discard", lambda: False)
    window._top_bar._create_mode_btn.click()
    assert window._modes.currentWidget() is page and window._top_bar.mode() == "edit"
    monkeypatch.setattr(page, "confirm_discard", lambda: True)
    window._top_bar._create_mode_btn.click()
    assert window._modes.currentWidget() is window._create_screen and not page.has_work()
    assert page._opened is None


def test_busy_disables_modes_settings_and_choose_another_file(window):
    page = window._edit_page
    page.set_busy(True)
    for button in (window._top_bar._create_mode_btn, window._top_bar._edit_mode_btn,
                   window._top_bar._settings_btn, page._choose_btn):
        assert not button.isEnabled()
    window._show_mode("create")
    assert window._modes.currentWidget() is page
    page.set_busy(False)
    assert window._top_bar._settings_btn.isEnabled()


def test_late_proposal_after_cancel_is_ignored(window):
    page = window._edit_page
    page.select_paragraph(1)
    epoch = window._edit_epoch
    window._cancel_edit()
    window._on_edit_proposed(*candidate_for(page._opened), epoch=epoch)
    assert page._candidate is None


def test_late_result_after_opening_another_document_is_ignored(window, tmp_path, monkeypatch, qtbot):
    page = window._edit_page
    old_epoch = window._edit_epoch
    old = page._opened
    new = make_opened(tmp_path, "another.docx")
    page.choose_path(new.path)
    qtbot.waitUntil(lambda: window._edit_thread is None, timeout=5000)
    window._on_edit_opened(old, reading_view.build(old), epoch=old_epoch)
    assert page._opened.path == new.path


def test_late_result_after_switching_to_create_is_ignored(window, monkeypatch):
    page = window._edit_page
    candidate = candidate_for(page._opened)
    old_epoch = window._edit_epoch
    window._show_mode("create")
    window._on_edit_proposed(*candidate, epoch=old_epoch)
    assert page._candidate is None and window._modes.currentWidget() is window._create_screen


def test_close_waits_for_an_accepted_save(window, qtbot, tmp_path, monkeypatch):
    import app.workers.edit_worker as workers
    entered, release = Event(), Event()
    page = window._edit_page
    page.show_proposal(*candidate_for(page._opened))
    page._use_btn.click()

    def held_save(candidate, destination):
        entered.set()
        assert release.wait(5)
        return destination

    monkeypatch.setattr(workers, "save_candidate", held_save)
    window._on_edit_save_requested(tmp_path / "copy.docx")
    qtbot.waitUntil(entered.is_set, timeout=3000)
    event = QCloseEvent()
    try:
        window.closeEvent(event)
        assert not event.isAccepted() and window._edit_thread is not None
        assert not window._edit_worker._cancel.is_set()
    finally:
        release.set()
    qtbot.waitUntil(lambda: window._edit_thread is None, timeout=5000)
