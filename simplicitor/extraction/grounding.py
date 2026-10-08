"""One literal evidence rule for every type, followed by deterministic conversion."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Mapping

from extraction.models import ColumnSpec, FieldProposal, FieldResult, SourceUnit

_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_MONTHS = {name: i for i, name in enumerate(_MONTH_NAMES, 1)}
_MONTHS.update({name[:3]: i for i, name in enumerate(_MONTH_NAMES, 1)})
_MONTHS["sept"] = 9


def validate_field(
    proposal: FieldProposal, column: ColumnSpec, units: Mapping[str, SourceUnit]
) -> FieldResult:
    """Check anchor, normalized quote, literal value span, then column conversion."""
    issue = ""
    unit = units.get(proposal.anchor)
    if proposal.value is None or proposal.value == "":
        issue = "missing_value"
    elif not isinstance(proposal.value, str):
        issue = "invalid_value_type"
    elif unit is None:
        issue = "unknown_anchor"
    elif not proposal.quote.strip() or " ".join(proposal.quote.split()) not in " ".join(unit.text.split()):
        issue = "quote_not_in_source"
    elif proposal.value not in proposal.quote or not _has_grounded_match(
        proposal.value, proposal.quote, unit.text
    ):
        issue = "value_not_verbatim"
    if issue:
        return FieldResult(proposal, None, True, (issue,))
    try:
        if column.kind == "text":
            value = proposal.value
        elif column.kind in ("integer", "decimal"):
            value = _number(proposal.value, column)
        elif column.kind == "date":
            value = _date(proposal.value, column.date_order)
        else:
            raise ValueError("unsupported_type")
        return FieldResult(proposal, value, False)
    except (ValueError, InvalidOperation, OverflowError):
        return FieldResult(proposal, None, True, ("conversion_failed",))


def _has_grounded_match(value: str, quote: str, source: str) -> bool:
    # Literal containment was checked first. Normalize whitespace only to locate
    # that same quote/value span in the reader's text and inspect its real edges.
    value, quote, source = (" ".join(text.split()) for text in (value, quote, source))
    if not value:
        return False
    for quote_match in re.finditer(re.escape(quote), source):
        for value_match in re.finditer(re.escape(value), quote):
            start, end = value_match.span()
            if (_at_token_boundaries(quote, start, end)
                    and _at_token_boundaries(source, quote_match.start() + start,
                                             quote_match.start() + end)):
                return True
    return False


def _at_token_boundaries(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start else ""
    after = text[end] if end < len(text) else ""
    return not (
        before.isalnum() or after.isalnum()
        or (before in (",", ".") and start > 1 and text[start - 2].isdigit())
        or (after in (",", ".") and end + 1 < len(text) and text[end + 1].isdigit())
    )


def _number(value: str, column: ColumnSpec) -> Decimal | int:
    text = value.strip()
    marker = r"(?:[£$€¥]|[A-Z]{3})"
    text = re.sub(rf"^{marker}\s*|\s*{marker}$", "", text, count=1)
    thousands, decimal = column.thousands_separator, column.decimal_separator
    if not decimal or len(decimal) != 1 or decimal == thousands or len(thousands) > 1:
        raise ValueError("invalid_separator")
    grouped = rf"[0-9]{{1,3}}(?:{re.escape(thousands)}[0-9]{{3}})+" if thousands else r"[0-9]+"
    pattern = rf"[+-]?(?:[0-9]+|{grouped})(?:{re.escape(decimal)}[0-9]+)?"
    if not re.fullmatch(pattern, text):
        raise ValueError("invalid_numeric_grammar")
    normalized = text.replace(thousands, "") if thousands else text
    number = Decimal(normalized.replace(decimal, "."))
    if not number.is_finite():
        raise ValueError("nonfinite")
    if column.kind == "integer":
        if number != number.to_integral_value():
            raise ValueError("not_integer")
        return int(number)
    return number


def _date(value: str, order: str | None) -> date:
    text = value.strip()
    if re.fullmatch(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}", text):
        year, month, day = map(int, text.split("-"))
        return date(year, month, day)
    numeric = re.fullmatch(r"([0-9]{1,2})([/.-])([0-9]{1,2})\2([0-9]{4})", text)
    if numeric:
        a, b, year = int(numeric[1]), int(numeric[3]), int(numeric[4])
        if a == b or a > 12 or order == "DMY":
            return date(year, b, a)
        if b > 12 or order == "MDY":
            return date(year, a, b)
        raise ValueError("ambiguous_date")
    day_first = re.fullmatch(
        r"(?:the )?([0-9]{1,2})(?:st|nd|rd|th)?(?: day of)?[ -]+([A-Za-z]+)[ -]+([0-9]{4})",
        text, re.IGNORECASE,
    )
    month_first = re.fullmatch(
        r"([A-Za-z]+) +([0-9]{1,2})(?:st|nd|rd|th)?,? +([0-9]{4})", text, re.IGNORECASE,
    )
    if day_first:
        day, month_name, year = int(day_first[1]), day_first[2].lower(), int(day_first[3])
    elif month_first:
        day, month_name, year = int(month_first[2]), month_first[1].lower(), int(month_first[3])
    else:
        raise ValueError("invalid_date")
    if month_name not in _MONTHS:
        raise ValueError("invalid_month")
    return date(year, _MONTHS[month_name], day)
