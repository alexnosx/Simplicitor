# tests/test_create_screen.py
def test_edit_placeholder_explains_and_offers_create(qtbot, isolated_profile):
    from app.widgets.edit_placeholder import EditPlaceholder
    page = EditPlaceholder()
    qtbot.addWidget(page)
    assert "later version" in page._body.text()
    with qtbot.waitSignal(page.create_requested):
        page._create_btn.click()


def test_step_indicator_keeps_state_and_layout(qtbot, isolated_profile):
    from app.widgets.step_indicator import StepIndicator
    steps = StepIndicator()
    qtbot.addWidget(steps)
    steps.set_steps(["Describe", "Choose columns", "Review and save"])
    steps.set_current(1)
    steps.set_steps(["Describe", "Choose columns", "Review and save"])  # same route: no reset
    assert steps.current() == 1
    assert [label.text() for label in steps._labels] == ["Describe", "Choose columns", "Review and save"]
    count = steps._layout.count()
    steps.set_steps(["Describe", "Save"])
    steps.set_steps(["Describe", "Choose columns", "Review and save"])
    assert steps._layout.count() == count  # no accumulating stretches
    assert steps.current() == 0
    assert steps._labels[0].property("current") is True


def test_anchor_issue_and_coverage_text_are_plain():
    from app.widgets.plain_labels import describe_anchor, describe_coverage, describe_issues
    assert describe_anchor("source-1#page:3") == "page 3"
    assert describe_anchor("source-1#p:0") == "paragraph 1"
    assert describe_anchor("source-2#t:0:r:1:c:2") == "table 1, row 2, column 3"
    assert describe_anchor("source-1#header:0:p:1") == "paragraph 2 of the header"
    assert describe_anchor("") == ""
    assert describe_issues("sectioned_source") == "Long document: check every value."
    assert describe_issues("leading_zero; excel_precision") == (
        "Starts with 0, so it was kept as text to keep every digit. "
        "Too many digits for an Excel number, so it was kept as text.")
    assert describe_issues("") == ""
    assert describe_issues("something_new") == "Check this value."
    assert describe_coverage("invoice-02.pdf", "source-2#page:3", "unreadable_page") == (
        "invoice-02.pdf, page 3: this page has too little text to read.")
    assert describe_coverage("a.docx", "source-1", "unsupported_structure") == (
        "a.docx: some parts of this file (such as text boxes, tracked changes or footnotes) were not read.")


from pathlib import Path


def _screen(qtbot, isolated_profile):
    from app.widgets.create_screen import CreateScreen
    screen = CreateScreen(isolated_profile)
    qtbot.addWidget(screen)
    screen.set_model("qwen3:8b")
    screen.set_ollama_connected(True)
    return screen


