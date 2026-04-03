# simplicitor/app/parsers/llm_response_parser.py
# Phase 3: LLM response parser

import json
import re


class ParseError(Exception):
    """Raised when LLM response cannot be parsed into the expected structure."""

    def __init__(self, message: str, details: str = "") -> None:
        super().__init__(message)
        self.details = details


class LlmResponseParser:
    """Parses LLM JSON responses into structured dicts (Phase 3).

    Strips markdown fences, handles preamble/postamble text, and raises
    ParseError with details on unrecoverable failures.
    """

    # Valid section types for Word documents
    _WORD_SECTION_TYPES = {"text", "table", "list"}

    # Valid slide types for PowerPoint
    _PPTX_SLIDE_TYPES = {"title", "content", "section"}

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _clean(text: str) -> str:
        """Return *text* with whitespace and markdown fences stripped.

        Processing steps, in order:
        1. Strip leading/trailing whitespace.
        2. Remove markdown code fences (```json...``` or ```...```).
        3. Extract the outermost JSON object by finding the first ``{`` and
           last ``}`` — discards any preamble/postamble prose.
        """
        text = text.strip()

        # Remove markdown code fences (optional language tag)
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        # Extract outermost JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end >= start:
            text = text[start : end + 1]

        return text

    # -----------------------------------------------------------------------
    # Public parse methods
    # -----------------------------------------------------------------------

    def parse_word_response(self, text: str) -> dict:
        """Parse a Word generation LLM response into a validated dict.

        Expected structure::

            {
                "title": str,
                "sections": [
                    {"heading": str, "content": str, "type": "text"|"table"|"list"}
                ]
            }

        Missing ``type`` fields on sections default to ``"text"``.

        Raises:
            ParseError: If the text cannot be parsed or fails validation.
        """
        cleaned = self._clean(text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ParseError("Failed to parse Word response as JSON", details=str(exc)) from exc

        # Validate top-level keys
        if "title" not in data:
            raise ParseError("Word response missing required key: 'title'")
        if not isinstance(data["title"], str):
            raise ParseError(
                f"Word response 'title' must be a string, got {type(data['title']).__name__}"
            )
        if "sections" not in data:
            raise ParseError("Word response missing required key: 'sections'")
        if not isinstance(data["sections"], list):
            raise ParseError(
                f"Word response 'sections' must be a list, got {type(data['sections']).__name__}"
            )

        # Validate each section
        for idx, section in enumerate(data["sections"]):
            prefix = f"Word response sections[{idx}]"
            if "heading" not in section:
                raise ParseError(f"{prefix} missing required key: 'heading'")
            if not isinstance(section["heading"], str):
                raise ParseError(f"{prefix} 'heading' must be a string")
            if "content" not in section:
                raise ParseError(f"{prefix} missing required key: 'content'")
            if not isinstance(section["content"], str):
                raise ParseError(f"{prefix} 'content' must be a string")
            # Default missing type to "text"
            if "type" not in section:
                section["type"] = "text"
            if section["type"] not in self._WORD_SECTION_TYPES:
                raise ParseError(
                    f"Invalid section type '{section['type']}'; must be one of {sorted(self._WORD_SECTION_TYPES)}",
                    details=f"section index {idx}",
                )

        return data

    def parse_excel_response(self, text: str) -> dict:
        """Parse an Excel generation LLM response into a validated dict.

        Expected structure::

            {
                "sheet_name": str,
                "headers": [str, ...],
                "rows": [[cell_value, ...], ...],
                "formulas": [{"cell": str, "formula": str}, ...]  # optional
            }

        Missing ``formulas`` key defaults to ``[]``.
        Rows shorter than ``headers`` are padded with empty strings.

        Raises:
            ParseError: If the text cannot be parsed or fails validation.
        """
        cleaned = self._clean(text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ParseError("Failed to parse Excel response as JSON", details=str(exc)) from exc

        # Validate required keys
        for key in ("sheet_name", "headers", "rows"):
            if key not in data:
                raise ParseError(f"Excel response missing required key: '{key}'")

        if not isinstance(data["sheet_name"], str):
            raise ParseError(
                f"Excel response 'sheet_name' must be a string, "
                f"got {type(data['sheet_name']).__name__}"
            )
        if not isinstance(data["headers"], list):
            raise ParseError(
                f"Excel response 'headers' must be a list, "
                f"got {type(data['headers']).__name__}"
            )
        if not all(isinstance(h, str) for h in data["headers"]):
            raise ParseError(
                "headers must be a list of strings",
                details=f"headers={data['headers']!r}",
            )
        if not isinstance(data["rows"], list):
            raise ParseError(
                f"Excel response 'rows' must be a list, "
                f"got {type(data['rows']).__name__}"
            )

        # Default missing formulas
        if "formulas" not in data:
            data["formulas"] = []

        # Pad short rows with empty strings rather than failing hard
        num_headers = len(data["headers"])
        for idx, row in enumerate(data["rows"]):
            if not isinstance(row, list):
                raise ParseError(f"Excel response rows[{idx}] must be a list")
            if len(row) < num_headers:
                data["rows"][idx] = row + [""] * (num_headers - len(row))

        return data

    def parse_pptx_response(self, text: str) -> dict:
        """Parse a PowerPoint generation LLM response into a validated dict.

        Expected structure::

            {
                "title": str,
                "slides": [
                    {"title": str, "bullets": [str, ...], "type": "title"|"content"|"section"}
                ]
            }

        Missing ``type`` on a slide defaults to ``"content"``.
        Missing ``bullets`` on a slide defaults to ``[]``.

        Raises:
            ParseError: If the text cannot be parsed or fails validation.
        """
        cleaned = self._clean(text)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ParseError("Failed to parse PPTX response as JSON", details=str(exc)) from exc

        # Validate top-level keys
        if "title" not in data:
            raise ParseError("PPTX response missing required key: 'title'")
        if not isinstance(data["title"], str):
            raise ParseError(
                f"PPTX response 'title' must be a string, got {type(data['title']).__name__}"
            )
        if "slides" not in data:
            raise ParseError("PPTX response missing required key: 'slides'")
        if not isinstance(data["slides"], list):
            raise ParseError(
                f"PPTX response 'slides' must be a list, got {type(data['slides']).__name__}"
            )

        # Validate each slide
        for idx, slide in enumerate(data["slides"]):
            prefix = f"PPTX response slides[{idx}]"
            if "title" not in slide:
                raise ParseError(f"{prefix} missing required key: 'title'")
            if not isinstance(slide["title"], str):
                raise ParseError(f"{prefix} 'title' must be a string")
            # Default missing bullets to []
            if "bullets" not in slide:
                slide["bullets"] = []
            if not isinstance(slide["bullets"], list):
                raise ParseError(f"{prefix} 'bullets' must be a list")
            # Default missing type to "content"
            if "type" not in slide:
                slide["type"] = "content"
            if slide["type"] not in self._PPTX_SLIDE_TYPES:
                raise ParseError(
                    f"Invalid slide type '{slide['type']}'; must be one of {sorted(self._PPTX_SLIDE_TYPES)}",
                    details=f"slide index {idx}",
                )

        return data


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def parse_word(text: str) -> dict:
    """Parse an LLM Word response. Convenience wrapper around LlmResponseParser."""
    return LlmResponseParser().parse_word_response(text)


def parse_excel(text: str) -> dict:
    """Parse an LLM Excel response. Convenience wrapper around LlmResponseParser."""
    return LlmResponseParser().parse_excel_response(text)


def parse_pptx(text: str) -> dict:
    """Parse an LLM PowerPoint response. Convenience wrapper around LlmResponseParser."""
    return LlmResponseParser().parse_pptx_response(text)
