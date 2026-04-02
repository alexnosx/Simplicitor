# simplicitor/app/generators/word_generator.py
# Phase 3: Word document generator
from pathlib import Path


class WordGenerator:
    """Generates .docx files from parsed LLM output (Phase 3)."""

    def generate(self, parsed: dict, output_path: Path) -> Path:
        """Write a Word document from the parsed LLM response structure."""
        raise NotImplementedError  # Phase 3
