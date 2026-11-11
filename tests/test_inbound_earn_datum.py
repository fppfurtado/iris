"""SP-T8 (Spec item-inbound-context v2) — the earn datum of ``iris inbound`` on recorded real data.

Fixtures (tests/fixtures/inbound/, decisions/0002 D4): redacted recordings of the knowledge store at the
snapshot commit ``1f760ec``, re-recorded on 2026-11-11 with mneme 0.27.0 (it carries fppfurtado/mneme#344,
heading titles indexed, and #343, tasks resolved per task) over a ``git archive`` of that commit:

    mneme index rebuild --instance <snap>
    mneme backlinks <key> --instance <snap> --json          # for each of the 7 keys
    mneme task list --status open|done --instance <snap> --json

Kept: each record's locator as its file path plus a 12-hex hash of its block slug (a task record keeps its
``#^<anchor>``), its link type; every task of both lists with its text reduced to its ``iris#<n>`` tokens; the
items' forge states (``gh issue view``, 2026-11-11). Nothing else from the private store is committed.

Deciding assumption, shown on the snapshot: 28 open + 2 done tasks, 0 without an ``id``; the one task the
expected sets name (``^8g58ft``, for iris#34) is returned by the store as ``knowledge/gtd.md#^8g58ft``.

Oracle (record-level, parser-independent; it reads the private store, so it lives outside this repo — the
gitignored dossier ``.throughline/dossiers/item-inbound-oracle/oracle_v2.py``), run 2026-11-11 over the same
snapshot and these recordings: positive control PASS (journal/2026/2026-09-08.md:287 maps to a returned
block); for all 7 keys, every raw ``iris#<n>`` line — owner-qualified included, task list included — sits
inside a returned record: TOTAL MISS 0. Per-task scan (raw task lines citing the key) equals the store's task
records for every key (iris#34: ``^8g58ft``; the others: none). Out-of-identity lines (bare ``#<n>``, URL) are
listed by the oracle, not matched (Brief C3): url 0 for every key.

Latency: one live ``iris inbound iris#38`` (worktree build, live config, 2026-11-11): 1.33 s / 1.43 s / 1.34 s.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from iris._present import inbound_context
from iris.config import Config, SourceSpec
from iris.core.federation import federate
from iris.core.model import Node
from iris.core.registry import Registry
from iris.core.source import KIND_CHAIN, Query, SourceResult
from iris.sources._repos import parse_refs
from iris.sources.cli_json import CliJsonSource
from iris.sources.tasks import TasksSource

_FIX = Path(__file__).parent / "fixtures" / "inbound"
_RECORDS = json.loads((_FIX / "records.json").read_text())
_OPEN = (_FIX / "tasks_open.json").read_text()
_DONE = (_FIX / "tasks_done.json").read_text()
_STATES = json.loads((_FIX / "states.json").read_text())


class _RecordedForge:
    """The item's state, as the forge returned it — the ``chain`` read of a ``<repo>#<n>``."""

    name = "tracker"
    produces = frozenset({KIND_CHAIN})

    def read(self, query: Query) -> SourceResult:
        nodes = [
            Node(id=f"{r.slug}#{r.number}", kind="issue", title="", roles=[_STATES[f"{r.slug}#{r.number}"]],
                 source=self.name)
            for r in parse_refs(query.text)
            if r.kind == "issue" and f"{r.slug}#{r.number}" in _STATES
        ]
        return SourceResult(nodes=nodes)


def _store(cmd: list[str]) -> str:
    return json.dumps(_RECORDS[cmd[2]]) if cmd[:2] == ["store", "backlinks"] else "[]"


def _lists(cmd: list[str]) -> str:
    return _OPEN if cmd == ["open"] else _DONE


