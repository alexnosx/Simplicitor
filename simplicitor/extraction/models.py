"""Small shared contracts for source reading, grounding, and evaluation."""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from app.config.defaults import EXTRACTION_NUM_CTX, EXTRACTION_NUM_PREDICT, EXTRACTION_TIMEOUT_S


@dataclass(frozen=True)
class Issue:
    code: str
    source_id: str
    anchor: str
    safe_message: str


@dataclass(frozen=True)
class SourceUnit:
    anchor: str
    text: str
    kind: str
    order: int
    structural_group: str = ""


@dataclass(frozen=True)
class SourceDocument:
    source_id: str
    original_path: Path
    label: str
    units: tuple[SourceUnit, ...]
    page_cost: int
    issues: tuple[Issue, ...] = ()


@dataclass(frozen=True)
class ColumnSpec:
    id: str
    label: str
    description: str
    kind: str = "text"
    thousands_separator: str = ","
    decimal_separator: str = "."
    date_order: str | None = None


@dataclass(frozen=True)
class FieldProposal:
    value: str | None
    quote: str
    anchor: str

    def __post_init__(self) -> None:
        """Treat blank model strings as absent across parsing and Data projection."""
        if isinstance(self.value, str) and not self.value.strip():
            object.__setattr__(self, "value", None)


@dataclass(frozen=True)
class FieldResult:
    proposal: FieldProposal
    typed_value: str | int | Decimal | date | None
    flagged: bool
    issues: tuple[str, ...] = ()
    alternatives: tuple[FieldProposal, ...] = ()

    @property
    def data_value(self) -> str | int | Decimal | date | None:
        """Project exactly what the future Data cell must contain."""
        return self.proposal.value if self.flagged else self.typed_value


@dataclass(frozen=True)
class ExtractionProfile:
    """Explicit model/request settings, independent of hardware inspection."""
    model: str
    options: dict = field(default_factory=dict)
    timeout: int = EXTRACTION_TIMEOUT_S

    def __post_init__(self) -> None:
        """Apply fixed defaults without modifying the caller's options dictionary."""
        defaults = {"num_ctx": EXTRACTION_NUM_CTX, "num_predict": EXTRACTION_NUM_PREDICT,
                    "temperature": 0, "seed": 0}
        object.__setattr__(self, "options", defaults | self.options)


@dataclass(frozen=True)
class Section:
    """A non-overlapping unit group, including visibly excluded oversized groups."""
    section_id: str
    source_id: str
    unit_ids: tuple[str, ...]
    excluded: bool = False


@dataclass(frozen=True)
class ExtractionResult:
    """The complete source/column roster, proposals, and per-unit coverage status."""
    ordered_source_ids: tuple[str, ...]
    fields: Mapping[tuple[str, str], FieldResult]
    source_paths: Mapping[str, Path]
    issues: tuple[Issue, ...]
    coverage: Mapping[str, str]


def build_response_schema(
    columns: tuple[ColumnSpec, ...], record_ids: tuple[str, ...]
) -> dict:
    """Constrain structure while keeping every proposed value a literal string."""
    proposal = {
        "type": "object",
        "properties": {
            "value": {"type": ["string", "null"]},
            "quote": {"type": "string"},
            "anchor": {"type": "string"},
        },
        "required": ["value", "quote", "anchor"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "records": {
                "type": "array", "minItems": len(record_ids), "maxItems": len(record_ids),
                "items": {
                    "type": "object",
                    "properties": {
                        "record_id": {"type": "string", "enum": list(record_ids)},
                        "fields": {
                            "type": "object",
                            "properties": {c.id: proposal for c in columns},
                            "required": [c.id for c in columns],
                            "additionalProperties": False,
                        },
                    },
                    "required": ["record_id", "fields"], "additionalProperties": False,
                },
            },
        },
        "required": ["records"], "additionalProperties": False,
    }
