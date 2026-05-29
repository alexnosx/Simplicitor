# tests/templates_engine/test_manifest.py
# Phase B: Tests for manifest schema, loader, and linter.
from pathlib import Path

import pytest
import yaml

from templates_engine.manifest import FieldDef, Manifest, SlideTypeDef, lint_manifest, load_manifest

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# load_manifest — valid
# ---------------------------------------------------------------------------

def test_valid_manifest_loads():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    assert isinstance(m, Manifest)
    assert m.name == "test_template"
    assert m.type == "pptx"
    assert m.template_file == "test_template.pptx"
    assert "title" in m.slide_types
    assert "content" in m.slide_types


def test_valid_manifest_slide_structure():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    title = m.slide_types["title"]
    assert title.layout_index == 0
    assert title.repeatable is False
    assert len(title.fields) == 2
    assert title.fields[0].name == "title"
    assert title.fields[0].kind == "text"
    assert title.fields[0].required is True
    assert title.fields[0].max_chars == 100


def test_valid_manifest_bullets_field():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    content = m.slide_types["content"]
    body = next(f for f in content.fields if f.name == "body")
    assert body.kind == "bullets"
    assert body.max_items == 8
    assert body.required is False


def test_valid_manifest_image_field():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    photo = m.slide_types["photo"]
    img = next(f for f in photo.fields if f.name == "image")
    assert img.kind == "image"
    assert img.placeholder_idx == 10


def test_repeatable_defaults_false():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    assert m.slide_types["title"].repeatable is False
    assert m.slide_types["content"].repeatable is True


def test_manifest_is_immutable():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    with pytest.raises(Exception):  # pydantic ValidationError or AttributeError
        m.name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_manifest — broken_kind_manifest fixture
# ---------------------------------------------------------------------------

def test_broken_kind_raises_value_error():
    with pytest.raises(ValueError):
        load_manifest(FIXTURES / "broken_kind_manifest.yaml")


def test_broken_kind_error_names_problem():
    with pytest.raises(ValueError, match=r"kind|invalid_kind|validation failed"):
        load_manifest(FIXTURES / "broken_kind_manifest.yaml")


# ---------------------------------------------------------------------------
# load_manifest — broken_duplicate_manifest fixture
# ---------------------------------------------------------------------------

def test_broken_duplicate_raises_value_error():
    with pytest.raises(ValueError):
        load_manifest(FIXTURES / "broken_duplicate_manifest.yaml")


def test_broken_duplicate_error_names_field():
    with pytest.raises(ValueError, match=r"duplicate.*body|body.*duplicate"):
        load_manifest(FIXTURES / "broken_duplicate_manifest.yaml")


# ---------------------------------------------------------------------------
# load_manifest — inline bad-kind (isolated)
# ---------------------------------------------------------------------------

def test_bad_kind_raises_value_error(tmp_path):
    data = {
        "name": "x",
        "type": "pptx",
        "template_file": "x.pptx",
        "description": "d",
        "slide_types": {
            "s": {
                "layout_index": 0,
                "fields": [
                    {"name": "f", "placeholder_idx": 0, "kind": "video", "required": True}
                ],
            }
        },
    }
    p = tmp_path / "bad_kind.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"kind|validation failed"):
        load_manifest(p)


# ---------------------------------------------------------------------------
# load_manifest — inline duplicate field name (isolated)
# ---------------------------------------------------------------------------

def test_duplicate_field_name_raises_value_error(tmp_path):
    data = {
        "name": "x",
        "type": "pptx",
        "template_file": "x.pptx",
        "description": "d",
        "slide_types": {
            "s": {
                "layout_index": 0,
                "fields": [
                    {"name": "body", "placeholder_idx": 0, "kind": "text", "required": True},
                    {"name": "body", "placeholder_idx": 1, "kind": "bullets", "required": False},
                ],
            }
        },
    }
    p = tmp_path / "dup.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"duplicate.*body|body.*duplicate"):
        load_manifest(p)


# ---------------------------------------------------------------------------
# load_manifest — other malformed inputs
# ---------------------------------------------------------------------------