def _config_and_registry() -> tuple[Config, Registry]:
    registry = Registry()
    registry.register("forge", lambda name, opts: _RecordedForge())
    registry.register(
        "cli-json",
        lambda name, opts: CliJsonSource(name, opts, runner=_store),
    )
    registry.register("tasks", lambda name, opts: TasksSource(name, opts, runner=_lists))
    inbound = {
        "command": ["store", "backlinks", "{key}", "--json"],
        "items": "",
        "map": {"locator": "source", "type": "type"},
        "tasks": "knowledge/gtd.md#^",
        "skip": ["knowledge/gtd.md"],  # the old live setting, left in: `tasks` is classified first
    }
    config = Config(
        sources=[
            SourceSpec(name="tracker", type="forge", options={}),
            SourceSpec(name="mneme", type="cli-json", options={"command": ["store", "search"], "inbound": inbound}),
            SourceSpec(name="gtd", type="tasks", options={"command": ["open"], "done_command": ["done"]}),
        ]
    )
    return config, registry


def _run(key: str):
    config, registry = _config_and_registry()
    return inbound_context(config, key, lambda c, q: federate(c, q, registry))


def _by_file(nodes) -> Counter:
    return Counter(n.id.split("#", 1)[0] for n in nodes)


_NOTE = "knowledge/notes/iris-dogfood-publish-hold-decision-state.md"

# The Spec v2 expected sets: the files are the Spec's (its listed journal dates + the note); the per-file
# split is the recording's, which the oracle confirmed record by record (0 MISS, 0 returned-without-line).
_EXPECTED = {
    "iris#5": ([], {"journal/2026/2026-08-14.md": 1, "journal/2026/2026-09-06.md": 1, "journal/2026/2026-09-10.md": 1,
                    _NOTE: 1}),
    "iris#29": ([], {"journal/2026/2026-09-05.md": 2, "journal/2026/2026-09-06.md": 3, "journal/2026/2026-09-08.md": 1,
                     "journal/2026/2026-09-09.md": 1, _NOTE: 1}),
    "iris#38": ([], {"journal/2026/2026-09-08.md": 2, "journal/2026/2026-09-09.md": 1, _NOTE: 1}),
    "iris#12": ([], {"journal/2026/2026-09-04.md": 2, "journal/2026/2026-09-05.md": 1, "journal/2026/2026-09-08.md": 1,
                     "journal/2026/2026-09-09.md": 1}),
    "iris#34": (["8g58ft"], {"journal/2026/2026-09-04.md": 1, "journal/2026/2026-09-09.md": 1, _NOTE: 1}),
}


def test_recorded_items_compose_exactly_the_expected_sets():
    for key, (tasks, citations) in _EXPECTED.items():
        ctx = _run(key)
        assert [t.id for t in ctx.tasks] == tasks, key
        expected = Counter(citations)
        assert _by_file(ctx.citations) == expected, key  # no extras, no misses, per file
        assert ctx.unknown == [], key
        assert ctx.item is not None and ctx.item.roles == [_STATES[key]], key


def test_spec_record_counts():
    # Spec v2 expected sets: iris#5 → 4 · iris#29 → 8 (v1's 7 + the heading-only block) · iris#38 → 4 ·
    # iris#12 → 5 · iris#34 → 3 citations + task ^8g58ft.
    counts = {key: (len(_run(key).citations), len(_run(key).tasks)) for key in _EXPECTED}
    assert counts == {"iris#5": (4, 0), "iris#29": (8, 0), "iris#38": (4, 0), "iris#12": (5, 0), "iris#34": (3, 1)}


def test_iris34_names_the_citing_task_by_its_anchor_with_its_state():
    ctx = _run("iris#34")
    assert [(t.id, t.roles) for t in ctx.tasks] == [("8g58ft", ["open"])]
    assert "iris#34" in ctx.tasks[0].title  # the title comes from the recorded list (its ref tokens)


def test_prefix_pairs_never_borrow_the_longer_keys_records():
    # Brief C3/S4 on both halves — one rule now, the store's.
    for short, long in (("iris#1", "iris#12"), ("iris#3", "iris#34")):
        a, b = _run(short), _run(long)
        assert not ({n.id for n in a.citations} & {n.id for n in b.citations}), (short, long)
        assert not ({t.id for t in a.tasks} & {t.id for t in b.tasks}), (short, long)
        assert a.citations == [] and a.tasks == []
