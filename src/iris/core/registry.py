"""Source registry — maps a source TYPE to its implementation.

Each source module self-registers a factory under its ``type`` (into :data:`DEFAULT`).
Federation resolves only the sources the config declares — looking up each spec's
``type`` (falling back to its ``name`` for a built-in registered under its own name).
A config-only source (e.g. a ``cli-json`` instance) needs no new module: adding it is
a config change, and a new *kind* of source is one isolated module (additive
federation, PR5).
"""

from __future__ import annotations

from typing import Callable

from iris.config import Config
from iris.core.source import Source

# A factory takes the instance name and its options and returns a Source.
Factory = Callable[[str, dict], Source]


class Registry:
    """A type → source-factory map."""

    def __init__(self) -> None:
        self._factories: dict[str, Factory] = {}

    def register(self, type_: str, factory: Factory) -> None:
        """Register ``factory`` under a source type (idempotent overwrite)."""
        self._factories[type_] = factory

    def resolve(self, config: Config) -> list[Source]:
        """Return the sources the config declares, in declared order.

        Each spec is resolved by its ``type`` (or its ``name`` when no type is given).
        A spec whose type has no registered factory is skipped (absent), never an error.
        """
        resolved: list[Source] = []
        for spec in config.sources:
            factory = self._factories.get(spec.type or spec.name)
            if factory is not None:
                resolved.append(factory(spec.name, spec.options))
        return resolved


# The default registry sources register themselves into at import time.
DEFAULT = Registry()
