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


def parse_key(key: str) -> Ref | None:
    """The single :class:`Ref` an item KEY names — the input of ``iris inbound``.

    The whole stripped input must be exactly one ``<repo>#<n>`` or ``^<anchor>``, by the same patterns
    ``parse_refs`` uses; empty input, several refs, or any other text → ``None``.
    """
    text = key.strip()
    if m := _REPO_REF.fullmatch(text):
        return Ref(kind="issue", slug=m.group(1), number=int(m.group(2)))
    if m := _ANCHOR_REF.fullmatch(text):
        return Ref(kind="anchor", anchor=m.group(1))
    return None


def repo_paths(mrconfig: Path) -> list[Path]:
    """Parse ``mrconfig`` section headers into absolute repo paths."""
    return [path for path, _ in repo_entries(mrconfig)]


def repo_entries(mrconfig: Path) -> list[tuple[Path, str]]:
    """Each ``mrconfig`` repo section as ``(path, checkout command)`` — the command is ``""`` when absent."""
    text = mrconfig.read_text(encoding="utf-8")
    matches = list(_SECTION.finditer(text))
    entries: list[tuple[Path, str]] = []
    for i, match in enumerate(matches):
        name = match.group("name").strip()
        if name in _NON_REPO_SECTIONS:
            continue
        expanded = os.path.expandvars(os.path.expanduser(name))
        if not (os.path.isabs(expanded) or "/" in expanded):
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        checkout = _CHECKOUT.search(text, match.end(), end)
        entries.append((Path(expanded), checkout.group(1).strip() if checkout else ""))
    return entries


def identity(path: Path) -> str:
    """The repo's cross-source join identity — its checkout basename."""
    return path.name


# Clone-URL forms a remote can take: scp-style ``[user@]host:path``, and ``scheme://[user@]host[:port]/path``.
_URL_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://(?:[^@/]+@)?(?P<host>[^/:]+)(?::\d+)?/(?P<path>.+)$", re.I)
_URL_SCP = re.compile(r"^(?:[^@/\s]+@)?(?P<host>[^/:\s]+):(?P<path>[^\s]+)$")
_URL_TOKEN = re.compile(r"""['"]?((?:[a-z][a-z0-9+.-]*://|[^\s'"@/]+@)[^\s'"]+)['"]?""", re.I)
_CHECKOUT = re.compile(r"(?m)^\s*checkout\s*=\s*(.*)$")
_ORIGIN_URL = re.compile(r'(?ms)^\[remote\s+"origin"\]\s*$(?P<body>.*?)(?=^\[|\Z)')
_URL_KEY = re.compile(r"(?m)^\s*url\s*=\s*(\S+)\s*$")


def forge_slug(url: str, host_aliases: dict | None = None) -> str | None:
    """A clone URL's forge slug ``<host>/<path>``, normalised — ``None`` when ``url`` is not a clone URL.

    Host and path are lowercased, a ``.git`` suffix, a trailing ``/`` and any port are dropped, and the host
    is mapped through ``host_aliases`` (an ssh alias → the real host). The path keeps every segment, so a
    GitLab subgroup repo stays distinct.
    """
    match = _URL_SCHEME.match(url) or _URL_SCP.match(url)
    if not match:
        return None
    host = match.group("host").lower()
    path = match.group("path").lower().rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    aliases = {str(k).lower(): str(v).lower() for k, v in (host_aliases or {}).items()}
    host = aliases.get(host, host)
    return f"{host}/{path}" if path else None


def origin_url(repo: Path) -> str | None:
    """The ``origin`` remote URL from a checkout's ``.git/config`` (read directly, no subprocess)."""
    config = repo / ".git" / "config"
    try:
        text = config.read_text(encoding="utf-8")
    except OSError:
        return None
    section = _ORIGIN_URL.search(text)
    if not section:
        return None
    url = _URL_KEY.search(section.group("body"))
    return url.group(1) if url else None


def checkout_url(command: str) -> str | None:
    """The clone URL inside an ``mrconfig`` ``checkout =`` command (e.g. ``git clone '<url>' 'name'``)."""
    for token in _URL_TOKEN.finditer(command):
        if forge_slug(token.group(1)):
            return token.group(1)
    return None


def local_slug(repo: Path, checkout: str = "") -> str:
    """A local repo's membership identity: the forge slug of its ``origin`` — or, when the checkout is
    absent, of the clone URL in its ``checkout =`` command — falling back to ``local:<basename>``."""
    url = origin_url(repo) if repo.is_dir() else checkout_url(checkout)
    slug = forge_slug(url) if url else None
    return slug or f"local:{repo.name}"
