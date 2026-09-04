"""Shared repo discovery from an ``mr`` manifest (``~/.mrconfig``).

Both the constellation source (repo nodes) and the tracker source (issues per repo) derive their repo
set — and each repo's join **identity** — from the SAME sovereign registry by the SAME rule (the
checkout basename). Factoring it here makes the cross-source join key genuinely *shared*, not two
coincidentally-aligned derivations (Brief F6: identity is derived, not matched by luck).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_SECTION = re.compile(r"(?m)^\[(?P<name>[^\]]+)\]\s*$")
_NON_REPO_SECTIONS = {"DEFAULT", "ALIAS"}


def repo_paths(mrconfig: Path) -> list[Path]:
    """Parse ``mrconfig`` section headers into absolute repo paths."""
    text = mrconfig.read_text(encoding="utf-8")
    paths: list[Path] = []
    for match in _SECTION.finditer(text):
        name = match.group("name").strip()
        if name in _NON_REPO_SECTIONS:
            continue
        expanded = os.path.expandvars(os.path.expanduser(name))
        if os.path.isabs(expanded) or "/" in expanded:
            paths.append(Path(expanded))
    return paths


def identity(path: Path) -> str:
    """The repo's cross-source join identity — its checkout basename."""
    return path.name
