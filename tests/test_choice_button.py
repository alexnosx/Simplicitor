"""The visual parts of a choice remain one accessible, keyboard-ready button."""
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap


@pytest.mark.parametrize("region", ["title", "caption", "icon", "check"])
def test_clicking_a_choice_region_emits_one_action(qtbot, qapp, region):
    from app.widgets.choice_button import ChoiceButton
    pixmap = QPixmap(24, 24)
    pixmap.fill(QColor("blue"))
    button = ChoiceButton("Write a new document", "A synthetic explanation", QIcon(pixmap))
    qtbot.addWidget(button)
    button.resize(440, 100)
    qapp.processEvents()
    events = []
    button.clicked.connect(lambda checked: events.append(checked))
    child = getattr(button, f"_{region}_label")
    assert child.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton,
                     pos=child.mapTo(button, child.rect().center()))
    assert events == [True] and button.isChecked()
    assert "Write a new document" in button.accessibleName()
    assert "A synthetic explanation" in button.accessibleName()


def test_choice_keeps_caption_wrapped_and_shows_its_selected_mark(qtbot):
    from app.widgets.choice_button import ChoiceButton
    button = ChoiceButton("Title", "A longer caption that must wrap")
    qtbot.addWidget(button)
    assert button._caption_label.wordWrap()
    assert button._check_label.text() == ""
    button.setChecked(True)
    assert button._check_label.text()
    button.setEnabled(False)
    assert not button.isEnabled()


def test_choices_show_light_hover_selection_and_focus(qtbot):
    from app.config.defaults import CHOICE_HOVER_COLOR, CHOICE_SELECTED_COLOR, PRIMARY_ACCENT_COLOR
    from app.widgets.choice_button import ChoiceButton
    button = ChoiceButton("Title", "Caption")
    qtbot.addWidget(button)
    style = button.styleSheet()
    assert "ChoiceButton:hover" in style and CHOICE_HOVER_COLOR in style
    assert "ChoiceButton:checked" in style and CHOICE_SELECTED_COLOR in style
    assert "ChoiceButton:focus" in style and PRIMARY_ACCENT_COLOR in style
