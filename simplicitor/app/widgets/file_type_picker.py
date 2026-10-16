"""Four generation formats with the existing backend labels and change semantics."""
from functools import lru_cache

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QWidget

from app.config.defaults import APP_FONT_FAMILY, FILE_MARK_COLORS, GENERATE_FILE_TYPES
from app.widgets.choice_button import ChoiceButton


@lru_cache(maxsize=4)
def file_mark(label: str) -> QIcon:
    """Cache small, decorative format marks drawn with Qt, without external assets."""
    name = label.split(" (", 1)[0]
    pixmap = QPixmap(60, 60)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(FILE_MARK_COLORS[name]))
    painter.drawRoundedRect(2, 2, 56, 56, 9, 9)
    painter.setPen(Qt.GlobalColor.white)
    painter.setFont(QFont(APP_FONT_FAMILY, 12, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter,
                     {"Word": "W", "PDF": "PDF", "Excel": "X", "PowerPoint": "P"}[name])
    painter.end()
    return QIcon(pixmap)


class FileTypePicker(QWidget):
    """Own one selected backend label, emitting once only for a real change."""
    changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, ChoiceButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        for index, label in enumerate(GENERATE_FILE_TYPES):
            name, extension = label.split(" (", 1)
            button = ChoiceButton(name, extension.rstrip(")"), file_mark(label))
            button.setAccessibleName(label)
            self._group.addButton(button)
            self._buttons[label] = button
            button.toggled.connect(lambda checked, value=label: self.changed.emit(value)
                                   if checked else None)
            grid.addWidget(button, index // 2, index % 2)
        self._buttons[GENERATE_FILE_TYPES[0]].setChecked(True)

    def file_type(self) -> str:
        """Return the selected backend label."""
        return next(label for label, button in self._buttons.items() if button.isChecked())

    def set_file_type(self, label: str) -> None:
        """Select a known label; same-value selection emits no change."""
        if label not in self._buttons:
            raise ValueError("Unknown file type.")
        self._buttons[label].setChecked(True)

    def button_for(self, label: str) -> ChoiceButton:
        """Return the actual button for keyboard, focus and state inspection."""
        return self._buttons[label]
