"""Production extraction keeps the roster, evidence, coverage, and cancellation contract."""
import json
from math import ceil
from pathlib import Path
from threading import Event

import pytest

from extraction.models import ColumnSpec, SourceDocument, SourceUnit


def document(texts, source_id="one"):
    return SourceDocument(source_id, Path(source_id + ".docx"), "same.docx", tuple(
        SourceUnit(f"{source_id}#p:{i}", text, "paragraph", i) for i, text in enumerate(texts)
    ), 1)


def profile(context=16384):
    from extraction.models import ExtractionProfile
    return ExtractionProfile("qwen", {"num_ctx": context, "num_predict": 256}, 180)


def reply(source_id, fields):
    return json.dumps({"records": [{"record_id": source_id, "fields": {
        field: {"value": value, "quote": quote, "anchor": anchor}
        for field, (value, quote, anchor) in fields.items()
    }}]})


class Client:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []

    def generate(self, model, prompt, system, **kwargs):
        self.calls.append({"model": model, "prompt": prompt, "system": system, **kwargs})
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        if callable(output):
            return output(self.calls[-1])
        return output


def test_small_files_use_one_complete_request_each_and_keep_distinct_records():
    from extraction.pipeline import extract
    docs = (document(["ID 00123", "Tail"], "one"), document(["ID 00456"], "two"))
    columns = (ColumnSpec("id", "ID", "Identifier"),)
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")}),
                     reply("two", {"id": ("00456", "ID 00456", "two#p:0")})])
    result = extract(docs, columns, "Extract IDs", profile(), client, Event())
    assert result.ordered_source_ids == ("one", "two")
    assert result.fields[("one", "id")].data_value == "00123"
    assert result.fields[("two", "id")].data_value == "00456"
    assert result.source_paths == {"one": Path("one.docx"), "two": Path("two.docx")}
    assert set(result.coverage.values()) == {"processed"}
    assert len(client.calls) == 2
    assert "Tail" in client.calls[0]["prompt"]
    assert all(c["think"] is False and c["local_only"] is True for c in client.calls)
    assert all(c["timeout"] == 180 and isinstance(c["output_format"], dict) for c in client.calls)


def test_columns_come_from_first_source_with_types_and_english_defaults():
    from extraction.pipeline import propose_columns, ambiguous_date_columns
    doc = document(["Gross total USD 12,500.00 due 15 March 2026."])
    client = Client([json.dumps({"columns": [
        {"label": "Total", "description": "Amount payable", "kind": "decimal"},
        {"label": "Due date", "description": "Final payment date", "kind": "date"},
        {"label": "Reference", "description": "Reference", "kind": "unknown"},
    ]})])
    columns = propose_columns("Extract the amount and due date", doc, profile(), client, Event())
    assert [c.kind for c in columns] == ["decimal", "date", "text"]
    assert len({c.id for c in columns}) == 3
    assert columns[0].thousands_separator == "," and columns[0].decimal_separator == "."
    assert columns[1].date_order is None
    assert ambiguous_date_columns((doc,), columns) == ()
    assert "Gross total" in client.calls[0]["prompt"]
    assert client.calls[0]["think"] is False and client.calls[0]["local_only"] is True


@pytest.mark.parametrize("output", ["invalid", '{"columns": []}', '{"columns":[{"label":""}]}'])
def test_failed_column_suggestion_leaves_inputs_available_for_manual_recovery(output):
    from extraction.pipeline import ExtractionError, propose_columns
    doc = document(["Invoice text"])
    before = doc.units
    with pytest.raises(ExtractionError):
        propose_columns("Extract details", doc, profile(), Client([output]), Event())
    assert doc.units == before


def test_numeric_date_order_is_required_only_for_ambiguous_source_dates():
    from extraction.pipeline import ExtractionError, ambiguous_date_columns, extract
    columns = (ColumnSpec("date", "Date", "", "date"), ColumnSpec("id", "ID", ""))
    assert ambiguous_date_columns((document(["Due 01/02/2026"]),), columns) == ("date",)
    assert ambiguous_date_columns((document(["Due 15/02/2026"]),), columns) == ()
    assert ambiguous_date_columns((document(["Due 02/02/2026"]),), columns) == ()
    client = Client([])
    with pytest.raises(ExtractionError, match="order"):
        extract((document(["Due 01/02/2026"]),), columns, "", profile(), client, Event())
    assert not client.calls
    confirmed = (ColumnSpec("date", "Date", "", "date", date_order="DMY"),)
    assert ambiguous_date_columns((document(["Due 01/02/2026"]),), confirmed) == ()


