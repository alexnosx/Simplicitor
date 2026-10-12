# tests/test_create_screen.py
def test_edit_placeholder_explains_and_offers_create(qtbot, isolated_profile):
    from app.widgets.edit_placeholder import EditPlaceholder
    page = EditPlaceholder()
    qtbot.addWidget(page)
    assert "later version" in page._body.text()
    with qtbot.waitSignal(page.create_requested):
        page._create_btn.click()
