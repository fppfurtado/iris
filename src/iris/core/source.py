"""The ``Source`` protocol — a read-only context source.

A source adapts one sovereign canonical (a knowledge base, a repo registry, …) into
iris's normalized model. Adding a source means writing one module that implements this
protocol and declaring it in ``sources.toml`` — no other module changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from iris.core.model import GroundHit, Node, Relation


@dataclass(frozen=True)
class Query:
    """A read request against sources."""

    text: str = ""
    tag: str | None = None


@dataclass
class SourceResult:
    """The normalized result of reading one source.

    ``ok=False`` with a ``note`` is how a source degrades gracefully: it returns empty
    plus a flag instead of raising, so one failing source never brings down the
    federation.
    """

    nodes: list[Node] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    hits: list[GroundHit] = field(default_factory=list)
    ok: bool = True
    note: str = ""


@runtime_checkable
class Source(Protocol):
    """A read-only context source. Implementations expose no write path."""

    name: str

    def read(self, query: Query) -> SourceResult:
        """Read this source for ``query`` and return a normalized result."""
        ...
