# simplicitor/app/services/file_generator.py
# Phase 3: File generation orchestrator
import logging
from pathlib import Path

from app.config.defaults import GENERATE_FILE_TYPES
from app.generators.excel_generator import ExcelGenerator
from app.generators.pptx_generator import PptxGenerator
from app.generators.word_generator import WordGenerator
from app.parsers.llm_response_parser import ParseError, parse_excel, parse_pptx, parse_word

logger = logging.getLogger(__name__)


class FileGenerationError(Exception):
    """Raised when the full generate pipeline fails (parse + write)."""


class FileGenerator:
    """Orchestrates LLM response → parse → file write pipeline.

    Does NOT call Ollama — it receives the already-fetched LLM response text.
    Retry logic (calling Ollama again) lives in GenerateWorker.
    """

    # Map file_type strings to (parser_fn, generator_class, extension)
    _DISPATCH: dict = {
        "Word (.docx)": (parse_word, WordGenerator, ".docx"),
        "Excel (.xlsx)": (parse_excel, ExcelGenerator, ".xlsx"),
        "PowerPoint (.pptx)": (parse_pptx, PptxGenerator, ".pptx"),
    }

    def generate(self, file_type: str, llm_response: str, output_path: Path) -> Path:
        """Parse llm_response and write the appropriate Office file.

        Args:
            file_type: One of GENERATE_FILE_TYPES ("Word (.docx)", "Excel (.xlsx)",
                       "PowerPoint (.pptx)")
            llm_response: Raw text returned by the LLM.
            output_path: Full path including filename where the file should be written.

        Returns:
            output_path as Path on success.

        Raises:
            FileGenerationError: If the response cannot be parsed or the file cannot be written.
            ValueError: If file_type is not recognized.
        """
        if file_type not in self._DISPATCH:
            raise ValueError(f"Unknown file type: {file_type!r}")

        parser_fn, generator_cls, extension = self._DISPATCH[file_type]
        output_path = Path(output_path)

        # Metadata only: never log LLM output, prompts, or file content.
        logger.debug("Parsing LLM response for file type %r (%d chars)", file_type, len(llm_response))
        try:
            parsed = parser_fn(llm_response)
        except ParseError as exc:
            logger.error(
                "Failed to parse LLM response for %r (%d chars, %s): %s",
                file_type, len(llm_response), type(exc).__name__, exc,
            )
            raise FileGenerationError(f"Could not parse LLM response: {exc}") from exc
        logger.debug("LLM response parsed successfully for %r", file_type)

        logger.debug("Writing %r file to %s", file_type, output_path)
        try:
            result = generator_cls().generate(parsed, output_path)
        except OSError as exc:
            logger.error("Failed to write file %s: %s", output_path, exc)
            raise FileGenerationError(f"Could not write file to {output_path}: {exc}") from exc
        except Exception as exc:
            logger.error("Unexpected error writing %r file %s: %s", file_type, output_path, exc)
            raise FileGenerationError(f"Unexpected error generating file: {exc}") from exc

        return result