@pytest.mark.parametrize("response", ["bad JSON", reply("other", {}), reply("one", {})])
def test_bad_or_missing_model_fields_never_remove_requested_rows_and_columns(response):
    from extraction.pipeline import extract
    columns = (ColumnSpec("id", "ID", ""), ColumnSpec("total", "Total", "", "decimal"))
    result = extract((document(["Some facts"]),), columns, "", profile(), Client([response]), Event())
    assert set(result.fields) == {("one", "id"), ("one", "total")}
    assert all(f.flagged for f in result.fields.values())


def test_wrong_evidence_keeps_the_literal_proposal_flagged():
    from extraction.pipeline import extract
    output = reply("one", {"id": ("00123", "ID 00123", "wrong#p:0")})
    result = extract((document(["ID 00123"]),), (ColumnSpec("id", "ID", ""),),
                     "", profile(), Client([output]), Event())
    field = result.fields[("one", "id")]
    assert field.flagged and field.data_value == "00123"


def test_sectioned_fields_accumulate_and_conflicting_quotes_remain_visible():
    from extraction.pipeline import extract
    docs = (document(["ID 00123 " + "a" * 1200, "ID 00456 " + "b" * 1200]),)
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")}),
                     reply("one", {"id": ("00456", "ID 00456", "one#p:1")})])
    result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600), client, Event())
    field = result.fields[("one", "id")]
    assert len(client.calls) == 2
    assert field.flagged and "conflict" in field.issues
    assert field.data_value == "00123"
    assert [p.value for p in field.alternatives] == ["00456"]
    assert "previous_fields" in client.calls[1]["prompt"]
    assert set(result.coverage.values()) == {"processed"}


def test_agreeing_section_evidence_is_retained_and_null_does_not_erase_a_value():
    from extraction.pipeline import extract
    docs = (document(["ID 00123 " + "a" * 1200, "ID 00123 " + "b" * 1200,
                      "No identifier here " + "c" * 1200]),)
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")}),
                     reply("one", {"id": ("00123", "ID 00123", "one#p:1")}),
                     reply("one", {"id": (None, "", "")})])
    result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600), client, Event())
    field = result.fields[("one", "id")]
    assert not field.flagged and field.data_value == "00123"
    assert [p.anchor for p in field.alternatives] == ["one#p:1"]


def test_oversized_unit_is_excluded_visibly_but_other_units_are_processed():
    from extraction.pipeline import extract
    docs = (document(["x" * 10000, "ID 00123"]),)
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:1")})])
    result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600), client, Event())
    assert result.coverage == {"one#p:0": "excluded", "one#p:1": "processed"}
    assert any(i.code == "oversized_unit" for i in result.issues)
    assert result.fields[("one", "id")].data_value == "00123"


def test_timeout_and_output_exhaustion_keep_roster_and_failed_coverage():
    from app.services.ollama_client import OllamaOutputLimitError, OllamaTimeoutError
    from extraction.pipeline import extract
    columns = (ColumnSpec("id", "ID", ""),)
    output = reply("one", {"id": ("00123", "ID 00123", "one#p:0")})
    for error in (OllamaTimeoutError("timed out"), OllamaOutputLimitError(output)):
        result = extract((document(["ID 00123"]),), columns, "", profile(), Client([error]), Event())
        assert set(result.fields) == {("one", "id")}
        assert result.fields[("one", "id")].flagged
        assert set(result.coverage.values()) == {"failed"}
        assert result.issues
        if isinstance(error, OllamaOutputLimitError):
            assert result.fields[("one", "id")].data_value == "00123"


def test_cancellation_before_request_and_after_late_response_returns_no_result():
    from extraction.pipeline import ExtractionCancelled, extract
    columns = (ColumnSpec("id", "ID", ""),)
    cancel = Event()
    cancel.set()
    client = Client([])
    with pytest.raises(ExtractionCancelled):
        extract((document(["ID 00123"]),), columns, "", profile(), client, cancel)
    assert not client.calls
    cancel.clear()
    def late_response(call):
        cancel.set()
        return reply("one", {"id": ("00123", "ID 00123", "one#p:0")})
    with pytest.raises(ExtractionCancelled):
        extract((document(["ID 00123"]),), columns, "", profile(), Client([late_response]), cancel)


def test_column_sample_is_leading_complete_units_and_explicitly_labelled():
    from extraction.pipeline import propose_columns
    doc = document(["FIRST " + "a" * 1000, "LAST " + "b" * 10000])
    client = Client(['{"columns":[{"label":"ID"}]}'])
    columns = propose_columns("Extract identifiers", doc, profile(1600), client, Event())
    payload = json.loads(client.calls[0]["prompt"])
    assert payload["sample"] is True
    assert [u["anchor"] for u in payload["source_units"]] == ["one#p:0"]
    assert "LAST" not in client.calls[0]["prompt"]
    assert columns[0].kind == "text"


