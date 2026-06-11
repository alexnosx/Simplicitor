# tests/templates_engine/test_validation.py
# Phase C: Tests for content model generation and validation.
from pathlib import Path

import pytest
from pydantic import BaseModel

from templates_engine.manifest import load_manifest
from templates_engine.validation import (
    build_content_model,
    format_validation_errors,
    validate_content,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def manifest():
    return load_manifest(FIXTURES / "valid_manifest.yaml")


# ---------------------------------------------------------------------------
# build_content_model
# ---------------------------------------------------------------------------

def test_build_content_model_returns_basemodel_subclass(manifest):
    model = build_content_model(manifest)
    assert issubclass(model, BaseModel)


def test_build_content_model_accepts_valid_structure(manifest):
    model = build_content_model(manifest)
    instance = model(slides=[{"type": "title", "fields": {"title": "X"}}])
    assert len(instance.slides) == 1
    assert instance.slides[0].type == "title"


def test_build_content_model_rejects_missing_slides(manifest):
    model = build_content_model(manifest)
    with pytest.raises(Exception):
        model(no_slides=[])


# ---------------------------------------------------------------------------
# validate_content — success paths
# ---------------------------------------------------------------------------

def test_valid_content_returns_true(manifest):
    content = {
        "slides": [
            {"type": "title", "fields": {"title": "My Deck", "subtitle": "Sub"}},
            {"type": "content", "fields": {"heading": "Intro", "body": ["A", "B"]}},
        ]
    }
    ok, result = validate_content(manifest, content)
    assert ok is True


def test_valid_content_parsed_structure(manifest):
    content = {
        "slides": [
            {"type": "title", "fields": {"title": "My Deck", "subtitle": "Sub"}},
        ]
    }
    ok, result = validate_content(manifest, content)
    assert ok is True
    assert "slides" in result
    assert result["slides"][0]["type"] == "title"
    assert result["slides"][0]["fields"]["title"] == "My Deck"


def test_optional_field_omitted_succeeds(manifest):
    # subtitle is optional in title slide
    content = {"slides": [{"type": "title", "fields": {"title": "Only title"}}]}
    ok, result = validate_content(manifest, content)
    assert ok is True


def test_optional_bullets_omitted_defaults_to_empty(manifest):
    # body is optional in content slide
    content = {"slides": [{"type": "content", "fields": {"heading": "Section"}}]}
    ok, result = validate_content(manifest, content)
    assert ok is True
    assert result["slides"][0]["fields"]["body"] == []


def test_all_slide_types_validate(manifest):
    content = {
        "slides": [
            {"type": "title", "fields": {"title": "Title"}},
            {"type": "content", "fields": {"heading": "H", "body": ["x"]}},
            {"type": "photo", "fields": {"heading": "Photo"}},
        ]
    }
    ok, _ = validate_content(manifest, content)
    assert ok is True


def test_empty_slides_list_validates(manifest):
    ok, result = validate_content(manifest, {"slides": []})
    assert ok is True
    assert result["slides"] == []


# ---------------------------------------------------------------------------
# validate_content — missing required field
# ---------------------------------------------------------------------------

def test_missing_required_field_returns_false(manifest):
    # heading is required in content slide
    content = {"slides": [{"type": "content", "fields": {"body": ["A"]}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False


def test_missing_required_field_names_field(manifest):
    content = {"slides": [{"type": "content", "fields": {"body": ["A"]}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("heading" in e for e in errors), f"Expected 'heading' in errors: {errors}"


def test_missing_required_title_names_field(manifest):
    content = {"slides": [{"type": "title", "fields": {"subtitle": "sub"}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("title" in e for e in errors), f"Expected 'title' in errors: {errors}"


# ---------------------------------------------------------------------------
# validate_content — unknown slide type
# ---------------------------------------------------------------------------

def test_unknown_slide_type_returns_false(manifest):
    content = {"slides": [{"type": "nonexistent", "fields": {"title": "X"}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False


def test_unknown_slide_type_names_the_type(manifest):
    content = {"slides": [{"type": "mystery_layout", "fields": {}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("mystery_layout" in e for e in errors), f"Expected type name in errors: {errors}"


# ---------------------------------------------------------------------------
# validate_content — non-string slide type (unhashable: must collect, not raise)
# ---------------------------------------------------------------------------

def test_list_slide_type_collected_as_error_not_raised(manifest):
    content = {"slides": [{"type": ["content"], "fields": {}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert errors
    assert any("slides[0].type" in e for e in errors), \
        f"Expected 'slides[0].type' in errors: {errors}"


def test_dict_slide_type_collected_as_error_not_raised(manifest):
    content = {"slides": [{"type": {"name": "content"}, "fields": {}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("slides[0].type" in e for e in errors), \
        f"Expected 'slides[0].type' in errors: {errors}"


# ---------------------------------------------------------------------------
# validate_content — too many bullets (max_items)
# ---------------------------------------------------------------------------

def test_too_many_bullets_returns_false(manifest):
    # max_items is 8 for content.body
    content = {
        "slides": [{
            "type": "content",
            "fields": {"heading": "S", "body": [f"Item {i}" for i in range(9)]}
        }]
    }
    ok, errors = validate_content(manifest, content)
    assert ok is False


def test_too_many_bullets_names_the_field(manifest):
    content = {
        "slides": [{
            "type": "content",
            "fields": {"heading": "S", "body": [f"Item {i}" for i in range(9)]}
        }]
    }
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("body" in e for e in errors), f"Expected 'body' in errors: {errors}"


def test_exactly_max_bullets_validates(manifest):
    # Exactly 8 items should pass
    content = {
        "slides": [{
            "type": "content",
            "fields": {"heading": "S", "body": [f"Item {i}" for i in range(8)]}
        }]
    }
    ok, _ = validate_content(manifest, content)
    assert ok is True


# ---------------------------------------------------------------------------
# validate_content — oversize text (max_chars)
# ---------------------------------------------------------------------------

def test_oversize_text_returns_false(manifest):
    # max_chars is 100 for title.title
    content = {"slides": [{"type": "title", "fields": {"title": "x" * 101}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False


def test_oversize_text_names_the_field(manifest):
    content = {"slides": [{"type": "title", "fields": {"title": "x" * 101}}]}
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert any("title" in e for e in errors), f"Expected 'title' in errors: {errors}"


def test_exactly_max_chars_validates(manifest):
    # Exactly 100 chars should pass
    content = {"slides": [{"type": "title", "fields": {"title": "x" * 100}}]}
    ok, _ = validate_content(manifest, content)
    assert ok is True


# ---------------------------------------------------------------------------
# validate_content — structural errors
# ---------------------------------------------------------------------------

def test_non_object_content_fails(manifest):
    ok, errors = validate_content(manifest, ["not", "a", "dict"])
    assert ok is False


def test_missing_slides_key_fails(manifest):
    ok, errors = validate_content(manifest, {"data": []})
    assert ok is False
    assert any("slides" in e for e in errors)


def test_slides_not_a_list_fails(manifest):
    ok, errors = validate_content(manifest, {"slides": "not a list"})
    assert ok is False


def test_slide_not_an_object_fails(manifest):
    ok, errors = validate_content(manifest, {"slides": ["string item"]})
    assert ok is False


def test_slide_missing_type_fails(manifest):
    ok, errors = validate_content(manifest, {"slides": [{"fields": {}}]})
    assert ok is False
    assert any("type" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_content — all errors collected
# ---------------------------------------------------------------------------

def test_multiple_bad_slides_all_errors_returned(manifest):
    content = {
        "slides": [
            {"type": "bad_type_1", "fields": {}},
            {"type": "bad_type_2", "fields": {}},
            {"type": "content", "fields": {}},  # missing required heading
        ]
    }
    ok, errors = validate_content(manifest, content)
    assert ok is False
    assert len(errors) >= 3


# ---------------------------------------------------------------------------
# format_validation_errors
# ---------------------------------------------------------------------------

def test_format_errors_is_string(manifest):
    content = {"slides": [{"type": "bad", "fields": {}}]}
    _, errors = validate_content(manifest, content)
    result = format_validation_errors(errors)
    assert isinstance(result, str)


def test_format_errors_numbered(manifest):
    content = {
        "slides": [
            {"type": "bad_1", "fields": {}},
            {"type": "bad_2", "fields": {}},
        ]
    }
    _, errors = validate_content(manifest, content)
    formatted = format_validation_errors(errors)
    assert "1." in formatted
    assert "2." in formatted


def test_format_errors_includes_count(manifest):
    content = {"slides": [{"type": "bad", "fields": {}}]}
    _, errors = validate_content(manifest, content)
    formatted = format_validation_errors(errors)
    assert "1 error" in formatted


def test_format_errors_mentions_problem(manifest):
    content = {"slides": [{"type": "content", "fields": {}}]}  # missing heading
    _, errors = validate_content(manifest, content)
    formatted = format_validation_errors(errors)
    assert "heading" in formatted