def test_missing_required_key_raises(tmp_path):
    data = {"name": "x", "type": "pptx", "template_file": "x.pptx"}
    p = tmp_path / "missing.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"validation failed|description|slide_types"):
        load_manifest(p)


def test_wrong_type_value_raises(tmp_path):
    data = {
        "name": "x",
        "type": "docx",
        "template_file": "x.pptx",
        "description": "d",
        "slide_types": {},
    }
    p = tmp_path / "wrong_type.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"validation failed|type"):
        load_manifest(p)


def test_invalid_yaml_raises(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("{ unclosed: [bracket", encoding="utf-8")
    with pytest.raises(ValueError, match=r"not valid YAML|YAML"):
        load_manifest(p)


def test_non_mapping_yaml_raises(tmp_path):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"mapping"):
        load_manifest(p)


def test_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_manifest(tmp_path / "nonexistent.yaml")


def test_negative_max_chars_raises(tmp_path):
    data = {
        "name": "x",
        "type": "pptx",
        "template_file": "x.pptx",
        "description": "d",
        "slide_types": {
            "s": {
                "layout_index": 0,
                "fields": [
                    {"name": "t", "placeholder_idx": 0, "kind": "text",
                     "required": True, "max_chars": -1},
                ],
            }
        },
    }
    p = tmp_path / "neg_chars.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(p)


def test_zero_max_items_raises(tmp_path):
    data = {
        "name": "x",
        "type": "pptx",
        "template_file": "x.pptx",
        "description": "d",
        "slide_types": {
            "s": {
                "layout_index": 0,
                "fields": [
                    {"name": "b", "placeholder_idx": 1, "kind": "bullets",
                     "required": False, "max_items": 0},
                ],
            }
        },
    }
    p = tmp_path / "zero_items.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(p)


# ---------------------------------------------------------------------------
# lint_manifest
# ---------------------------------------------------------------------------

def test_lint_clean_manifest():
    m = load_manifest(FIXTURES / "valid_manifest.yaml")
    assert lint_manifest(m) == []


def test_lint_warns_no_slide_types():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={},
    )
    warnings = lint_manifest(m)
    assert any("no slide types" in w for w in warnings)


def test_lint_warns_empty_fields():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={
            "empty": SlideTypeDef(layout_index=0, fields=[]),
        },
    )
    warnings = lint_manifest(m)
    assert any("empty" in w and "no fields" in w for w in warnings)


def test_lint_warns_max_chars_on_image():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={
            "s": SlideTypeDef(
                layout_index=0,
                fields=[FieldDef(name="img", placeholder_idx=10, kind="image",
                                 required=False, max_chars=200)],
            )
        },
    )
    warnings = lint_manifest(m)
    assert any("max_chars" in w and "img" in w for w in warnings)


def test_lint_warns_max_items_on_text():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={
            "s": SlideTypeDef(
                layout_index=0,
                fields=[FieldDef(name="heading", placeholder_idx=0, kind="text",
                                 required=True, max_items=5)],
            )
        },
    )
    warnings = lint_manifest(m)
    assert any("max_items" in w and "heading" in w for w in warnings)


def test_lint_warns_max_items_on_image():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={
            "s": SlideTypeDef(
                layout_index=0,
                fields=[FieldDef(name="img", placeholder_idx=10, kind="image",
                                 required=False, max_items=3)],
            )
        },
    )
    warnings = lint_manifest(m)
    assert any("max_items" in w and "img" in w for w in warnings)


def test_lint_no_warnings_for_valid_constraints():
    m = Manifest(
        name="x",
        type="pptx",
        template_file="x.pptx",
        description="d",
        slide_types={
            "s": SlideTypeDef(
                layout_index=0,
                fields=[
                    FieldDef(name="t", placeholder_idx=0, kind="text", required=True, max_chars=80),
                    FieldDef(name="b", placeholder_idx=1, kind="bullets", required=False, max_items=6),
                ],
            )
        },
    )
    assert lint_manifest(m) == []
