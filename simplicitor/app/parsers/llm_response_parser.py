# simplicitor/app/parsers/llm_response_parser.py
# Phase 3: LLM response parser


class ParseError(Exception):
    """Raised when LLM response cannot be parsed into the expected structure."""


class LlmResponseParser:
    """Parses LLM JSON responses into structured dicts (Phase 3).

    Strips markdown fences, handles common JSON errors, and raises
    ParseError with details on unrecoverable failures.
    """

    def parse_word_response(self, text: str) -> dict:
        """Parse Word generation response into {title, sections} dict."""
        raise NotImplementedError  # Phase 3

    def parse_excel_response(self, text: str) -> dict:
        """Parse Excel generation response into {sheet_name, headers, rows, formulas} dict."""
        raise NotImplementedError  # Phase 3

    def parse_pptx_response(self, text: str) -> dict:
        """Parse PowerPoint generation response into {title, slides} dict."""
        raise NotImplementedError  # Phase 3