def test_confirmed_number_overrides_are_used_without_changing_literal_evidence():
    from decimal import Decimal
    from extraction.pipeline import extract
    columns = (ColumnSpec("total", "Total", "", "decimal", ".", ","),)
    output = reply("one", {"total": ("EUR 2.400,00", "Total EUR 2.400,00", "one#p:0")})
    result = extract((document(["Total EUR 2.400,00"]),), columns, "", profile(), Client([output]), Event())
    field = result.fields[("one", "total")]
    assert not field.flagged and field.data_value == Decimal("2400.00")
    assert field.proposal.value == "EUR 2.400,00"


def test_carried_fields_are_rebudgeted_before_each_request():
    from extraction.pipeline import extract
    docs = (document(["Memo " + "X" * 3000, "ID 00123 " + "b" * 1000,
                      "Tail " + "c" * 1000]),)
    columns = (ColumnSpec("memo", "Memo", ""), ColumnSpec("id", "ID", ""))
    output = reply("one", {"memo": ("X" * 3000, "Memo " + "X" * 3000, "one#p:0"),
                           "id": (None, "", "")})
    client = Client([output])
    result = extract(docs, columns, "", profile(2400), client, Event())
    assert len(client.calls) == 1
    assert result.fields[("one", "memo")].data_value == "X" * 3000
    assert result.coverage == {"one#p:0": "processed", "one#p:1": "excluded", "one#p:2": "excluded"}
    for call in client.calls:
        input_bytes = sum(len(text.encode("utf-8")) for text in (
            call["system"], call["prompt"]))
        assert ceil(input_bytes / 2.5) + 256 + call["options"]["num_predict"] <= call["options"]["num_ctx"]


def test_cancellation_between_sections_makes_no_second_request():
    from extraction.pipeline import ExtractionCancelled, extract
    cancel = Event()
    docs = (document(["ID 00123 " + "a" * 1200, "ID 00456 " + "b" * 1200]),)
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")})])
    progress = []
    def on_progress(source_id, section_id, completed, total):
        progress.append((source_id, section_id, completed, total))
        cancel.set()
    with pytest.raises(ExtractionCancelled):
        extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600), client, cancel, on_progress)
    assert len(client.calls) == 1
    assert progress == [("one", "one:section:1", 1, 2)]


def test_source_coverage_issues_survive_a_successful_model_call():
    from dataclasses import replace
    from extraction.models import Issue
    from extraction.pipeline import extract
    issue = Issue("unsupported_structure", "one", "one#", "Embedded text needs review.")
    doc = replace(document(["ID 00123"]), issues=(issue,))
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")})])
    result = extract((doc,), (ColumnSpec("id", "ID", ""),), "", profile(), client, Event())
    assert issue in result.issues
    assert result.coverage == {"one#p:0": "processed"}


@pytest.mark.parametrize("bad_first", [False, True])
@pytest.mark.parametrize("bad_kind", ["malformed_null", "omitted_field"])
def test_section_schema_failure_cannot_disappear_behind_a_valid_value(bad_first, bad_kind):
    from extraction.pipeline import extract
    docs = (document(["ID 00123 " + "a" * 1200, "ID 00123 " + "b" * 1200]),)
    bad_index = 0 if bad_first else 1
    good_index = 1 - bad_index
    fields = {} if bad_kind == "omitted_field" else {
        "id": {"value": None, "quote": 42, "anchor": f"one#p:{bad_index}"}}
    bad = json.dumps({"records": [{"record_id": "one", "fields": fields}]})
    good = reply("one", {"id": ("00123", "ID 00123", f"one#p:{good_index}")})
    client = Client([bad, good] if bad_first else [good, bad])
    result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600), client, Event())
    field = result.fields[("one", "id")]
    assert field.data_value == "00123"
    assert field.flagged and "invalid_field_schema" in field.issues
    assert result.coverage[f"one#p:{bad_index}"] == "failed"
    assert result.coverage[f"one#p:{good_index}"] == "processed"
    assert any(i.code == "invalid_field_schema" for i in result.issues)


