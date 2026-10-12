"""Numbered workflow steps, with state preserved until the route changes."""
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.config.defaults import PRIMARY_ACCENT_COLOR


class StepIndicator(QWidget):
    """Show a numbered route and highlight its current step."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(16)
        self._layout.addStretch()
        self._labels: list[QLabel] = []
        self._badges: list[QLabel] = []
        self._pairs: list[QWidget] = []
        self._names: list[str] = []
        self._current = 0
        self.setStyleSheet(
            f"QLabel[current='true'] {{ color: {PRIMARY_ACCENT_COLOR}; font-weight: 600; }}"
            "QLabel[current='false'] { color: #626B78; }"
            "QLabel[badge='true'] { background: #EDF0F4; border-radius: 11px; }"
            f"QLabel[badge='true'][current='true'] {{ background: {PRIMARY_ACCENT_COLOR}; "
            "color: white; }")

    def set_steps(self, names: list[str]) -> None:
        """Replace the route, resetting its current step only when names change."""
        if names == self._names:
            return
        for pair in self._pairs:
            self._layout.removeWidget(pair)
            pair.hide()
            pair.deleteLater()
        self._labels, self._badges, self._pairs = [], [], []
        self._names = list(names)
        for number, name in enumerate(names, 1):
            pair = QWidget()
            layout = QHBoxLayout(pair)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(7)
            badge = QLabel(str(number))
            badge.setProperty("badge", True)
            badge.setFixedSize(22, 22)
            from PySide6.QtCore import Qt
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label = QLabel(name)
            label.setAccessibleName(f"Step {number}: {name}")
            layout.addWidget(badge)
            layout.addWidget(label)
            self._layout.insertWidget(len(self._pairs), pair)
            self._labels.append(label)
            self._badges.append(badge)
            self._pairs.append(pair)
        self.set_current(0)

    def current(self) -> int:
        """Return the current zero-based step."""
        return self._current

    def set_current(self, index: int) -> None:
        """Highlight a step without changing the route."""
        self._current = index
        for position, (label, badge) in enumerate(zip(self._labels, self._badges)):
            for control in (label, badge):
                control.setProperty("current", position == index)
                control.style().unpolish(control)
                control.style().polish(control)
