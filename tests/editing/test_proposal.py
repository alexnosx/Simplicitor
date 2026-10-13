"""Request payload, budget, alignment and validation of the model reply."""
import json
from threading import Event

import pytest

from app.services.ollama_client import OllamaConnectionError, OllamaOutputLimitError
from editing import proposal
from editing.models import EditError
from editing.package import open_document
from tests.editing.docx_builder import p


def reply(*texts) -> str:
    return json.dumps({"paragraphs": list(texts)})


@pytest.mark.parametrize("raw", [
    "not json", "{}", '{"paragraphs": "x"}', json.dumps({"paragraphs": [1]}),
    json.dumps({"paragraphs": [{"text": "x"}]}), reply(), reply("bad\x01"),
    '{"paragraphs": ["bad\\ud800"]}', '{"paragraphs": ["x"], "extra": 1}', '["x"]',
])
def test_unusable_replies_are_rejected(raw):
    with pytest.raises(EditError, match="did not return a usable change"):
        proposal.validate(raw, ["One", "Two"], [False, False])


def test_valid_reply_normalizes_line_endings_only():
    result = proposal.validate(reply("A\r\nB\t\n", "", "C\rD"), ["One", "Two"], [False, False], 3)
    assert [x.text for x in result.paragraphs] == ["A\nB\t\n", "", "C\nD"]
    assert result.attempt == 3


def test_original_trailing_tab_break_and_spaces_are_kept():
    originals = ["Name\t", "Line\n", "Spaced  ", "Pay in 30 days."]
    result = proposal.validate(reply("Name\t", "Line\n", "Spaced  ", "Pay in 45 days."),
                               originals, [False] * 4)
    assert [x.text for x in result.paragraphs] == ["Name\t", "Line\n", "Spaced  ", "Pay in 45 days."]
    assert [x.source for x in result.paragraphs] == [0, 1, 2, 3]


def test_all_blank_output_is_rejected_unless_the_selection_was_blank():
    with pytest.raises(EditError, match="usable change"):
        proposal.validate(reply("  "), ["One", "Two"], [False, False])
    assert proposal.validate(reply("Filled"), [""], [False]).paragraphs[0].text == "Filled"


def test_no_change_is_reported():
    with pytest.raises(EditError, match="proposed no change"):
        proposal.validate(reply("One", "Two"), ["One", "Two"], [False, False])


def test_too_many_output_paragraphs_are_rejected():
    with pytest.raises(EditError, match="usable change"):
        proposal.validate(reply(*["x"] * 22), ["One"], [False])


@pytest.mark.parametrize("originals, outputs, sources", [
    (["A b c", "D e f"], ["A b C", "D e F"], [0, 1]),
    (["Report with actions.", "Review meeting."],
     ["Report with actions.", "Review meeting.", "Final presentation."], [0, 1, 1]),
    (["Heading", "Body text here."], ["Heading", "New intro line.", "Body text here."], [0, 0, 1]),
    (["Short report.", "Draft in two weeks."], ["Short report and draft in two weeks."], [1]),
    (["Alpha beta gamma."], ["Alpha beta.", "Gamma."], [0, 0]),
    (["Alpha heading", "Body one", "Body two"], ["Body one", "Alpha heading", "Body two"], None),
    (["Alpha heading", "Body one", "Body two"], ["Body one", "Alpha heading", "Body two", "Added"], None),
    (["Alpha heading", "Body one"], ["Alpha heading", "Body one, longer.", "Added"], [0, 1, 1]),
])
def test_alignment_is_monotonic_and_follows_word_similarity(originals, outputs, sources):
    assert proposal.align(originals, outputs) == sources


def test_dropping_a_paragraph_with_bookmarks_is_rejected():
    with pytest.raises(EditError, match="usable change"):
        proposal.validate(reply("Body text, rewritten."), ["Heading", "Body text."], [True, False])
    kept = proposal.validate(reply("Body text, rewritten."), ["Heading", "Body text."], [False, True])
    assert [x.source for x in kept.paragraphs] == [1]


def test_request_contains_styles_and_instruction_but_no_other_text(make_docx):
    opened = open_document(make_docx(p("Before") + p("Chosen") + p("After")))
    payload = json.loads(proposal.build_request(opened, 1, 1, "Make it formal.", {1: "Heading 2"}))
    assert payload == {"paragraphs": [{"style": "Heading 2", "text": "Chosen"}],
                       "instruction": "Make it formal."}


