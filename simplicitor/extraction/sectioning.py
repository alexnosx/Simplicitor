"""Whole-file-first planning with a conservative context-derived token estimate."""
import json

from app.config.defaults import EXTRACTION_TEMPLATE_TOKEN_RESERVE
from extraction.models import (
    ColumnSpec, ExtractionProfile, Section, SourceDocument, build_response_schema,
)
from extraction.request_format import SYSTEM_PROMPT, build_extraction_prompt


class ContextBudgetError(ValueError):
    """The configured request leaves no source budget; setup must be changed."""


def request_fits(system: str, prompt: str, schema: dict, profile: ExtractionProfile) -> bool:
    """Estimate one token per UTF-8 byte plus template and reserved output tokens."""
    context, output = profile.options.get("num_ctx"), profile.options.get("num_predict")
    if type(context) is not int or type(output) is not int or context <= 0 or output <= 0:
        raise ContextBudgetError("Choose positive context and output token budgets.")
    estimate = sum(len(text.encode("utf-8")) for text in
                   (system, prompt, json.dumps(schema, ensure_ascii=False)))
    return estimate + EXTRACTION_TEMPLATE_TOKEN_RESERVE + output <= context


def make_sections(
    documents: tuple[SourceDocument, ...], profile: ExtractionProfile, *,
    columns: tuple[ColumnSpec, ...] = (), request: str = "",
    carried_fields: dict | None = None,
) -> tuple[Section, ...]:
    """Keep whole files when estimated to fit; otherwise preserve structural groups."""
    sections = []
    for doc in documents:
        schema = build_response_schema(columns, (doc.source_id,))
        def fits(ids: tuple[str, ...]) -> bool:
            prompt = build_extraction_prompt(doc, columns, request, ids, carried_fields)
            return request_fits(SYSTEM_PROMPT, prompt, schema, profile)
        if not fits(()):
            raise ContextBudgetError("The request leaves no source room. Use fewer columns or a larger context.")
        ids = tuple(u.anchor for u in doc.units)
        if fits(ids):
            sections.append(Section(f"{doc.source_id}:section:1", doc.source_id, ids))
            continue
        groups = []
        for unit in doc.units:
            key = unit.structural_group or unit.anchor
            if groups and groups[-1][0] == key:
                groups[-1][1].append(unit.anchor)
            else:
                groups.append((key, [unit.anchor]))
        pending = ()
        index = 0
        for _, group in groups:
            group = tuple(group)
            if pending and not fits(pending + group):
                index += 1
                sections.append(Section(f"{doc.source_id}:section:{index}", doc.source_id, pending))
                pending = ()
            if not fits(group):
                index += 1
                sections.append(Section(f"{doc.source_id}:section:{index}", doc.source_id, group, True))
            else:
                pending += group
        if pending:
            index += 1
            sections.append(Section(f"{doc.source_id}:section:{index}", doc.source_id, pending))
    return tuple(sections)
