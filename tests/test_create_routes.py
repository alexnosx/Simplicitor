"""The chosen Create option owns its inputs and the work request, not visibility alone."""
from pathlib import Path

import pytest

from tests.test_create_screen import _screen, _document, saved_candidate
from tests.test_main_window_extraction import window, configure_window, ExtractionClient
from extraction.models import ColumnSpec
from extraction.xlsx_writer import read_candidate


def test_routes_keep_independent_inputs_and_write_never_sends_sources(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen._prompt_edit.setPlainText("Write a summary")
    screen.set_file_type("PDF (.pdf)")
    screen.set_route("pull")
    assert screen._prompt_edit.toPlainText() == ""
    screen._prompt_edit.setPlainText("Invoice number and total")
    source = Path("synthetic.docx")
    screen.set_paths((source,))
    screen.show_inspection((_document(source),))
    screen.set_route("write")
    assert screen._prompt_edit.toPlainText() == "Write a summary"
    assert screen.file_type() == "PDF (.pdf)"
    assert screen._paths == (source,)
    assert screen.snapshot(False).paths == ()
    with qtbot.waitSignal(screen.generate_requested) as generated:
        screen._primary_btn.click()
    assert generated.args == ["PDF (.pdf)", screen._save_dir, "Write a summary"]
    screen.set_route("pull")
    assert screen._prompt_edit.toPlainText() == "Invoice number and total"
    assert screen.file_type() == "Excel (.xlsx)"
    with qtbot.waitSignal(screen.propose_requested) as proposed:
        screen._primary_btn.click()
    assert proposed.args[0].paths == (source,)
    assert proposed.args[0].request == "Invoice number and total"


def test_pull_without_sources_cannot_generate(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    screen._prompt_edit.setPlainText("Find the totals")
    generated = []
    screen.generate_requested.connect(lambda *args: generated.append(args))
    screen._primary_btn.click()
    screen._primary_clicked()  # the route guard also applies to a stale queued action
    assert generated == [] and not screen._primary_btn.isEnabled()


@pytest.mark.parametrize("work", ["busy", "generating", "reading"])
def test_switching_is_blocked_for_every_kind_of_work(qtbot, isolated_profile, work):
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    screen._prompt_edit.setPlainText("Keep this request")
    if work == "busy":
        screen.set_busy(True)
    elif work == "generating":
        screen.set_generating(True)
    else:
        screen.set_paths((Path("synthetic.docx"),))
    screen.set_route("write")
    assert screen.route() == "pull"
    assert screen._prompt_edit.toPlainText() == "Keep this request"
    assert not screen._write_option.isEnabled()


def test_leaving_pull_invalidates_columns_review_acknowledgement_and_owned_job(
        window, tmp_path, qtbot):
    panel, source = configure_window(window, tmp_path, qtbot)
    window._ollama_client = ExtractionClient()
    panel._extract_btn.click()
    qtbot.waitUntil(lambda: window._extraction_thread is None)
    job = window._extraction_job
    panel._ack_checkbox.setChecked(True)
    panel.set_route("write")
    assert window._extraction_job is None and not job.exists()
    assert panel.candidate() is None and not panel._ack_checkbox.isChecked()
    assert panel.current_columns() == () and not panel.columns_confirmed()
    assert panel._pages.currentWidget() is panel._describe_page
    panel.set_route("pull")
    assert panel.snapshot(False).paths == (source,)
    assert panel.snapshot(False).request == "Extract the ID"
    assert panel.current_columns() == () and panel.candidate() is None


def test_late_pull_results_do_not_repopulate_write(window, tmp_path):
    panel = window._create_screen
    candidate = saved_candidate(tmp_path)
    window._on_inspection_ready((_document(Path("synthetic.docx")),))
    window._on_columns_ready((ColumnSpec("id", "ID", "Identifier"),))
    window._on_candidate_ready(candidate, read_candidate(candidate))
    assert panel.route() == "write"
    assert panel._documents == () and panel.current_columns() == ()
    assert panel.candidate() is None and panel._pages.currentWidget() is panel._describe_page


def test_late_write_result_does_not_clear_pull_request(window):
    panel = window._create_screen
    panel.set_route("pull")
    panel._prompt_edit.setPlainText("Keep the extraction request")
    window._on_generate_completed("synthetic.docx")
    window._on_template_completed("synthetic.pptx", ())
    assert panel._prompt_edit.toPlainText() == "Keep the extraction request"
    assert panel._pages.currentWidget() is panel._describe_page


def test_reading_problems_survive_a_round_trip(qtbot, isolated_profile):
    from dataclasses import replace
    from extraction.models import Issue
    screen = _screen(qtbot, isolated_profile)
    screen.set_route("pull")
    source = Path("synthetic.docx")
    screen.set_paths((source,))
    doc = _document(source)
    screen.show_inspection((replace(doc, issues=(
        Issue("skipped_text_box", doc.source_id, doc.source_id + "#", "unread"),)),))
    screen.set_route("write")
    screen.set_route("pull")
    assert "text in text boxes was not read" in screen._source_coverage.toPlainText()


def test_pull_rejects_a_stale_write_request_and_write_status(window, tmp_path, monkeypatch):
    panel = window._create_screen
    panel.set_route("pull")
    window._current_model = "qwen3:8b"
    monkeypatch.setattr(window, "_start_freeform_generation",
                        lambda *args: pytest.fail("Pull started prompt generation"))
    window._on_generate_requested("Word (.docx)", str(tmp_path / "unused"), "Stale write")
    assert not (tmp_path / "unused").exists()
    panel.show_status("Keep this Pull message")
    window._on_generate_started()
    window._on_generate_progress("Stale progress")
    window._on_generate_failed("Stale failure")
    window._on_template_started()
    window._on_template_failed("Stale template failure")
    assert panel._status.text() == "Keep this Pull message"
    assert not panel._generating
