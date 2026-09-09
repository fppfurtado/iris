"""Shared repo discovery from an ``mr`` manifest (``~/.mrconfig``).

Both the constellation source (repo nodes) and the tracker source (issues per repo) derive their repo
set — and each repo's join **identity** — from the SAME sovereign registry by the SAME rule (the
checkout basename). Factoring it here makes the cross-source join key genuinely *shared*, not two
coincidentally-aligned derivations (Brief F6: identity is derived, not matched by luck).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
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
# The number is captured (group 2) for the specific-issue join (F6-mínimo); ``repo_refs`` still keys on
# the slug alone, so its existing callers are unaffected.
_REPO_REF = re.compile(r"(?<![A-Za-z0-9_#])([a-z][a-z0-9._-]*)#(\d+)")

# A ``^<anchor>`` reference — a list/GTD block id in the knowledge base (e.g. ``^dogfd1``). Lowercase
# alphanumeric, and the ``^`` must not sit inside a word (``a^b`` is not a ref), mirroring the
# repo-ref's own boundary discipline. The within-store companion of the cross-repo ``token#N`` ref.
_ANCHOR_REF = re.compile(r"(?<![A-Za-z0-9^])\^([a-z0-9]+)")


@dataclass(frozen=True)
class Ref:
    """A reference parsed from a work item's prose — the join key of the F6-mínimo chain.

    ``kind="issue"`` carries ``slug`` + ``number`` (a cross-repo ``<repo>#<n>``); ``kind="anchor"``
    carries ``anchor`` (a within-store ``^<id>``). Exactly one shape is populated per kind.
    """

    kind: str  # "issue" | "anchor"
    slug: str | None = None  # issue: the repo slug
    number: int | None = None  # issue: the issue number
    anchor: str | None = None  # anchor: the block id (without the leading ``^``)


def repo_refs(text: str) -> list[str]:
    """The distinct ``<repo>`` slugs referenced as ``<repo>#<number>`` in ``text``, first-seen order.

    Shared by the tasks source (keying a task to the repos it names) and the tracker source (scoping
    the forge fan-out to the repos a query names — iris#36), so both derive the join/scope key by the
    SAME rule rather than two coincidentally-aligned regexes (Brief F6: identity is derived, not luck).
    """
    return list(dict.fromkeys(m.group(1) for m in _REPO_REF.finditer(text)))


def parse_refs(text: str) -> list[Ref]:
    """Every reference in ``text`` — cross-repo ``<repo>#<n>`` issues AND within-store ``^<id>``
    anchors — as typed :class:`Ref`s in first-seen (text-position) order, deduplicated.

    The ref parser for the F6-mínimo chain (Brief J1): unlike ``repo_refs`` it PRESERVES the issue
    number (the specific-issue join key, not the repo-scope key) and additionally captures anchors.
    """
    matches: list[tuple[int, Ref]] = []
    for m in _REPO_REF.finditer(text):
        matches.append((m.start(), Ref(kind="issue", slug=m.group(1), number=int(m.group(2)))))
    for m in _ANCHOR_REF.finditer(text):
        matches.append((m.start(), Ref(kind="anchor", anchor=m.group(1))))
    matches.sort(key=lambda pair: pair[0])
    ordered: list[Ref] = []
    seen: set[Ref] = set()
    for _, ref in matches:
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    return ordered


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
