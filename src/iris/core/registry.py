"""Source registry — maps a declared source name to its implementation.

Each source module self-registers a factory under its name (into :data:`DEFAULT`).
Federation resolves only the sources the config declares, so a source that is not
declared is simply absent — and a new source is an isolated module that registers
itself without any other module changing (additive federation, PR5).
"""

from __future__ import annotations

from typing import Callable

from iris.config import Config
from iris.core.source import Source

Factory = Callable[[dict], Source]


class Registry:
    """A name → source-factory map."""

    def __init__(self) -> None:
        self._factories: dict[str, Factory] = {}

    def register(self, name: str, factory: Factory) -> None:
        """Register ``factory`` under ``name`` (idempotent overwrite)."""
        self._factories[name] = factory

    def resolve(self, config: Config) -> list[Source]:
        """Return the sources the config declares, in declared order.

        A declared name with no registered factory is skipped (absent), never an
        error — an undeclared name is likewise absent.
        """
        resolved: list[Source] = []
        for spec in config.sources:
            factory = self._factories.get(spec.name)
            if factory is not None:
                resolved.append(factory(spec.options))
        return resolved


# The default registry sources register themselves into at import time.
DEFAULT = Registry()
