"""One Create workspace, with source extraction first and prompt creation preserved."""
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.config.settings import Settings
from app.widgets.create_panel import CreatePanel
from app.widgets.extraction_panel import ExtractionPanel


class CreateWorkspace(QWidget):
    """Host the new source route and the existing prompt/template panel unchanged."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        self._tabs = QTabWidget()
        self.extraction_panel = ExtractionPanel()
        self.prompt_panel = CreatePanel(settings)
        self._tabs.addTab(self.extraction_panel, "From source files")
        self._tabs.addTab(self.prompt_panel, "From prompt")
        layout.addWidget(self._tabs)

    def set_busy(self, busy: bool) -> None:
        """Keep a long operation in its active route until it finishes."""
        self._tabs.tabBar().setEnabled(not busy)
