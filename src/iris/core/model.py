"""The context data model — normalized types every Source maps its raw output into.

These types are read-only value objects (frozen dataclasses); iris never mutates a
source, only reads and composes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tag:
    """A label on a node (e.g. ``pro-bono``)."""

    name: str


@dataclass(frozen=True)
class Node:
    """A federated entity — a repo, a system, a concept — from some source."""

    id: str
    kind: str
    title: str
    tags: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    source: str = ""


@dataclass(frozen=True)
class Relation:
    """A directed edge between two nodes."""

    from_: str
    type: str
    to: str


@dataclass(frozen=True)
class GroundHit:
    """A grounding excerpt with provenance, as returned by a knowledge source."""

    ref: str
    excerpt: str
    trust: str = ""
    age: str = ""
