# tests/test_llm_response_parser.py
# TDD tests for the Phase 3 LLM response parser.
import json

import pytest

from app.parsers.llm_response_parser import (
    LlmResponseParser,
    ParseError,
    parse_excel,
    parse_pptx,
    parse_word,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

VALID_WORD = {
    "title": "My Report",
    "sections": [
        {"heading": "Introduction", "content": "Some text here.", "type": "text"},
        {"heading": "Data", "content": "More text.", "type": "list"},
    ],
}

VALID_EXCEL = {
    "sheet_name": "Budget",
    "headers": ["Item", "Amount"],
    "rows": [["Rent", "1200"], ["Food", "400"]],
    "formulas": [{"cell": "B4", "formula": "=SUM(B2:B3)"}],
}

VALID_PPTX = {
    "title": "My Deck",
    "slides": [
        {"title": "Intro", "bullets": ["Point one", "Point two"], "type": "title"},
        {"title": "Details", "bullets": ["Detail A"], "type": "content"},
    ],
}


def _json(obj: dict) -> str:
    """Serialize dict to a JSON string."""
    return json.dumps(obj)


def _fenced(obj: dict, lang: str = "json") -> str:
    """Wrap JSON string in markdown code fences."""
    body = _json(obj)
    return f"```{lang}\n{body}\n```"


def _with_preamble(obj: dict) -> str:
    """Surround JSON with leading/trailing non-JSON text."""
    return f"Here is the JSON response you requested:\n{_json(obj)}\nThat's all!"


# ---------------------------------------------------------------------------
# ParseError
# ---------------------------------------------------------------------------

class TestParseError:
    def test_is_exception(self) -> None:
        err = ParseError("boom")
        assert isinstance(err, Exception)

    def test_message(self) -> None:
        err = ParseError("something went wrong")
        assert str(err) == "something went wrong"

    def test_details_default_empty(self) -> None:
        err = ParseError("msg")
        assert err.details == ""

    def test_details_stored(self) -> None:
        err = ParseError("msg", details="raw cause")
        assert err.details == "raw cause"


# ---------------------------------------------------------------------------
# _clean (via happy-path side-effects)
# ---------------------------------------------------------------------------

class TestClean:
    """Test _clean indirectly by verifying the parsers accept cleaned inputs."""

    def test_strips_whitespace(self) -> None:
        text = "   " + _json(VALID_WORD) + "   "
        result = LlmResponseParser().parse_word_response(text)
        assert result["title"] == "My Report"

    def test_strips_json_fenced(self) -> None:
        result = LlmResponseParser().parse_word_response(_fenced(VALID_WORD, "json"))
        assert result["title"] == "My Report"

    def test_strips_plain_fenced(self) -> None:
        result = LlmResponseParser().parse_word_response(_fenced(VALID_WORD, ""))
        assert result["title"] == "My Report"

    def test_strips_preamble_text(self) -> None:
        result = LlmResponseParser().parse_word_response(_with_preamble(VALID_WORD))
        assert result["title"] == "My Report"


# ---------------------------------------------------------------------------
# parse_word_response — happy path
# ---------------------------------------------------------------------------

class TestParseWordResponse:
    def test_clean_json_returns_dict(self) -> None:
        result = LlmResponseParser().parse_word_response(_json(VALID_WORD))
        assert isinstance(result, dict)

    def test_title_present(self) -> None:
        result = LlmResponseParser().parse_word_response(_json(VALID_WORD))
        assert result["title"] == "My Report"

    def test_sections_present(self) -> None:
        result = LlmResponseParser().parse_word_response(_json(VALID_WORD))
        assert len(result["sections"]) == 2

    def test_json_wrapped_in_markdown_fences(self) -> None:
        result = LlmResponseParser().parse_word_response(_fenced(VALID_WORD))
        assert result["title"] == "My Report"

    def test_json_with_preamble_text(self) -> None:
        result = LlmResponseParser().parse_word_response(_with_preamble(VALID_WORD))
        assert result["title"] == "My Report"

    def test_missing_type_defaults_to_text(self) -> None:
        doc = {
            "title": "T",
            "sections": [{"heading": "H", "content": "C"}],
        }
        result = LlmResponseParser().parse_word_response(_json(doc))
        assert result["sections"][0]["type"] == "text"

    def test_missing_title_raises_parse_error(self) -> None:
        bad = {"sections": [{"heading": "H", "content": "C", "type": "text"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_missing_sections_raises_parse_error(self) -> None:
        bad = {"title": "T"}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_title_wrong_type_raises_parse_error(self) -> None:
        bad = {"title": 42, "sections": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_sections_wrong_type_raises_parse_error(self) -> None:
        bad = {"title": "T", "sections": "not a list"}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_completely_invalid_text_raises_parse_error_with_details(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            LlmResponseParser().parse_word_response("this is not json at all!!!")
        assert exc_info.value.details != ""

    def test_section_missing_heading_raises_parse_error(self) -> None:
        bad = {"title": "T", "sections": [{"content": "C", "type": "text"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_section_missing_content_raises_parse_error(self) -> None:
        bad = {"title": "T", "sections": [{"heading": "H", "type": "text"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(_json(bad))

    def test_parse_word_invalid_section_type_raises(self) -> None:
        data = {"title": "T", "sections": [{"heading": "H", "content": "C", "type": "invalid"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(json.dumps(data))

    def test_non_dict_section_raises(self) -> None:
        data = {"title": "T", "sections": ["not a dict"]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_word_response(json.dumps(data))


# ---------------------------------------------------------------------------
# parse_excel_response — happy path
# ---------------------------------------------------------------------------

class TestParseExcelResponse:
    def test_clean_json_returns_dict(self) -> None:
        result = LlmResponseParser().parse_excel_response(_json(VALID_EXCEL))
        assert isinstance(result, dict)

    def test_sheet_name_present(self) -> None:
        result = LlmResponseParser().parse_excel_response(_json(VALID_EXCEL))
        assert result["sheet_name"] == "Budget"

    def test_headers_present(self) -> None:
        result = LlmResponseParser().parse_excel_response(_json(VALID_EXCEL))
        assert result["headers"] == ["Item", "Amount"]

    def test_rows_present(self) -> None:
        result = LlmResponseParser().parse_excel_response(_json(VALID_EXCEL))
        assert len(result["rows"]) == 2

    def test_formulas_present(self) -> None:
        result = LlmResponseParser().parse_excel_response(_json(VALID_EXCEL))
        assert result["formulas"][0]["cell"] == "B4"

    def test_json_wrapped_in_markdown_fences(self) -> None:
        result = LlmResponseParser().parse_excel_response(_fenced(VALID_EXCEL))
        assert result["sheet_name"] == "Budget"

    def test_missing_formulas_defaults_to_empty_list(self) -> None:
        doc = {
            "sheet_name": "S",
            "headers": ["A", "B"],
            "rows": [["1", "2"]],
        }
        result = LlmResponseParser().parse_excel_response(_json(doc))
        assert result["formulas"] == []

    def test_short_row_padded_with_empty_strings(self) -> None:
        doc = {
            "sheet_name": "S",
            "headers": ["A", "B", "C"],
            "rows": [["only_one"]],
            "formulas": [],
        }
        result = LlmResponseParser().parse_excel_response(_json(doc))
        assert result["rows"][0] == ["only_one", "", ""]

    def test_missing_sheet_name_raises_parse_error(self) -> None:
        bad = {"headers": ["A"], "rows": [], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(_json(bad))

    def test_missing_headers_raises_parse_error(self) -> None:
        bad = {"sheet_name": "S", "rows": [], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(_json(bad))

    def test_missing_rows_raises_parse_error(self) -> None:
        bad = {"sheet_name": "S", "headers": ["A"], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(_json(bad))

    def test_headers_wrong_type_raises_parse_error(self) -> None:
        bad = {"sheet_name": "S", "headers": "not a list", "rows": [], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(_json(bad))

    def test_rows_wrong_type_raises_parse_error(self) -> None:
        bad = {"sheet_name": "S", "headers": ["A"], "rows": "not a list", "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(_json(bad))

    def test_completely_invalid_text_raises_parse_error_with_details(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            LlmResponseParser().parse_excel_response("not json at all")
        assert exc_info.value.details != ""

    def test_parse_excel_non_string_header_raises(self) -> None:
        data = {"sheet_name": "S", "headers": ["col1", 42], "rows": [], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(json.dumps(data))

    def test_nested_cell_value_raises(self) -> None:
        data = {"sheet_name": "S", "headers": ["col"], "rows": [[{"nested": "dict"}]], "formulas": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_excel_response(json.dumps(data))


# ---------------------------------------------------------------------------
# parse_pptx_response — happy path
# ---------------------------------------------------------------------------

class TestParsePptxResponse:
    def test_clean_json_returns_dict(self) -> None:
        result = LlmResponseParser().parse_pptx_response(_json(VALID_PPTX))
        assert isinstance(result, dict)

    def test_title_present(self) -> None:
        result = LlmResponseParser().parse_pptx_response(_json(VALID_PPTX))
        assert result["title"] == "My Deck"

    def test_slides_present(self) -> None:
        result = LlmResponseParser().parse_pptx_response(_json(VALID_PPTX))
        assert len(result["slides"]) == 2

    def test_json_wrapped_in_markdown_fences(self) -> None:
        result = LlmResponseParser().parse_pptx_response(_fenced(VALID_PPTX))
        assert result["title"] == "My Deck"

    def test_json_with_preamble_text(self) -> None:
        result = LlmResponseParser().parse_pptx_response(_with_preamble(VALID_PPTX))
        assert result["title"] == "My Deck"

    def test_missing_slide_type_defaults_to_content(self) -> None:
        doc = {
            "title": "D",
            "slides": [{"title": "S", "bullets": ["b"]}],
        }
        result = LlmResponseParser().parse_pptx_response(_json(doc))
        assert result["slides"][0]["type"] == "content"

    def test_missing_bullets_defaults_to_empty_list(self) -> None:
        doc = {
            "title": "D",
            "slides": [{"title": "S", "type": "content"}],
        }
        result = LlmResponseParser().parse_pptx_response(_json(doc))
        assert result["slides"][0]["bullets"] == []

    def test_missing_title_raises_parse_error(self) -> None:
        bad = {"slides": [{"title": "S", "bullets": [], "type": "content"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(_json(bad))

    def test_missing_slides_raises_parse_error(self) -> None:
        bad = {"title": "D"}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(_json(bad))

    def test_title_wrong_type_raises_parse_error(self) -> None:
        bad = {"title": 99, "slides": []}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(_json(bad))

    def test_slides_wrong_type_raises_parse_error(self) -> None:
        bad = {"title": "D", "slides": "nope"}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(_json(bad))

    def test_slide_missing_title_raises_parse_error(self) -> None:
        bad = {"title": "D", "slides": [{"bullets": [], "type": "content"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(_json(bad))

    def test_completely_invalid_text_raises_parse_error_with_details(self) -> None:
        with pytest.raises(ParseError) as exc_info:
            LlmResponseParser().parse_pptx_response("%%% garbage %%%")
        assert exc_info.value.details != ""

    def test_parse_pptx_invalid_slide_type_raises(self) -> None:
        data = {"title": "T", "slides": [{"title": "S", "bullets": [], "type": "bad"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(json.dumps(data))

    def test_non_string_bullet_raises(self) -> None:
        data = {"title": "T", "slides": [{"title": "S", "bullets": [42], "type": "content"}]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(json.dumps(data))

    def test_non_dict_slide_raises(self) -> None:
        data = {"title": "T", "slides": ["not a dict"]}
        with pytest.raises(ParseError):
            LlmResponseParser().parse_pptx_response(json.dumps(data))


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_parse_word_returns_dict(self) -> None:
        result = parse_word(_json(VALID_WORD))
        assert result["title"] == "My Report"

    def test_parse_excel_returns_dict(self) -> None:
        result = parse_excel(_json(VALID_EXCEL))
        assert result["sheet_name"] == "Budget"

    def test_parse_pptx_returns_dict(self) -> None:
        result = parse_pptx(_json(VALID_PPTX))
        assert result["title"] == "My Deck"

    def test_parse_word_propagates_parse_error(self) -> None:
        with pytest.raises(ParseError):
            parse_word("bad input")

    def test_parse_excel_propagates_parse_error(self) -> None:
        with pytest.raises(ParseError):
            parse_excel("bad input")

    def test_parse_pptx_propagates_parse_error(self) -> None:
        with pytest.raises(ParseError):
            parse_pptx("bad input")
