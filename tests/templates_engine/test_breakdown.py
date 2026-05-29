# tests/templates_engine/test_breakdown.py
# Phase D: Tests for pptx structural inspector.
from pathlib import Path

import pytest
from pptx import Presentation

from templates_engine.breakdown import format_inspection, inspect_pptx

# Bundled default template shipped with Simplicitor -- a real .pptx fixture.
BUNDLED_TEMPLATE = (
    Path(__file__).parent.parent.parent / "simplicitor" / "templates" / "pptx_default.pptx"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_minimal_pptx(path: Path) -> Path:
    """Save a default-layout Presentation to path and return it."""
    prs = Presentation()  # uses python-pptx's built-in blank template
    prs.save(str(path))
    return path


# ---------------------------------------------------------------------------
# inspect_pptx — happy path
# ---------------------------------------------------------------------------

def test_inspect_returns_dict(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    assert isinstance(report, dict)
    assert "path" in report
    assert "layouts" in report


def test_inspect_has_layouts(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    assert len(report["layouts"]) > 0


def test_inspect_layout_has_required_keys(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    layout = report["layouts"][0]
    assert "layout_index" in layout
    assert "name" in layout
    assert "placeholders" in layout


def test_inspect_layout_index_is_sequential(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    for i, layout in enumerate(report["layouts"]):
        assert layout["layout_index"] == i


def test_inspect_placeholder_has_required_keys(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    # Find any layout that has placeholders
    ph = next(
        ph
        for layout in report["layouts"]
        for ph in layout["placeholders"]
    )
    assert "idx" in ph
    assert "type" in ph
    assert "name" in ph
    assert "position" in ph
    assert "is_custom" in ph


def test_inspect_detects_title_at_idx_0(tmp_path):
    """Layout 0 of a default presentation must have a placeholder with idx=0."""
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    layout_0 = report["layouts"][0]
    idx_values = [ph["idx"] for ph in layout_0["placeholders"]]
    assert 0 in idx_values, (
        f"Expected placeholder idx=0 in layout 0. Got indices: {idx_values}"
    )


def test_inspect_idx_0_type_contains_title(tmp_path):
    """The idx=0 placeholder in layout 0 should have a title-related type."""
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    layout_0 = report["layouts"][0]
    ph0 = next(ph for ph in layout_0["placeholders"] if ph["idx"] == 0)
    assert "TITLE" in ph0["type"].upper(), (
        f"Expected TITLE in type of idx=0 placeholder, got: {ph0['type']!r}"
    )


def test_inspect_is_custom_true_for_idx_gte_10(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    for layout in report["layouts"]:
        for ph in layout["placeholders"]:
            expected = ph["idx"] >= 10
            assert ph["is_custom"] == expected, (
                f"is_custom mismatch for idx={ph['idx']}: expected {expected}"
            )


def test_inspect_position_dict_has_four_keys(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    ph = next(
        ph for layout in report["layouts"] for ph in layout["placeholders"]
    )
    pos = ph["position"]
    assert set(pos.keys()) == {"left", "top", "width", "height"}


def test_inspect_path_is_absolute(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    assert Path(report["path"]).is_absolute()


def test_inspect_bundled_template_smoke():
    """Smoke test against the real bundled template shipped with Simplicitor."""
    assert BUNDLED_TEMPLATE.exists(), f"Bundled template not found at {BUNDLED_TEMPLATE}"
    report = inspect_pptx(BUNDLED_TEMPLATE)
    assert len(report["layouts"]) >= 1
    # Layout 0 must have a title placeholder at idx 0
    layout_0 = report["layouts"][0]
    assert any(ph["idx"] == 0 for ph in layout_0["placeholders"])


# ---------------------------------------------------------------------------
# inspect_pptx — error paths (conventional Simplicitor errors)
# ---------------------------------------------------------------------------

def test_missing_file_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match=r"not found|missing"):
        inspect_pptx(tmp_path / "ghost.pptx")


def test_non_pptx_extension_raises_value_error(tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("not a presentation", encoding="utf-8")
    with pytest.raises(ValueError, match=r"\.pptx|extension"):
        inspect_pptx(txt)


def test_non_pptx_error_names_extension(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")
    with pytest.raises(ValueError, match=r"\.pdf|extension|Expected"):
        inspect_pptx(pdf)


def test_corrupt_pptx_raises_value_error(tmp_path):
    bad = tmp_path / "corrupt.pptx"
    bad.write_bytes(b"this is not a zip file at all")
    with pytest.raises(ValueError, match=r"[Cc]ould not open|PowerPoint"):
        inspect_pptx(bad)


def test_corrupt_pptx_valid_zip_wrong_structure(tmp_path):
    """A valid zip that is not a pptx internally must also raise ValueError."""
    import zipfile as zf
    bad = tmp_path / "fake.pptx"
    with zf.ZipFile(str(bad), "w") as z:
        z.writestr("not_a_pptx.txt", "wrong content")
    with pytest.raises(ValueError, match=r"[Cc]ould not open|PowerPoint"):
        inspect_pptx(bad)


# ---------------------------------------------------------------------------
# format_inspection
# ---------------------------------------------------------------------------

def test_format_inspection_is_string(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    result = format_inspection(report)
    assert isinstance(result, str)


def test_format_inspection_contains_path(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    result = format_inspection(report)
    assert "test.pptx" in result


def test_format_inspection_contains_layout_index(tmp_path):
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    result = format_inspection(report)
    assert "[" in result and "]" in result  # layout index brackets


def test_format_inspection_marks_custom_placeholders(tmp_path):
    """idx >= 10 placeholders should be flagged as CUSTOM."""
    pptx = _make_minimal_pptx(tmp_path / "test.pptx")
    report = inspect_pptx(pptx)
    # Only check if any custom placeholder exists in the template
    has_custom = any(
        ph["is_custom"]
        for layout in report["layouts"]
        for ph in layout["placeholders"]
    )
    if has_custom:
        result = format_inspection(report)
        assert "CUSTOM" in result
