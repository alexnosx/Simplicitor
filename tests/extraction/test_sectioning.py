"""Context accounting and structural coverage use hand-sized source units."""
from pathlib import Path

from extraction.models import ColumnSpec, SourceDocument, SourceUnit


def source(texts, groups=None):
    return SourceDocument("one", Path("one.docx"), "one", tuple(
        SourceUnit(f"one#p:{i}", text, "paragraph", i, groups[i] if groups else "")
        for i, text in enumerate(texts)
    ), 1)


def profile(context=4096, output=256):
    from extraction.models import ExtractionProfile
    return ExtractionProfile("qwen", {"num_ctx": context, "num_predict": output})


def test_request_boundary_uses_bytes_per_token_and_ignores_output_schema():
    from extraction.sectioning import request_fits
    # ceil((3 + 3) / 2.5) + 256 template + 10 output = 269 tokens.
    assert request_fits("abc", "def", {"description": "x" * 10000}, profile(269, 10))
    assert not request_fits("abc", "def", {}, profile(268, 10))


def test_dense_pdf_page_can_go_whole_with_ten_columns():
    from extraction.sectioning import make_sections
    doc = source(["Dense financial narrative " * 480])
    columns = tuple(ColumnSpec(f"c{i}", f"Column {i}", "A requested field") for i in range(10))
    sections = make_sections((doc,), profile(16384, 4096), columns=columns)
    assert len(sections) == 1 and not sections[0].excluded


def test_whole_file_larger_than_old_byte_limit_is_one_request_when_context_allows():
    from extraction.sectioning import make_sections
    doc = source(["a" * 4500, "b" * 4500])
    sections = make_sections((doc,), profile(16384))
    assert len(sections) == 1 and not sections[0].excluded
    assert sections[0].unit_ids == ("one#p:0", "one#p:1")


def test_small_context_sections_without_overlap_or_dropped_units():
    from extraction.sectioning import make_sections
    doc = source([str(i) * 2000 for i in range(6)])
    sections = make_sections((doc,), profile())
    assert len(sections) > 1
    assert not any(s.excluded for s in sections)
    assert [u for s in sections for u in s.unit_ids] == [u.anchor for u in doc.units]


def test_table_row_cells_stay_together_and_oversized_group_is_visible():
    from extraction.sectioning import make_sections
    doc = source(["a" * 500, "b" * 500, "c" * 10000, "tail"],
                 ["row-0", "row-0", "row-1", "tail"])
    sections = make_sections((doc,), profile())
    assert any(s.unit_ids[:2] == ("one#p:0", "one#p:1") for s in sections)
    assert [s.unit_ids for s in sections if s.excluded] == [("one#p:2",)]
    assert [u for s in sections for u in s.unit_ids] == [u.anchor for u in doc.units]


def test_selected_units_use_the_whole_file_request_contract():
    import json
    from extraction.request_format import build_extraction_prompt
    doc = source(["ID 00123", "ID 00456"])
    payload = json.loads(build_extraction_prompt(doc, (), "Extract IDs", ("one#p:1",)))
    assert payload == {"record_id": "one", "columns": [], "request": "Extract IDs",
                       "source_units": [{"anchor": "one#p:1", "text": "ID 00456", "group": ""}]}