def test_metadata_heavy_core_is_refused_at_normal_settings(make_docx):
    opened = open_document(make_docx(p("Example") + "<w:p/>" * 1999))
    with pytest.raises(EditError, match="request is too long"):
        proposal.build_request(opened, 0, 1999, "Shorten.", {i: "Normal" for i in range(2000)})


def test_schema_bounds_count_and_requires_strings():
    items = proposal.response_schema(3)["properties"]["paragraphs"]
    assert items["maxItems"] == 23 and items["items"] == {"type": "string"}


class FakeClient:
    def __init__(self, answer=None, error=None, on_call=None):
        self.answer, self.error, self.on_call, self.calls = answer, error, on_call, []

    def generate(self, model, prompt, system, output_format=None, timeout=None, **kwargs):
        self.calls.append((model, prompt, system, output_format, timeout, kwargs))
        if self.on_call:
            self.on_call()
        if self.error:
            raise self.error
        return self.answer


def test_request_change_uses_local_settings_and_attempt_seed(make_docx):
    opened = open_document(make_docx(p("Pay in 30 days.")))
    client = FakeClient(reply("Pay in 45 days."))
    result = proposal.request_change(opened, 0, 0, "Use 45 days.", {}, "model:8b", 2, client, Event())
    assert result.paragraphs[0].text == "Pay in 45 days." and result.attempt == 2
    _, _, system, schema, timeout, kwargs = client.calls[0]
    assert system == proposal.SYSTEM_PROMPT and timeout == 180
    assert kwargs["options"] == {"num_ctx": 16384, "num_predict": 4096, "temperature": 0.3, "seed": 2}
    assert kwargs["think"] is False and kwargs["local_only"] is True
    assert schema == proposal.response_schema(1)


def test_request_change_errors_and_cancellation(make_docx):
    opened = open_document(make_docx(p("Text.")))
    with pytest.raises(EditError, match="too long for one request"):
        proposal.request_change(opened, 0, 0, "x", {}, "m", 0, FakeClient(error=OllamaOutputLimitError("")), Event())
    with pytest.raises(EditError, match="Could not reach the local AI"):
        proposal.request_change(opened, 0, 0, "x", {}, "m", 0, FakeClient(error=OllamaConnectionError("down")), Event())
    cancel = Event()
    cancel.set()
    client = FakeClient(reply("New."))
    with pytest.raises(proposal.EditCancelled):
        proposal.request_change(opened, 0, 0, "x", {}, "m", 0, client, cancel)
    assert client.calls == []
    late = Event()
    with pytest.raises(proposal.EditCancelled):
        proposal.request_change(opened, 0, 0, "x", {}, "m", 0, FakeClient(reply("New."), on_call=late.set), late)


@pytest.mark.parametrize("outputs", [
    ["Body one", "Alpha heading", "Body two"],
    ["Body one", "Alpha heading", "Body two", "Added"],
    ["Body one, edited.", "Alpha heading, edited.", "Body two"],
])
def test_reordering_a_bookmarked_paragraph_is_rejected(outputs):
    originals = ["Alpha heading", "Body one", "Body two"]
    with pytest.raises(EditError, match="usable change"):
        proposal.validate(reply(*outputs), originals, [True, False, False])


@pytest.mark.parametrize("outputs, sources", [
    (["Alpha heading renamed", "Body one", "Body two"], [0, 1, 2]),
    (["Alpha heading", "Body one", "An inserted body line.", "Body two"], [0, 1, 1, 2]),
    (["Alpha heading", "Body one and body two."], [0, 1]),
])
def test_intended_edits_keep_the_bookmark_on_its_heading(outputs, sources):
    result = proposal.validate(reply(*outputs), ["Alpha heading", "Body one", "Body two"],
                               [True, False, False])
    assert [x.source for x in result.paragraphs] == sources


def test_splitting_a_bookmarked_paragraph_keeps_the_bookmark_on_the_first_part():
    original = "Pay in 30 days. Keep feedback concise and specific for the final report."
    result = proposal.validate(
        reply("Pay in 45 days.", "Keep feedback concise and specific for the final report."),
        [original], [True])
    assert [x.source for x in result.paragraphs] == [0, 0]


def test_identical_original_paragraphs_do_not_count_as_a_moved_bookmark():
    result = proposal.validate(reply("Payment schedule", "Payment terms"),
                               ["Payment terms", "Payment terms"], [True, False])
    assert [x.source for x in result.paragraphs] == [0, 1]
