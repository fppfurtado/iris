"""Load source declarations from ``sources.toml``.

The config lists which sources are active and their per-source options. Federation
reads only the declared sources; adding or removing a source is a local change to
this file plus one source module — no other module is touched (PR5).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    """One declared source: its registered name and its options."""

    name: str
    options: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    """The federation configuration — the declared sources, in order."""

    sources: list[SourceSpec] = field(default_factory=list)


def load_config(path: str | Path) -> Config:
    """Parse ``sources.toml`` into a :class:`Config`.

    The file declares sources as ``[sources.<name>]`` tables; the table body (if
    any) becomes that source's options.
    """
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    declared = data.get("sources") or {}
    specs = [SourceSpec(name=name, options=dict(opts or {})) for name, opts in declared.items()]
    return Config(sources=specs)
