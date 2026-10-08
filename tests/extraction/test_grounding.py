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


@pytest.mark.parametrize("value,quote,kind", [
    ("2,500.00", "Gross total: USD 12,500.00", "decimal"),
    ("500.00", "Gross total: USD 12,500.00", "decimal"),
    ("12", "Gross total: USD 12,500.00", "decimal"),
    ("12,500", "Gross total: USD 12,500.00", "decimal"),
    ("5 March 2026", "15 March 2026", "date"),
    ("Alder", "Alderton Ltd", "text"),
])
def test_partial_tokens_cannot_ground_a_value(value, quote, kind):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", quote, "paragraph", 0)
    result = validate_field(FieldProposal(value, quote, unit.anchor),
                            ColumnSpec("field", "Field", "", kind), {unit.anchor: unit})
    assert result.flagged
    assert result.data_value == value


@pytest.mark.parametrize("value,quote,kind,want", [
    ("12,500.00", "Gross total: USD 12,500.00", "decimal", Decimal("12500.00")),
    ("15 March 2026", "Payment is due on 15 March 2026.", "date", date(2026, 3, 15)),
    ("500.00", "Gross 12,500.00; deposit 500.00.", "decimal", Decimal("500.00")),
])
def test_whole_tokens_and_sentence_punctuation_are_grounded(value, quote, kind, want):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", quote, "paragraph", 0)
    result = validate_field(FieldProposal(value, quote, unit.anchor),
                            ColumnSpec("field", "Field", "", kind), {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == want


@pytest.mark.parametrize("value", [
    "15th March 2026", "March 15th, 2026", "the 15th day of March 2026",
    "1st March 2026", "March 1st, 2026", "the 1st day of March 2026",
])
def test_ordinal_days_are_converted_after_literal_grounding(value):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", "Effective on " + value + ".", "paragraph", 0)
    result = validate_field(FieldProposal(value, unit.text, unit.anchor),
                            ColumnSpec("date", "Date", "", "date"), {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == date(2026, 3, 1 if "1st" in value else 15)


@pytest.mark.parametrize("value,quote,source,kind", [
    ("2,500.00", "2,500.00", "Gross total: USD 12,500.00", "decimal"),
    ("500.00", "500.00", "Gross total: USD 12,500.00", "decimal"),
    ("12,500", "12,500", "Gross total: USD 12,500.00", "decimal"),
    ("5 March 2026", "5 March 2026", "Payment due on 15 March 2026.", "date"),
])
def test_truncated_quote_cannot_hide_source_token_boundaries(value, quote, source, kind):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", source, "paragraph", 0)
    result = validate_field(FieldProposal(value, quote, unit.anchor),
                            ColumnSpec("field", "Field", "", kind), {unit.anchor: unit})
    assert result.flagged
    assert result.data_value == value


def test_short_date_quote_at_sentence_end_keeps_real_source_boundaries():
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", "Payment\nis due on 15 March 2026.", "paragraph", 0)
    result = validate_field(FieldProposal("15 March 2026", "due on 15 March 2026", unit.anchor),
                            ColumnSpec("date", "Date", "", "date"), {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == date(2026, 3, 15)


@pytest.mark.parametrize("value,want", [
    ("GBP 2,400.00", "2400.00"), ("£48,000.00", "48000.00"),
    ("12,500.00 USD", "12500.00"), ("USD12,500.00", "12500.00"),
    ("$ 12,500.00", "12500.00"), ("€12,500.00", "12500.00"),
    ("¥12,500.00", "12500.00"), ("12,500.00£", "12500.00"),
    ("12,500.00 $", "12500.00"), ("12,500.00€", "12500.00"),
    ("12,500.00 ¥", "12500.00"), ("-12,500.00 USD", "-12500.00"),
])
def test_currency_is_stripped_only_after_verbatim_grounding(value, want):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", "The amount payable is " + value + ".", "paragraph", 0)
    result = validate_field(FieldProposal(value, unit.text, unit.anchor),
                            ColumnSpec("total", "Total", "", "decimal"), {unit.anchor: unit})
    assert not result.flagged
    assert result.typed_value == Decimal(want)
    assert result.proposal.value == value
    invented = validate_field(FieldProposal("GBP 1.00", unit.text, unit.anchor),
                               ColumnSpec("total", "Total", "", "decimal"),
                               {unit.anchor: unit})
    assert invented.flagged


@pytest.mark.parametrize("value", ["gbp 2,400.00", "TOTAL 2,400.00", "GBP 2,40.00"])
def test_currency_conversion_does_not_accept_labels_or_bad_numeric_grammar(value):
    from extraction.grounding import validate_field
    from extraction.models import ColumnSpec, FieldProposal, SourceUnit

    unit = SourceUnit("one#p:0", value, "paragraph", 0)
    result = validate_field(FieldProposal(value, value, unit.anchor),
                            ColumnSpec("total", "Total", "", "decimal"), {unit.anchor: unit})
    assert result.flagged
    assert result.data_value == value


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_blank_proposals_project_to_null(value):
    from extraction.models import FieldProposal, FieldResult

    field = FieldResult(FieldProposal(value, "", ""), None, True, ("missing_value",))
    assert field.proposal.value is None
    assert field.data_value is None
