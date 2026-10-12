# simplicitor/app/widgets/plain_labels.py
"""Plain-language text for source locations, review reasons, and coverage."""
import re

_ANCHOR = re.compile(
    r"#(?:(header|footer):\d+:)?(?:p:(\d+)|t:(\d+):r:(\d+):c:(\d+)|page:(\d+))$")

_AI_INCOMPLETE = "The AI request did not complete. Check this value."
_ISSUES = {
    "sectioned_source": "Long document: check every value.",
    "missing_value": "The source text did not contain a value for this column.",
    "value_not_verbatim": "The value does not match the document text exactly.",
    "quote_not_in_source": "The quoted text was not found in the document.",
    "unknown_anchor": "The quoted text was not found in the document.",
    "invalid_value_type": "The AI returned this value in an unexpected form.",
    "conversion_failed": "Could not read this as a number or date.",
    "leading_zero": "Starts with 0, so it was kept as text to keep every digit.",
    "excel_precision": "Too many digits for an Excel number, so it was kept as text.",
    "conflict": "Two proposed values disagreed.",
    "unverified_proposal": "Could not confirm this value from the document.",
    "context_truncated": _AI_INCOMPLETE,
    "output_limit": _AI_INCOMPLETE,
    "request_failed": _AI_INCOMPLETE,
    "request_timeout": _AI_INCOMPLETE,
    "invalid_response_schema": _AI_INCOMPLETE,
    "invalid_field_schema": _AI_INCOMPLETE,
}
_COVERAGE = {
    "unreadable_page": "this page has too little text to read.",
    "unsupported_structure": "some parts of this file (such as text boxes, tracked changes "
                             "or footnotes) were not read.",
    "oversized_unit": "one part of this file was too large to read.",
    "context_budget": "this file could not be read with the current settings.",
    "context_truncated": "part of this file was cut off and not read.",
}


def describe_anchor(anchor: str) -> str:
    """Describe an anchored source location without internal identifiers."""
    match = _ANCHOR.search(anchor or "")
    if not match:
        return ""
    area, paragraph, table, row, column, page = match.groups()
    if page:
        where = f"page {page}"
    elif paragraph is not None:
        where = f"paragraph {int(paragraph) + 1}"
    else:
        where = f"table {int(table) + 1}, row {int(row) + 1}, column {int(column) + 1}"
    return f"{where} of the {area}" if area else where


def describe_issues(issues: str) -> str:
    """Describe saved review issues with a safe fallback for unknown codes."""
    codes = [code.strip() for code in (issues or "").split(";") if code.strip()]
    return " ".join(dict.fromkeys(_ISSUES.get(code, "Check this value.") for code in codes))


def describe_coverage(file_label: str, anchor: str, code: str) -> str:
    """Describe an incomplete source using its visible file and location."""
    code = code.split(":", 1)[0].strip()
    reason = _COVERAGE.get(code, "part of this file was not read.")
    where = describe_anchor(anchor)
    return f"{file_label}, {where}: {reason}" if where else f"{file_label}: {reason}"
