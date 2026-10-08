"""Scoring is independent of grounding and expected labels never affect flags."""
from datetime import date

import pytest


@pytest.mark.parametrize("correct,wrong,passed", [
    (199, 1, True), (198, 2, True), (197, 3, False), (190, 2, True), (189, 0, False),
])
def test_quality_boundaries(correct, wrong, passed):
    from scripts.evaluate_extraction import passes_quality_gate
    assert passes_quality_gate(correct, wrong, 200) is passed


def test_real_quote_in_wrong_column_is_counted_unflagged():
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit
    from scripts.evaluate_extraction import ExpectedField, ScoredField, score_results

    unit = SourceUnit("invoice#p:0", "Invoice date: 15 March 2026", "paragraph", 0)
    field = validate_field(FieldProposal("15 March 2026", unit.text, unit.anchor),
                           ColumnSpec("due_date", "Due date", "", "date"),
                           {unit.anchor: unit})
    assert not field.flagged
    report = score_results({("invoice", "due_date"): ScoredField(field.data_value, False)},
                           {("invoice", "due_date"): ExpectedField(date(2026, 4, 15), "date")})
    assert report.correct == 0
    assert report.unflagged_wrong == 1


def test_missing_slots_and_correct_flag_review_burden():
    from scripts.evaluate_extraction import ExpectedField, ScoredField, score_results
    labels = {("one", "id"): ExpectedField("00123", "text"),
              ("two", "id"): ExpectedField("00456", "text")}
    report = score_results({("one", "id"): ScoredField("00123", True)}, labels)
    assert report.total == 2 and report.correct == 1
    assert report.unflagged_wrong == 0
    assert report.flagged_correct == 1
    assert report.flag_rate_correct == 1.0


def test_response_schema_keeps_all_values_as_literal_strings():
    from extraction.models import ColumnSpec, build_response_schema
    schema = build_response_schema((ColumnSpec("amount", "Amount", "", "decimal"),),
                                   ("one",))
    field = schema["properties"]["records"]["items"]["properties"]["fields"]
    assert field["required"] == ["amount"]
    assert field["properties"]["amount"]["properties"]["value"]["type"] == ["string", "null"]


def test_direct_call_sends_whole_file_schema_and_thinking_off(monkeypatch, tmp_path):
    from extraction.models import ColumnSpec, SourceDocument, SourceUnit
    from scripts.evaluate_extraction import call_ollama

    class FakeSession:
        trust_env = True
        body = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json, timeout):
            self.body = json
            class Response:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"response": '{"records": []}'}
            return Response()

    session = FakeSession()
    monkeypatch.setattr("scripts.evaluate_extraction.requests.Session", lambda: session)
    source = SourceDocument("one", tmp_path / "source.docx", "source.docx", (
        SourceUnit("one#p:0", "BEGIN Total: USD 12,500.00", "paragraph", 0),
        SourceUnit("one#p:1", "END-OF-SOURCE", "paragraph", 1),
    ), 1)
    call_ollama("http://localhost:11434", "model", source,
                (ColumnSpec("total", "Total", "", "decimal"),), {"num_ctx": 16384})
    assert not session.trust_env
    assert session.body["think"] is False and session.body["stream"] is False
    assert "BEGIN" in session.body["prompt"] and "END-OF-SOURCE" in session.body["prompt"]
    assert isinstance(session.body["format"], dict)
    assert "labels" not in session.body["prompt"]


def test_remote_transport_is_rejected_before_a_request(tmp_path):
    from extraction.models import SourceDocument
    from scripts.evaluate_extraction import EvaluationError, call_ollama
    with pytest.raises(EvaluationError, match="loopback"):
        call_ollama("https://remote.example", "model",
                    SourceDocument("one", tmp_path / "source.docx", "source", (), 1), (), {})


def test_invalid_output_retains_every_field(tmp_path):
    from extraction.models import ColumnSpec, SourceDocument
    from scripts.evaluate_extraction import parse_fields
    source = SourceDocument("one", tmp_path / "source.docx", "source", (), 1)
    columns = (ColumnSpec("id", "ID", ""), ColumnSpec("total", "Total", "", "decimal"))
    for output in ["not JSON", '{"records": []}', '{"records":[{"record_id":"other","fields":{}}]}']:
        fields = parse_fields(output, source, columns)
        assert set(fields) == {"id", "total"}
        assert all(f.flagged for f in fields.values())


def test_invalid_evidence_keeps_identifiable_proposed_value(tmp_path):
    import json
    from extraction.models import ColumnSpec, SourceDocument
    from scripts.evaluate_extraction import parse_fields

    output = json.dumps({"records": [{"record_id": "one", "fields": {
        "id": {"value": "00123", "quote": None, "anchor": "one#p:0"}
    }}]})
    fields = parse_fields(output, SourceDocument("one", tmp_path / "a.docx", "a", (), 1),
                           (ColumnSpec("id", "ID", ""),))
    assert fields["id"].flagged
    assert fields["id"].data_value == "00123"


@pytest.mark.parametrize("extra_location", ["root", "record", "fields"])
def test_extra_schema_properties_flag_but_retain_known_proposal(tmp_path, extra_location):
    import json
    from extraction.models import ColumnSpec, SourceDocument, SourceUnit
    from scripts.evaluate_extraction import parse_fields
    payload = {"records": [{"record_id": "one", "fields": {
        "id": {"value": "00123", "quote": "ID 00123", "anchor": "one#p:0"}
    }}]}
    target = payload if extra_location == "root" else payload["records"][0]
    if extra_location == "fields":
        target = target["fields"]
    target["unexpected"] = "extra"
    source = SourceDocument("one", tmp_path / "a.docx", "a", (
        SourceUnit("one#p:0", "ID 00123", "paragraph", 0),
    ), 1)
    result = parse_fields(json.dumps(payload), source, (ColumnSpec("id", "ID", ""),))["id"]
    assert result.flagged
    assert result.data_value == "00123"
