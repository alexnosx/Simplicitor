"""Frozen contracts for Edit for Word; no Qt, no file writes."""
from dataclasses import dataclass
from pathlib import Path


class EditError(ValueError):
    """A safe, user-facing editing failure. outcome tells the UI what to do next."""

    def __init__(self, message: str, outcome: str = "failed") -> None:
        super().__init__(message)
        self.outcome = outcome


@dataclass(frozen=True)
class Run:
    rpr: bytes
    text: str


@dataclass(frozen=True)
class Marker:
    """A bookmark marker inside a body paragraph; place is lead, trail or inline."""
    tag: str
    raw: bytes
    bookmark_id: str
    name: str
    place: str


@dataclass(frozen=True)
class Block:
    """One direct child of w:body. index is the body paragraph index, or -1."""
    kind: str
    start: int
    end: int
    index: int = -1
    start_tag: bytes = b""
    prefix: bytes = b""
    ppr: tuple[int, int] | None = None
    ppr_children: tuple[tuple[str, int, int], ...] = ()
    runs: tuple[Run, ...] = ()
    markers: tuple[Marker, ...] = ()
    text: str = ""
    reason: str | None = None


@dataclass(frozen=True)
class BookmarkMarker:
    """Any bookmark marker in the main part, for verification check 6."""
    tag: str
    start: int
    end: int
    bookmark_id: str


@dataclass(frozen=True)
class OpenedDocument:
    path: Path
    data: bytes
    sha256: str
    part_name: str
    xml: bytes
    blocks: tuple[Block, ...]
    bookmarks: tuple[BookmarkMarker, ...]
    track_changes_on: bool

    @property
    def paragraphs(self) -> tuple[Block, ...]:
        return tuple(b for b in self.blocks if b.kind == "p")


@dataclass(frozen=True)
class ProposedParagraph:
    source: int
    text: str


@dataclass(frozen=True)
class Proposal:
    paragraphs: tuple[ProposedParagraph, ...]
    attempt: int = 0


@dataclass(frozen=True)
class EditCandidate:
    """A verified new package held in memory until Save As."""
    data: bytes
    sha256: str
    original_path: Path
    original_sha256: str
    first: int
    last: int
    after_count: int
    highlights: tuple[tuple[tuple[int, int], ...], ...]
