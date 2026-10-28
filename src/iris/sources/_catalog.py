"""Shared ``catalog-info.yaml`` (Backstage-style descriptor) parsing.

One interpretation point for the descriptor, used by the constellation source for every repo it reads
(mrconfig entries and on-disk checkouts alike). A descriptor may be multi-document: the Component (the
repo itself) is the first mapping document whose ``kind`` is absent or ``Component``; every
``kind: Resource`` document is a non-code entity the repo hosts. Entity refs (``dependsOn``,
``dependencyOf``) follow Backstage's ``[<kind>:][<namespace>/]<name>`` grammar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Descriptor:
    """The parts of a descriptor iris reads."""

    component: dict = field(default_factory=dict)  # the Component document (empty when none)
    resources: list[dict] = field(default_factory=list)  # every ``kind: Resource`` document
    depends_on: list[str] = field(default_factory=list)  # the Component's raw ``spec.dependsOn`` refs


def parse_entity_ref(ref: str) -> tuple[str | None, str | None, str]:
    """Split a Backstage entity ref ``[<kind>:][<namespace>/]<name>`` into ``(kind, namespace, name)``."""
    kind: str | None = None
    namespace: str | None = None
    rest = str(ref).strip()
    if ":" in rest:
        kind, rest = rest.split(":", 1)
    if "/" in rest:
        namespace, rest = rest.split("/", 1)
    return kind, namespace, rest


def parse_descriptor(path: Path) -> Descriptor:
    """Read a ``catalog-info.yaml`` into its Component, Resources and raw ``dependsOn`` refs."""
    docs = [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(d, dict)]
    component = next((d for d in docs if d.get("kind") in (None, "Component")), {})
    resources = [d for d in docs if d.get("kind") == "Resource"]
    spec = component.get("spec") or {}
    depends_on = [str(dep) for dep in (spec.get("dependsOn") or [])]
    return Descriptor(component=component, resources=resources, depends_on=depends_on)
