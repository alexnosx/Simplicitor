# simplicitor/app/generators/pptx_generator.py
# Phase 3: PowerPoint generator
from pathlib import Path


class PptxGenerator:
    """Generates .pptx files from parsed LLM output (Phase 3)."""

    def generate(self, parsed: dict, output_path: Path) -> Path:
        """Write a PowerPoint presentation from the parsed LLM response structure."""
        raise NotImplementedError  # Phase 3
