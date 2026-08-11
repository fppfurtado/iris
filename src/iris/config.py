"""Load source declarations from ``sources.toml``.

The config lists which sources are active and their per-source options. Federation
reads only the declared sources; adding or removing a source is a local change to
this file plus one source module — no other module is touched (PR5).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    """One declared source: its instance ``name``, its ``type`` (which implementation
    to use — the registry key), and its options. When ``type`` is empty the name is
    used as the type (a built-in registered under its own name)."""

    name: str
    options: dict = field(default_factory=dict)
    type: str = ""


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
    specs = []
    for name, opts in declared.items():
        opts = dict(opts or {})
        source_type = opts.pop("type", "")
        specs.append(SourceSpec(name=name, options=opts, type=source_type))
    return Config(sources=specs)


def _xdg_config_path() -> Path:
    """The user-level config location: ``$XDG_CONFIG_HOME/iris/sources.toml``
    (default ``~/.config/iris/sources.toml``)."""
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "iris" / "sources.toml"


def discover_config_path() -> Path:
    """Find the active ``sources.toml`` so ``iris`` runs from any directory.

    Precedence, most-specific first:

    1. ``IRIS_CONFIG`` env var — an explicit override; used verbatim (an error
       surfaces if it points nowhere, since the caller asked for that path);
    2. ``./sources.toml`` in the current directory — a project-local config;
    3. ``$XDG_CONFIG_HOME/iris/sources.toml`` — the user-level default.

    Raises :class:`FileNotFoundError` listing the searched locations if none exists.
    """
    override = os.environ.get("IRIS_CONFIG")
    if override:
        return Path(override)
    candidates = [Path("sources.toml"), _xdg_config_path()]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    searched = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(
        f"no sources.toml found (searched: {searched}); set IRIS_CONFIG or create "
        f"one of those paths"
    )


def active_config() -> Config:
    """Load the active source declarations from the discovered config path
    (see :func:`discover_config_path`)."""
    return load_config(discover_config_path())
