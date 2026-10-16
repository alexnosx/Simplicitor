"""Single-line local names and paths with their full literal text retained."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class ElidedLabel(QLabel):
    """Paint middle-elided text without shortening its accessible name or tooltip."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setText(text)

    def setText(self, text: str) -> None:
        """Retain the full value for accessibility, inspection and hover."""
        super().setText(text)
        self.setAccessibleName(text)
        self.setToolTip(text)

    def display_text(self) -> str:
        """Return the one-line text painted at the current width."""
        return self.fontMetrics().elidedText(
            self.text(), Qt.TextElideMode.ElideMiddle, self.contentsRect().width())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(self.contentsRect(), self.alignment(), self.display_text())
