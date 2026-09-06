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

# A ``<repo>#<number>`` reference inside free text — the cross-source join carrier AND the query-scoping
# key. The slug must sit immediately before ``#`` (so a spaced "PR #32" or a bare "## heading" never
# matches) and be a repo-name-like token: LOWERCASE-led, matching the checkout-basename identity
# convention every repo follows (iris, agent-kit, pje-2.1). That lowercase anchor drops the
# uppercase-acronym noise ("PR#25", "P1#3", "GLPI#7") a bare letter-start would sweep in — those are
# prose, not repos. Whether a surviving slug is a REAL repo is the caller's resolution, not this
# extraction's (the composer resolves identity for tasks; the tracker matches it against the registry).
_REPO_REF = re.compile(r"(?<![A-Za-z0-9_#])([a-z][a-z0-9._-]*)#\d+")


def repo_refs(text: str) -> list[str]:
    """The distinct ``<repo>`` slugs referenced as ``<repo>#<number>`` in ``text``, first-seen order.

    Shared by the tasks source (keying a task to the repos it names) and the tracker source (scoping
    the forge fan-out to the repos a query names — iris#36), so both derive the join/scope key by the
    SAME rule rather than two coincidentally-aligned regexes (Brief F6: identity is derived, not luck).
    """
    return list(dict.fromkeys(m.group(1) for m in _REPO_REF.finditer(text)))


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
