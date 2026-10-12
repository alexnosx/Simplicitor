# simplicitor/app/widgets/edit_placeholder.py
"""Edit document mode until selective editing is built; no file actions."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EditPlaceholder(QWidget):
    """Explain the deferred editing mode and offer the supported create route."""

    create_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        title = QLabel("Edit a document")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        self._body = QLabel(
            "Editing documents is coming in a later version of Simplicitor. The earlier "
            "editing feature was removed because it could damage files. For now, use Create "
            "new to make a new Word, PDF, Excel or PowerPoint file, or to pull information "
            "from your documents into Excel.")
        self._body.setWordWrap(True)
        self._create_btn = QPushButton("Go to Create new")
        self._create_btn.clicked.connect(self.create_requested)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self._body)
        layout.addSpacing(16)
        layout.addWidget(self._create_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
