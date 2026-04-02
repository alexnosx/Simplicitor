# simplicitor/app/generators/excel_generator.py
# Phase 3: Excel spreadsheet generator
from pathlib import Path


class ExcelGenerator:
    """Generates .xlsx files from parsed LLM output (Phase 3)."""

    def generate(self, parsed: dict, output_path: Path) -> Path:
        """Write an Excel spreadsheet from the parsed LLM response structure."""
        raise NotImplementedError  # Phase 3
