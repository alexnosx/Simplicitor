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
