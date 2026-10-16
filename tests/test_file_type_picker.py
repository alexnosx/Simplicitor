"""File choices keep the generation API's existing four backend strings."""
import pytest
from PySide6.QtCore import Qt


def make_picker(qtbot):
    from app.widgets.file_type_picker import FileTypePicker
    picker = FileTypePicker()
    qtbot.addWidget(picker)
    return picker


def test_four_file_choices_have_exact_labels_order_and_one_selection(qtbot):
    from app.config.defaults import GENERATE_FILE_TYPES
    picker = make_picker(qtbot)
    assert list(picker._buttons) == list(GENERATE_FILE_TYPES)
    assert picker.file_type() == "Word (.docx)"
    assert [b.isChecked() for b in picker._buttons.values()] == [True, False, False, False]
    for label in GENERATE_FILE_TYPES:
        button = picker.button_for(label)
        assert button.accessibleName() == label
        assert button._caption_label.text() == label.split("(")[1].rstrip(")")
        assert not button._icon_label.pixmap().isNull()


def test_file_choice_emits_one_backend_label(qtbot):
    picker = make_picker(qtbot)
    changed = []
    picker.changed.connect(changed.append)
    picker.button_for("PDF (.pdf)").click()
    picker.button_for("PDF (.pdf)").click()
    assert picker.file_type() == "PDF (.pdf)"
    assert changed == ["PDF (.pdf)"]
    picker.setEnabled(False)
    picker.button_for("Word (.docx)").click()
    assert picker.file_type() == "PDF (.pdf)" and changed == ["PDF (.pdf)"]


def test_programmatic_choice_changes_once_and_rejects_unknown(qtbot):
    picker = make_picker(qtbot)
    changed = []
    picker.changed.connect(changed.append)
    picker.set_file_type("Excel (.xlsx)")
    picker.set_file_type("Excel (.xlsx)")
    with pytest.raises(ValueError):
        picker.set_file_type("Unknown")
    assert picker.file_type() == "Excel (.xlsx)" and changed == ["Excel (.xlsx)"]


def test_space_activates_a_format_choice(qtbot):
    picker = make_picker(qtbot)
    button = picker.button_for("PDF (.pdf)")
    button.setFocus()
    qtbot.keyClick(button, Qt.Key.Key_Space)
    assert picker.file_type() == "PDF (.pdf)"
