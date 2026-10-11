"""Generator write failures must not expose prompt-derived output names."""
import pytest

from app.generators.excel_generator import ExcelGenerator
from app.generators.pptx_generator import PptxGenerator
from app.generators.word_generator import WordGenerator


@pytest.mark.parametrize("generator,parsed,suffix", [
    (WordGenerator, {"title": "Synthetic", "sections": []}, ".docx"),
    (ExcelGenerator, {"sheet_name": "Synthetic", "headers": [], "rows": []}, ".xlsx"),
    (PptxGenerator, {"title": "Synthetic", "slides": []}, ".pptx"),
])
def test_failed_write_does_not_log_prompt_words(generator, parsed, suffix, tmp_path, caplog):
    # A real directory at the output path makes each library's save fail.
    destination = tmp_path / ("Salary review for Jane" + suffix)
    destination.mkdir()
    with pytest.raises(OSError):
        generator().generate(parsed, destination)
    assert caplog.records
    assert "Jane" not in caplog.text
    assert str(destination) not in caplog.text
