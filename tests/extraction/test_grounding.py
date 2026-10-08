"""A literal evidence span must precede any type conversion."""
from datetime import date
from decimal import Decimal

import pytest


@pytest.mark.parametrize("quote", [
    "Total: USD 12,500.00", "$12,500.00 (tax included)",
    "Balance due: £12,500.00", "Total: EUR 12,500.00", "Pay €12,500.00 now",
])
def test_currency_context_preserves_literal_amount(quote):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    column = ColumnSpec("total", "Total", "Invoice total", "decimal")
    unit = SourceUnit("one#p:0", quote, "paragraph", 0)
    result = validate_field(FieldProposal("12,500.00", quote, unit.anchor), column,
                            {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == Decimal("12500.00")
    normalized = validate_field(FieldProposal("12500.00", quote, unit.anchor), column,
                                {unit.anchor: unit})
    assert normalized.flagged
    assert normalized.data_value == "12500.00"


@pytest.mark.parametrize("value", ["15 March 2026", "March 15, 2026", "15-Mar-2026"])
def test_english_dates_are_converted_by_code(value):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#page:1", "Date: " + value, "page", 0)
    result = validate_field(FieldProposal(value, unit.text, unit.anchor),
                            ColumnSpec("date", "Date", "", "date"), {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == date(2026, 3, 15)


@pytest.mark.parametrize("value,kind,want_flag", [
    ("00123", "text", False), ("NaN", "text", False), ("inf", "decimal", True),
    ("1_000", "decimal", True), ("=1+1", "text", False), ("01/02/2026", "date", True),
])
def test_types_do_not_invent_normalization(value, kind, want_flag):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("s#p:0", value, "paragraph", 0)
    result = validate_field(FieldProposal(value, value, unit.anchor),
                            ColumnSpec("field", "Field", "", kind), {unit.anchor: unit})
    assert result.flagged is want_flag
    if kind == "text":
        assert result.data_value == value


def test_quote_must_belong_to_the_referenced_unit():
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("s#p:0", "Total: 12.00", "paragraph", 0)
    column = ColumnSpec("total", "Total", "", "decimal")
    for proposal in [FieldProposal("12.00", "Total: 12.00", "other#p:0"),
                     FieldProposal("13.00", "Total: 13.00", unit.anchor),
                     FieldProposal(None, "", "")]:
        assert validate_field(proposal, column, {unit.anchor: unit}).flagged


def test_quote_whitespace_can_vary_but_value_must_be_literal():
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("s#p:0", "Customer:\nAcme   Ltd", "paragraph", 0)
    result = validate_field(FieldProposal("Acme Ltd", "Customer: Acme Ltd", unit.anchor),
                            ColumnSpec("customer", "Customer", "", "text"),
                            {unit.anchor: unit})
    assert not result.flagged


def test_whitespace_is_not_evidence_of_a_missing_text_value():
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit
    unit = SourceUnit("s#p:0", "Customer not stated", "paragraph", 0)
    result = validate_field(FieldProposal(" ", " ", unit.anchor),
                            ColumnSpec("name", "Name", "", "text"), {unit.anchor: unit})
    assert result.flagged
