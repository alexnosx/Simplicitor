# simplicitor/app/services/file_manipulator.py
# Phase 4: File manipulation orchestrator
from pathlib import Path


class FileManipulator:
    """Orchestrates file read → LLM → parse → write-back pipeline (Phase 4)."""

    def extract_text(self, file_path: Path) -> str:
        """Extract plain text content from a supported file."""
        raise NotImplementedError  # Phase 4

    def apply_changes(self, file_path: Path, original_text: str, llm_response: str) -> Path:
        """Apply LLM-suggested changes and write back to the file."""
        raise NotImplementedError  # Phase 4
