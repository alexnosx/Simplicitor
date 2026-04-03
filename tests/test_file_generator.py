# tests/test_file_generator.py
# Phase 3: Tests for FileGenerator dispatcher

import pytest
from pathlib import Path
from unittest.mock import patch
from app.services.file_generator import FileGenerator, FileGenerationError
from app.parsers.llm_response_parser import ParseError

VALID_WORD_JSON = '{"title": "T", "sections": [{"heading": "H", "content": "C", "type": "text"}]}'
VALID_EXCEL_JSON = '{"sheet_name": "S", "headers": ["A"], "rows": [["1"]], "formulas": []}'
VALID_PPTX_JSON = '{"title": "T", "slides": [{"title": "S", "bullets": [], "type": "title"}]}'


def test_file_generator_word(tmp_path):
    out = FileGenerator().generate("Word (.docx)", VALID_WORD_JSON, tmp_path / "out.docx")
    assert out.exists()


def test_file_generator_excel(tmp_path):
    out = FileGenerator().generate("Excel (.xlsx)", VALID_EXCEL_JSON, tmp_path / "out.xlsx")
    assert out.exists()


def test_file_generator_pptx(tmp_path):
    out = FileGenerator().generate("PowerPoint (.pptx)", VALID_PPTX_JSON, tmp_path / "out.pptx")
    assert out.exists()


def test_file_generator_unknown_type_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Unknown file type"):
        FileGenerator().generate("Unknown", VALID_WORD_JSON, tmp_path / "out.txt")


def test_file_generator_parse_error_raises_file_generation_error(tmp_path):
    with pytest.raises(FileGenerationError):
        FileGenerator().generate("Word (.docx)", "not json at all", tmp_path / "out.docx")


def test_file_generator_oserror_raises_file_generation_error(tmp_path):
    with patch("app.generators.word_generator.WordGenerator.generate", side_effect=OSError("disk full")):
        with pytest.raises(FileGenerationError):
            FileGenerator().generate("Word (.docx)", VALID_WORD_JSON, tmp_path / "out.docx")


def test_file_generator_returns_path_object(tmp_path):
    out = FileGenerator().generate("Word (.docx)", VALID_WORD_JSON, tmp_path / "out.docx")
    assert isinstance(out, Path)


def test_file_generator_returns_correct_output_path(tmp_path):
    output_path = tmp_path / "my_doc.docx"
    out = FileGenerator().generate("Word (.docx)", VALID_WORD_JSON, output_path)
    assert out == output_path


def test_file_generator_excel_parse_error_raises_file_generation_error(tmp_path):
    with pytest.raises(FileGenerationError):
        FileGenerator().generate("Excel (.xlsx)", "not json", tmp_path / "out.xlsx")


def test_file_generator_pptx_parse_error_raises_file_generation_error(tmp_path):
    with pytest.raises(FileGenerationError):
        FileGenerator().generate("PowerPoint (.pptx)", "not json", tmp_path / "out.pptx")
