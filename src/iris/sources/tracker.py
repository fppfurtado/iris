"""``tracker`` source — open issues per repo from a forge CLI (gh/glab), keyed to repos by identity.

Source-agnostic by construction (Brief C7): the adapter names no org, host or instance. The config declares
WHICH forge CLI to run and how to map its JSON, and — for a registry that spans several forges — which CLI
serves which host (``forges."<host>"``, written only in the private config). Issues are resolved by running the
forge CLI with ``cwd`` set to each repo's local checkout (or ``{slug}``), so owner and token live only in the
checkout's own git remote, never in iris.

Forge per host (spec-repo-issues-federation v3, SP-T8): a ``forges`` entry whose key equals a repo's slug host
overrides the top-level ``command`` / ``view`` / ``items`` / ``map`` / ``states`` key by key (``map`` and
``states`` merge). A repo with no command for the read's mode is UNSERVED: counted unreadable with a note naming
its host, never skipped silently. The issue state read by ``view`` maps through ``states`` (raw lowercased →
canonical ``open`` / ``closed``, over the identity); an unmapped value carries no state (UNKNOWN downstream).

Scoped by the query, not the registry (iris#36): the fan-out is restricted to the repos the query
NAMES as ``<repo>#<n>`` — so ``context "mexer em iris#29"`` spawns the forge CLI only in ``iris``, and a
query naming no repo (a bare ``context``, or the ``repos``/``ground`` reads that carry no task text)
spawns nothing at all. This keeps the source ergonomic to enable in an active config over a large
registry, where the old all-repos sweep made every read pay one subprocess per checkout.

Each open issue becomes a ``Node(kind="issue")`` plus a
``Relation(<repo-identity>, "has-open-issue", …)`` so the composer can group it under its repo. The
subprocess runner is injected so normalization is testable without gh/glab installed; a per-repo
failure (forge absent / unauthenticated / timeout / bad JSON) degrades that repo only — never a raise
that sinks the federation.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable

from iris.core.model import Node, Relation
from iris.core.registry import DEFAULT
from iris.core.source import KIND_CHAIN, KIND_NODES, Query, Source, SourceResult
from iris.sources._json import dig
from iris.sources._repos import ambiguity_note, identity_map, parse_refs, repo_entries, repo_refs

# A runner takes the forge argv and the repo checkout to run it in, and returns stdout.
Runner = Callable[[list[str], Path], str]

_DEFAULT_TIMEOUT = 30.0

# The canonical issue states a ``states`` table maps to; the identity on them always applies beneath it.
_CANONICAL_STATES = ("open", "closed")
_LOCAL_HOST = "no forge host"
_KEYS = ("command", "view", "items", "map", "states")
# The shape each `forges` key must have; an entry with another shape is a config error, not a read-time crash.
_SHAPES = {"command": list, "view": list, "items": str, "map": dict, "states": dict}


def _states_table(raw, where: str, errors: list[str]) -> dict[str, str]:
    """A ``states`` table lowercased on load; a target outside the canonical states is a config error."""
    table: dict[str, str] = {}
    for key, target in (raw or {}).items():
        value = str(target).lower()
        if value not in _CANONICAL_STATES:
            errors.append(f"config: {where}states.{key} -> {target!r} is not open/closed (ignored)")
            continue
        table[str(key).lower()] = value
    return table


def _host_of(slug: str) -> str | None:
    """The host of a forge slug ``<host>/<path>`` — ``None`` for a ``local:`` slug."""
    if not slug or slug.startswith("local:"):
        return None
    return slug.split("/", 1)[0]


def _make_default_runner(timeout: float) -> Runner:
    """A runner that enforces a timeout and runs in the repo checkout — a hung/failing forge CLI
    raises, which ``read`` isolates into a per-repo note rather than sinking the read."""

    def _run(cmd: list[str], cwd: Path) -> str:
        # Same caller-marker discipline as cli_json: a source CLI can detect it was invoked BY iris.
        env = {**os.environ, "IRIS_CALLER": "iris"}
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True, timeout=timeout, env=env
        ).stdout

    return _run


class TrackerSource:
    """A read-only source over a forge issue-list CLI, one invocation per repo checkout."""

    # Emits the node graph (issue nodes + repo->issue relations) for ``context``, AND referenced-issue
    # state for ``chain`` (KIND_CHAIN). No hits: a hits-only query (e.g. ``ground``) skips it — no forge
    # subprocess spawned for a discarded read.
    produces = frozenset({KIND_NODES, KIND_CHAIN})

    def __init__(self, name: str, options: dict | None = None, runner: Runner | None = None) -> None:
        opts = options or {}
        self.name = name
        self._timeout = float(opts.get("timeout", _DEFAULT_TIMEOUT))
        self._runner = runner if runner is not None else _make_default_runner(self._timeout)
        self._mrconfig = opts.get("mrconfig", "~/.mrconfig")
        # Config errors are found here and reported on every read that names a `<repo>#<n>` ref (SP-T8 d).
        self._config_errors: list[str] = []
        # The top-level settings. `command` lists a repo's open issues (context); `view` fetches ONE issue by
        # number incl. its state (chain), via `{number}` — e.g. ["gh", "issue", "view", "{number}", "--json",
        # "number,title,state"]. A repo whose host has no `view` (here or in its `forges` entry) is unserved
        # in chain mode, per ref (BR04), leaving ``context`` untouched. ``{slug}`` in either is replaced by
        # the repo's forge slug ``<host>/<path>`` (from its checkout, never from config), so the CLI reads
        # the very repo the identity names — ``gh … -R {slug}`` or ``glab … -R https://{slug}``.
        self._top: dict = {
            "command": list(opts.get("command", [])),
            "view": list(opts.get("view", [])),
            "items": opts.get("items", ""),
            "map": dict(opts.get("map", {})),
            "states": _states_table(opts.get("states"), "", self._config_errors),
        }
        # The top-level command and map by their v2 names (the S2 proof reads them: no forge baked in).
        self._command: list[str] = self._top["command"]
        self._map: dict[str, str] = self._top["map"]
        self._forges: dict[str, dict] = {}
        for key, entry in (opts.get("forges") or {}).items():
            host = str(key).lower().split(":", 1)[0]
            if not isinstance(entry, dict) or not ("command" in entry or "view" in entry):
                self._config_errors.append(f"config: forges.{key} carries no command or view (ignored)")
                continue
            bad = [k for k, kind in _SHAPES.items() if k in entry and not isinstance(entry[k], kind)]
            if bad:
                self._config_errors.append(f"config: forges.{key} has a malformed {', '.join(bad)} (ignored)")
                continue
            if host in self._forges:
                self._config_errors.append(f"config: forges.{key} duplicates host {host!r} (ignored)")
                continue
            self._forges[host] = {
                k: (_states_table(entry[k], f"forges.{key}.", self._config_errors) if k == "states" else entry[k])
                for k in _KEYS
                if k in entry
            }

    def _settings(self, slug: str) -> dict:
        """The settings for one repo: its host's `forges` entry over the top level, key by key."""
        host = _host_of(slug)
        entry = self._forges.get(host, {}) if host else {}
        merged = {k: entry.get(k, self._top[k]) for k in ("command", "view", "items")}
        merged["map"] = {**self._top["map"], **dict(entry.get("map", {}))}
        merged["states"] = {
            **{v: v for v in _CANONICAL_STATES},
            **self._top["states"],
            **entry.get("states", {}),
        }
        return merged

    def _config_notes(self) -> list[str]:
        return list(self._config_errors)

    def read(self, query: Query) -> SourceResult:
        # Kind-aware mode split (BR07): a ``chain`` query wants the LIVE state of the SPECIFIC issues an
        # item references (incl. CLOSED) — a different read than ``context``'s list of a repo's OPEN
        # issues. Route by the consumed kind; ``context``/bare reads keep the existing list path.
        if query.kinds is not None and KIND_CHAIN in query.kinds:
            return self._read_referenced(query)
        return self._read_open(query)

    def _read_open(self, query: Query) -> SourceResult:
        # Scoped by construction (iris#36): the tracker spawns a forge CLI only for the repos the query
        # NAMES as `<repo>#<n>`, not the whole registry. A query naming none — a bare `context`, or the
        # `repos`/`ground` reads that carry no task text — derives zero targets and returns empty with
        # no fan-out, no forge subprocess. (Config-time overrides like an explicit allowlist grow by
        # validated need — iris#36 chose query-derived + empty-fallback; no allowlist until one is felt.)
        wanted = set(repo_refs(query.text))
        if not wanted:
            return SourceResult(ok=True)
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        try:
            identities = identity_map(repo_entries(mrconfig))
        except OSError as exc:
            return SourceResult(ok=False, note=f"cannot read mrconfig ({exc})")
        repos = [r for r, ident in identities.by_path.items() if ident in wanted]
        nodes: list[Node] = []
        relations: list[Relation] = []
        failed = 0
        unserved: dict[str, int] = {}
        for repo in repos:
            ident = identities.by_path[repo]
            slug = identities.slugs[repo]
            settings = self._settings(slug)
            if not settings["command"]:
                host = _host_of(slug) or _LOCAL_HOST
                unserved[host] = unserved.get(host, 0) + 1
                continue
            cmd = [arg.replace("{slug}", slug) for arg in settings["command"]]
            try:
                data = json.loads(self._runner(cmd, repo))
            except Exception:  # per-repo isolation: absent/unauth/timeout/bad-JSON degrades this repo
                failed += 1
                continue
            items_path = settings["items"]
            items = dig(data, items_path) if items_path else data
            fields = settings["map"]
            if not isinstance(items, list):
                # unexpected shape (e.g. a wrapped object with `items` mis-configured): degrade this
                # repo rather than iterate a dict's keys into malformed `#None` nodes.
                failed += 1
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                number = dig(item, fields.get("number", "number"))
                if number is None:
                    continue  # an issue without an identifiable number cannot key a stable node
                node_id = f"{ident}#{number}"
                nodes.append(
                    Node(
                        id=node_id,
                        kind="issue",
                        title=str(dig(item, fields.get("title", "title")) or ""),
                        source=self.name,
                    )
                )
                relations.append(Relation(from_=ident, type="has-open-issue", to=node_id))
        notes = self._config_notes()
        ok = not notes
        if failed:
            notes.append(f"{failed}/{len(repos)} repos unreadable (forge absent/unauth/timeout/unexpected-shape)")
            ok = False
        for host, count in unserved.items():
            notes.append(f"{count} repo(s) unserved ({host}): no `command` for this host")
            ok = False
        if wanted & identities.ambiguous:
            notes.append(ambiguity_note(wanted & identities.ambiguous))
        return SourceResult(nodes=nodes, relations=relations, ok=ok, note="; ".join(notes))

    def _read_referenced(self, query: Query) -> SourceResult:
        """Chain mode (F6-mínimo): fetch the LIVE state of each SPECIFIC ``<repo>#<n>`` the query names.

        Unlike ``_read_open`` this resolves refs to individual issues via the per-issue ``view`` command
        (state incl. CLOSED, carried in ``roles``). A ref whose fetch fails degrades that ref into a
        note (BR04) — the chain composer surfaces it as unresolved/unknown, never as clear.
        """
        refs = [r for r in parse_refs(query.text) if r.kind == "issue"]
        if not refs:
            return SourceResult(ok=True)
        mrconfig = Path(os.path.realpath(os.path.expanduser(self._mrconfig)))
        try:
            identities = identity_map(repo_entries(mrconfig))
        except OSError as exc:
            return SourceResult(ok=False, note=f"cannot read mrconfig ({exc})")
        # An ambiguous name keys no entry (each is keyed by its path), so a ref to it finds none here and
        # the composer marks it unresolved; the note says why.
        paths = {ident: p for p, ident in identities.by_path.items()}
        nodes: list[Node] = []
        failed = 0
        unserved: dict[str, int] = {}
        unmapped: dict[str, int] = {}
        for ref in refs:
            repo = paths.get(ref.slug)
            if repo is None:
                continue  # a ref to a repo outside the registry — the composer marks it unresolved
            slug = identities.slugs[repo]
            settings = self._settings(slug)
            if not settings["view"]:
                host = _host_of(slug) or _LOCAL_HOST
                unserved[host] = unserved.get(host, 0) + 1
                continue
            cmd = [arg.replace("{number}", str(ref.number)).replace("{slug}", slug) for arg in settings["view"]]
            try:
                data = json.loads(self._runner(cmd, repo))
            except Exception:  # per-ref isolation: absent/unauth/timeout/bad-JSON degrades this ref
                failed += 1
                continue
            if not isinstance(data, dict):
                failed += 1
                continue
            fields = settings["map"]
            raw = dig(data, fields.get("state", "state"))
            state = None
            if raw:  # a falsy state (absent, null, "", false, 0) is MISSING: no role and no note
                state = settings["states"].get(str(raw).lower())
                if state is None:
                    unmapped[str(raw)] = unmapped.get(str(raw), 0) + 1
            nodes.append(
                Node(
                    id=f"{ref.slug}#{ref.number}",
                    kind="issue",
                    title=str(dig(data, fields.get("title", "title")) or ""),
                    roles=[state] if state else [],
                    source=self.name,
                )
            )
        notes = self._config_notes()
        if failed:
            notes.append(f"chain: {failed} ref(s) unreadable (forge absent/unauth/timeout)")
        for host, count in unserved.items():
            notes.append(f"chain: {count} ref(s) unserved ({host}): no `view` command for this host")
        for raw, count in unmapped.items():
            notes.append(f"chain: state '{raw}' not mapped ({count} ref(s))")
        cited_ambiguous = {ref.slug for ref in refs} & identities.ambiguous
        if cited_ambiguous:
            notes.append(ambiguity_note(cited_ambiguous))
        ok = not (failed or unserved or self._config_errors)
        return SourceResult(nodes=nodes, ok=ok, note="; ".join(notes))


def _factory(name: str, options: dict) -> Source:
    return TrackerSource(name, options)


DEFAULT.register("tracker", _factory)