@pytest.mark.parametrize("last_pages,too_large", [(150, False), (151, True)])
def test_prepared_documents_still_obey_the_aggregate_job_page_limit(last_pages, too_large):
    from dataclasses import replace
    from extraction.pipeline import ExtractionError, extract

    docs = (replace(document(["ID 00123"], "one"), page_cost=150),
            replace(document(["ID 00456"], "two"), page_cost=last_pages))
    client = Client([reply("one", {"id": ("00123", "ID 00123", "one#p:0")}),
                     reply("two", {"id": ("00456", "ID 00456", "two#p:0")})])
    if too_large:
        with pytest.raises(ExtractionError, match="300"):
            extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(), client, Event())
        assert not client.calls
    else:
        result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(), client, Event())
        assert result.ordered_source_ids == ("one", "two")


def test_failed_grounding_alternative_cannot_demote_a_verified_value():
    from extraction.grounding import validate_field
    from extraction.models import FieldProposal
    from extraction.pipeline import _merge

    units = {"one#p:0": SourceUnit("one#p:0", "ID 00123", "paragraph", 0)}
    column = ColumnSpec("id", "ID", "")
    verified = validate_field(FieldProposal("00123", "ID 00123", "one#p:0"), column, units)
    failed = validate_field(FieldProposal("00456", "ID 00456", "one#p:0"), column, units)
    result = _merge(verified, failed)
    assert not result.flagged and result.data_value == "00123" and result.issues == ()
    assert result.alternatives == (failed.proposal,)


def test_two_verified_disagreeing_values_still_form_a_flagged_conflict():
    from extraction.grounding import validate_field
    from extraction.models import FieldProposal
    from extraction.pipeline import _merge

    unit = SourceUnit("one#p:0", "First ID 00123; second ID 00456", "paragraph", 0)
    column = ColumnSpec("id", "ID", "")
    first = validate_field(FieldProposal("00123", unit.text, unit.anchor), column, {unit.anchor: unit})
    second = validate_field(FieldProposal("00456", unit.text, unit.anchor), column, {unit.anchor: unit})
    result = _merge(first, second)
    assert result.flagged and "conflict" in result.issues
    assert result.data_value == "00123" and result.alternatives == (second.proposal,)


def test_truncated_extraction_flags_proposals_and_records_failed_coverage(monkeypatch):
    from app.services.ollama_client import OllamaClient
    from extraction.pipeline import extract

    output = reply("one", {"id": ("00123", "ID 00123", "one#p:0")})
    class Response:
        status_code = 200
        def json(self):
            return {"response": output, "prompt_eval_count": 16128, "done_reason": "stop"}
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr("app.services.ollama_client.requests.Session", Session)
    result = extract((document(["ID 00123"]),), (ColumnSpec("id", "ID", ""),),
                     "", profile(), OllamaClient("http://localhost:11434"), Event())
    field = result.fields[("one", "id")]
    assert field.flagged and field.data_value == "00123" and "context_truncated" in field.issues
    assert result.coverage == {"one#p:0": "failed"}
    assert any(i.code == "context_truncated" for i in result.issues)


def test_truncated_column_suggestion_fails_with_sample_coverage_issues(monkeypatch):
    from app.services.ollama_client import OllamaClient
    from extraction.pipeline import ExtractionError, propose_columns

    class Response:
        status_code = 200
        def json(self):
            return {"response": '{"columns":[{"label":"ID","kind":"text"}]}',
                    "prompt_eval_count": 16128, "done_reason": "stop"}
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr("app.services.ollama_client.requests.Session", Session)
    with pytest.raises(ExtractionError) as failure:
        propose_columns("Extract IDs", document(["ID 00123"]), profile(),
                        OllamaClient("http://localhost:11434"), Event())
    assert [(i.code, i.anchor) for i in failure.value.issues] == [("context_truncated", "one#p:0")]


def test_context_truncation_cannot_be_hidden_by_the_verified_value_merge_rule(monkeypatch):
    from app.services.ollama_client import OllamaClient
    from extraction.pipeline import extract

    docs = (document(["ID 00123 " + "a" * 1200, "Other details " + "b" * 1200]),)
    replies = iter([
        {"response": reply("one", {"id": ("00123", "ID 00123", "one#p:0")}),
         "prompt_eval_count": 500, "done_reason": "stop"},
        {"response": reply("one", {"id": ("00456", "ID 00456", "one#p:1")}),
         "prompt_eval_count": 1344, "done_reason": "stop"},
    ])
    class Response:
        status_code = 200
        def json(self):
            return next(replies)
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr("app.services.ollama_client.requests.Session", Session)
    result = extract(docs, (ColumnSpec("id", "ID", ""),), "", profile(1600),
                     OllamaClient("http://localhost:11434"), Event())
    assert result.fields[("one", "id")].flagged
    assert "context_truncated" in result.fields[("one", "id")].issues
    assert result.coverage == {"one#p:0": "processed", "one#p:1": "failed"}
