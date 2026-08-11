"""mneme source — shell out to ``mneme … --json`` and normalize into the model.

Reads the mneme knowledge base through its own CLI (federation/sovereignty: iris
does not import mneme as a library, it reads the source's sovereign interface). The
subprocess is injected as a ``runner`` so the normalization is testable without a
mneme install.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable

from iris.core.model import GroundHit
from iris.core.registry import DEFAULT
from iris.core.source import Query, Source, SourceResult

Runner = Callable[[list[str]], str]


def _default_runner(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _hit(item: dict) -> GroundHit:
    trust = item.get("trust") or {}
    label = " · ".join(p for p in (trust.get("status", ""), trust.get("class", "")) if p)
    age_days = trust.get("age_days")
    return GroundHit(
        ref=item.get("ref", ""),
        excerpt=item.get("excerpt", ""),
        trust=label,
        age=f"{age_days}d" if age_days is not None else "",
    )


class MnemeSource:
    """Reads the mneme KB via its ``--json`` CLI (read-only)."""

    name = "mneme"

    def __init__(self, options: dict | None = None, runner: Runner = _default_runner) -> None:
        opts = options or {}
        self._runner = runner
        self._bin = opts.get("bin", "mneme")

    def read(self, query: Query) -> SourceResult:
        out = self._runner([self._bin, "ground", "--query", query.text, "--json"])
        data = json.loads(out)
        return SourceResult(hits=[_hit(i) for i in data.get("items", [])])


def _factory(options: dict) -> Source:
    return MnemeSource(options)


DEFAULT.register("mneme", _factory)
