"""Per-attachment reading state and worker progress reach the visible actions."""
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import QLabel, QProgressBar

from tests.test_create_screen import _screen, _document
from tests.test_main_window_extraction import window, configure_window, ExtractionClient
from tests.test_extraction_worker import setup, Client
from app.workers.extraction_worker import ExtractionWorker
from extraction.jobs import create_job
from extraction.models import Issue


def row_labels(screen, index, view=None):
    view = view or screen._source_list
    holder = view.itemWidget(view.item(index))
    return [label.text() for label in holder.findChildren(QLabel)]


def test_rows_reading_ready_and_partly_read_are_per_attachment(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    source = Path("same-name.docx")
    screen.set_paths((source, source))
    assert all("Reading" in row_labels(screen, i) for i in range(2))
    assert screen._primary_btn.text() == "Reading files..."
    first = _document(source)
    second = replace(first, source_id="source-2", issues=(
        Issue("skipped_text_box", "source-2", "source-2#", "unread"),))
    screen.show_inspection((first, second))
    assert "Ready" in row_labels(screen, 0)
    assert "Partly read" in row_labels(screen, 1)
    assert "Partly read" not in row_labels(screen, 0)
    assert "text in text boxes was not read" in screen._source_coverage.toPlainText()


def test_worker_forwards_pipeline_source_identity_and_counts(setup, tmp_path, qtbot):
    worker = ExtractionWorker("extract", setup, Client(), job_dir=create_job(tmp_path))
    with qtbot.waitSignal(worker.source_progress) as progress:
        worker.run()
    assert progress.args == ["source-1", 1, 1]


def test_progress_reaches_rows_and_main_button_during_real_worker_run(
        window, tmp_path, qtbot):
    panel, _ = configure_window(window, tmp_path, qtbot)
    client = ExtractionClient(pause=True)
    window._ollama_client = client
    received = []
    original = panel.show_source_progress
    panel.show_source_progress = lambda *args: (received.append(args), original(*args))
    panel._extract_btn.click()
    try:
        qtbot.waitUntil(client.entered.is_set)
        assert panel._file_progress_box.isVisible()
        assert panel._extract_btn.text().startswith("Extracting...")
        holder = panel._working_files.itemWidget(panel._working_files.item(0))
        assert any(bar.isVisible() for bar in holder.findChildren(QProgressBar))
        assert any("Extracting" in text for text in row_labels(panel, 0, panel._working_files))
    finally:
        client.release.set()
        qtbot.waitUntil(lambda: window._extraction_thread is None)
    assert received == [("source-1", 1, 1)]
    assert not panel._file_progress_box.isVisible()
    assert panel._extract_btn.text() == "Extract to Excel"


def test_proposal_and_save_show_busy_action_without_changing_gates(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    screen.set_busy(True)
    screen.show_progress("Suggesting columns from the first source...")
    assert screen._primary_btn.text() == "Suggesting columns..."
    assert not screen._primary_btn.isEnabled()
    screen.set_busy(True, saving=True)
    screen.show_progress("Saving workbook...")
    assert screen._save_btn.text() == "Saving..."
    assert not screen._save_btn.isEnabled()
    screen.set_busy(False)
    assert screen._primary_btn.text() == "Next: choose columns"
    assert screen._save_btn.text() == "Save to Excel"


def test_late_source_progress_is_ignored_on_write(window):
    window._on_source_progress("source-1", 1, 2)
    assert window._create_screen._progress_counts is None


def test_progress_uses_source_ids_not_duplicate_names(qtbot, isolated_profile, qapp):
    from PySide6.QtCore import QPoint
    from extraction.models import SourceUnit
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    path = Path("same-name.docx")
    screen.set_paths((path, path))
    first = _document(path)
    second = replace(first, source_id="source-2", units=tuple(
        SourceUnit(f"source-2#p:{i}", "Synthetic text", "paragraph", i, f"source-2#p:{i}")
        for i in range(3)))
    screen.show_inspection((first, second))
    screen.set_busy(True, action="extract")
    screen.show_source_progress("source-1", 1, 4)
    screen.show_source_progress("source-2", 2, 4)
    assert "Processed 1 source units" in row_labels(screen, 0, screen._working_files)
    assert "Extracting... 1 / 3 source units" in row_labels(screen, 1, screen._working_files)
    assert screen._extract_btn.text() == "Extracting... 2 / 4"
    screen.resize(1240, 660)
    screen._pages.setCurrentWidget(screen._columns_page)
    qapp.processEvents()
    holder = screen._working_files.itemWidget(screen._working_files.item(1))
    bar = holder.findChild(QProgressBar)
    def active_row_is_visible():
        y = bar.mapTo(screen._working_files.viewport(), QPoint(0, 0)).y()
        return 0 <= y and y + bar.height() <= screen._working_files.viewport().height()
    qtbot.waitUntil(active_row_is_visible, timeout=1000)
