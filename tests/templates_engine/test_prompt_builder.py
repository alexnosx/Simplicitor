# tests/templates_engine/test_prompt_builder.py
# Phase I: Tests for the prompt builder.
from pathlib import Path
import pytest
from templates_engine.manifest import load_manifest
from templates_engine.prompt_builder import build_prompt, build_repair_prompt

FIXTURE_MANIFEST = Path(__file__).parent / "fixtures" / "render_manifest.yaml"

@pytest.fixture
def manifest():
    return load_manifest(FIXTURE_MANIFEST)


def test_build_prompt_returns_four_messages(manifest):
    messages = build_prompt(manifest, "Make a deck about dogs.")
    assert len(messages) == 4
    assert all("role" in m and "content" in m for m in messages)


def test_build_prompt_message_roles_in_order(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    roles = [m["role"] for m in messages]
    assert roles == ["system", "user", "assistant", "user"]


def test_build_prompt_system_message_contains_all_slide_types(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    system = messages[0]["content"]
    for slide_type in manifest.slide_types:
        assert slide_type in system


def test_build_prompt_system_message_contains_field_names(manifest):
    messages = build_prompt(manifest, "Make a deck.")
    system = messages[0]["content"]
    # All field names from all slide types must appear in the schema block
    for slide_def in manifest.slide_types.values():
        for field in slide_def.fields:
            assert field.name in system


def test_build_prompt_one_shot_assistant_uses_manifest_field_names(manifest):
    """One-shot example must use actual manifest field names, not hardcoded strings."""
    messages = build_prompt(manifest, "Make a deck.")
    assistant_content = messages[2]["content"]
    # The assistant one-shot response is JSON; all required field names must appear
    import json
    data = json.loads(assistant_content)
    assert "slides" in data
    for slide in data["slides"]:
        assert "type" in slide
        assert "fields" in slide
        slide_type = slide["type"]
        assert slide_type in manifest.slide_types
        slide_def = manifest.slide_types[slide_type]
        # Every key in the example's fields must be a real field name from the manifest
        manifest_field_names = {f.name for f in slide_def.fields}
        for key in slide["fields"]:
            assert key in manifest_field_names, f"Unknown field '{key}' in one-shot example for slide type '{slide_type}'"
        # All required fields must be present — guards against silent omission on unknown kinds
        required_names = {f.name for f in slide_def.fields if f.required}
        assert required_names == set(slide["fields"].keys()), (
            f"Required fields mismatch for '{slide_type}': "
            f"expected {required_names}, got {set(slide['fields'].keys())}"
        )


def test_build_prompt_last_message_contains_user_request(manifest):
    request = "Build a deck about quarterly results"
    messages = build_prompt(manifest, request)
    assert request in messages[-1]["content"]


def test_build_prompt_includes_source_text_when_provided(manifest):
    messages = build_prompt(manifest, "Summarise this.", source_text="Q3 revenue was $4.2M.")
    assert "Q3 revenue was $4.2M." in messages[-1]["content"]


def test_build_prompt_omits_source_section_when_none(manifest):
    messages = build_prompt(manifest, "Make a deck.", source_text=None)
    assert "Source content:" not in messages[-1]["content"]


# ---------------------------------------------------------------------------
# build_repair_prompt
# ---------------------------------------------------------------------------

def test_build_repair_prompt_appends_two_messages(manifest):
    original = build_prompt(manifest, "Make a deck.")
    result = build_repair_prompt(original, "not json")
    assert len(result) == len(original) + 2
    assert result[-2]["role"] == "assistant"
    assert result[-1]["role"] == "user"


def test_build_repair_prompt_parse_failure_instruction(manifest):
    original = build_prompt(manifest, "Make a deck.")
    result = build_repair_prompt(original, "not json", errors=None)
    correction = result[-1]["content"]
    assert "could not be parsed" in correction
    assert "no prose" in correction.lower()
    assert "no markdown fences" in correction.lower()


def test_build_repair_prompt_validation_failure_contains_error_strings(manifest):
    original = build_prompt(manifest, "Make a deck.")
    errors = ["slides[0].fields.title: Field required."]
    result = build_repair_prompt(original, '{"slides": []}', errors=errors)
    correction = result[-1]["content"]
    assert "slides[0].fields.title: Field required." in correction
    assert "Fix only the fields" in correction
