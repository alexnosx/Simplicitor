# simplicitor/app/services/file_generator.py
# Phase 3: File generation orchestrator
from pathlib import Path


class FileGenerator:
    """Orchestrates prompt → LLM → parse → file write pipeline (Phase 3)."""

    def generate(self, file_type: str, llm_response: str, output_path: Path) -> Path:
        """Parse llm_response and write the appropriate file type."""
        raise NotImplementedError  # Phase 3