def test_without_sources_all_types_and_create_file_uses_chosen_folder(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    assert [screen._type_combo.itemText(i) for i in range(screen._type_combo.count())] == [
        "Word", "PDF", "Excel", "PowerPoint"]
    assert screen._primary_btn.text() == "Create file"
    screen._save_dir = str(tmp_path / "chosen")
    screen._prompt_edit.setPlainText("A one-page project summary")
    screen._type_combo.setCurrentText("PDF")
    with qtbot.waitSignal(screen.generate_requested) as blocker:
        screen._primary_btn.click()
    assert blocker.args == ["PDF (.pdf)", str(tmp_path / "chosen"), "A one-page project summary"]


def test_sources_force_excel_and_wait_for_inspection(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    source = tmp_path / "invoice.docx"
    source.write_bytes(b"x")
    ignored = tmp_path / "notes.txt"
    ignored.write_bytes(b"x")
    screen._type_combo.setCurrentText("Word")
    screen._prompt_edit.setPlainText("Invoice number and total")
    with qtbot.waitSignal(screen.inspect_requested):
        screen.set_paths((source, ignored))
    assert screen._source_list.count() == 1
    assert screen._type_combo.currentText() == "Excel"
    word = screen._type_combo.findText("Word")
    assert not screen._type_combo.model().item(word).isEnabled()
    assert screen._sources_note.isVisible()
    assert screen._primary_btn.text() == "Next: choose columns"
    assert not screen._primary_btn.isEnabled()  # still reading the files
    screen.show_inspection(())
    assert screen._primary_btn.isEnabled()
    with qtbot.waitSignal(screen.propose_requested):
        screen._primary_btn.click()


def test_same_named_files_stay_separate(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    a, b = tmp_path / "a" / "invoice.pdf", tmp_path / "b" / "invoice.pdf"
    for path in (a, b):
        path.parent.mkdir()
        path.write_bytes(b"x")
    screen.set_paths((a, b))
    assert screen._source_list.count() == 2


def test_removing_all_sources_restores_every_type(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"x")
    screen.set_paths((source,))
    screen.set_paths(())
    word = screen._type_combo.findText("Word")
    assert screen._type_combo.model().item(word).isEnabled()
    assert screen._primary_btn.text() == "Create file"
    assert screen._steps.current() == 0


def test_busy_freezes_setup_and_reports(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    with qtbot.waitSignal(screen.busy_changed) as blocker:
        screen.set_busy(True)
    assert blocker.args == [True]
    assert not screen._prompt_edit.isEnabled() and not screen._primary_btn.isEnabled()


def test_show_status_accepts_secondary_and_tooltip(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.show_status("Saved", False, "summary.pdf", "C:/out/summary.pdf")


def test_source_changes_are_ignored_while_busy(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    source = tmp_path / "invoice.pdf"
    source.write_bytes(b"x")
    screen.set_busy(True)
    requests = []
    screen.inspect_requested.connect(requests.append)
    screen.set_paths((source,))
    assert screen._source_list.count() == 0 and requests == []


def test_switch_from_powerpoint_to_sources_notifies_type_once(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    screen._type_combo.setCurrentText("PowerPoint")
    seen = []
    screen.file_type_changed.connect(seen.append)
    source = tmp_path / "invoice.docx"
    source.write_bytes(b"x")
    screen.set_paths((source,))
    assert seen == ["Excel (.xlsx)"]


def test_failed_inspection_ends_reading_and_keeps_setup(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    screen._prompt_edit.setPlainText("Invoice number")
    source = tmp_path / "invoice.docx"
    source.write_bytes(b"x")
    screen.set_paths((source,))
    assert not screen._primary_btn.isEnabled()
    screen.show_failure("Could not read the files.", ())
    screen.inspection_finished()
    assert screen._primary_btn.isEnabled() and screen._source_list.count() == 1


def test_cancel_is_outside_the_frozen_setup(qtbot, isolated_profile):
    screen = _screen(qtbot, isolated_profile)
    screen.set_busy(True)
    assert screen._cancel_btn.isEnabled()
    screen.set_busy(True, saving=True)
    assert not screen._cancel_btn.isEnabled()
    screen.set_busy(False)
    assert not screen._cancel_btn.isEnabled()

def test_saved_prompt_page_and_start_another_preserve_folder(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    screen._save_dir = str(tmp_path / "chosen")
    screen._prompt_edit.setPlainText("A synthetic summary")
    screen._type_combo.setCurrentText("PDF")
    screen.show_open_file_btn(str(tmp_path / "summary.pdf"))
    assert screen._pages.currentWidget() is screen._saved_page
    assert screen._steps.current() == 1
    assert screen._saved_label.text() == "Saved: summary.pdf"
    screen._another_btn.click()
    assert screen._pages.currentWidget() is screen._describe_page
    assert screen._prompt_edit.toPlainText() == ""
    assert screen.file_type() == "Word (.docx)"
    assert screen._save_dir == str(tmp_path / "chosen")
    assert screen._steps.current() == 0


def test_source_route_hides_save_folder_and_saved_reset_clears_sources(qtbot, isolated_profile, tmp_path):
    screen = _screen(qtbot, isolated_profile)
    screen.set_paths((tmp_path / "invoice.docx",))
    assert not screen._save_folder.isVisible()
    screen.show_open_file_btn(str(tmp_path / "data.xlsx"))
    assert screen._steps.current() == 2
    screen._another_btn.click()
    assert screen.snapshot(False).paths == ()
    assert screen._save_folder.isVisible()

