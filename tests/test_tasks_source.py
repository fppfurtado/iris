"""arm-a acceptance (iris#29) — the `tasks` source emits task nodes + repo->task relations from the
`<repo>#<n>` references in each task's text, in one CLI invocation, and degrades without sinking."""

from __future__ import annotations

from iris.core.source import KIND_NODES, Query
from iris.sources.tasks import TasksSource

# mneme-shaped task JSON (a top-level array; id=caret slug, text=body).
_TASKS = (
    '[{"id": "aa1", "text": "wire iris#29 into iris#31 — the GTD join"},'
    ' {"id": "bb2", "text": "clean /storage; unrelated to any repo"},'
    ' {"id": "cc3", "text": "chase meta-system#47 and expedidor#317"}]'
)


def test_emits_task_nodes_and_repo_relations_one_call():
    calls: list[list[str]] = []

    def runner(cmd):
        calls.append(cmd)
        return _TASKS

    src = TasksSource("gtd", {"command": ["mneme", "task", "list", "--json"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))

    assert res.ok
    assert sorted(n.id for n in res.nodes) == ["aa1", "bb2", "cc3"]
    assert all(n.kind == "task" for n in res.nodes)
    rels = {(r.from_, r.type, r.to) for r in res.relations}
    # aa1 references iris (twice → one relation); bb2 references nothing; cc3 references two repos.
    assert ("iris", "has-task", "aa1") in rels
    assert ("meta-system", "has-task", "cc3") in rels
    assert ("expedidor", "has-task", "cc3") in rels
    assert [r for r in res.relations if r.to == "bb2"] == []  # no reference → no relation
    # the same-repo double reference (iris#29, iris#31) collapses to ONE relation
    assert len([r for r in res.relations if r.to == "aa1"]) == 1
    # one invocation for the whole list (not one-per-repo like the tracker)
    assert calls == [["mneme", "task", "list", "--json"]]


def test_spaced_heading_or_acronym_hash_is_not_a_reference():
    def runner(cmd):
        # spaced "PR #32", heading "## Contexto", and uppercase-acronym "PR#25"/"P1#3" must NOT read as
        # repo references — only the lowercase-led <slug>#<n> (a checkout-basename-shaped token) does.
        return '[{"id": "x", "text": "PR #32 under ## Contexto; strip/PR#25 P1#3 for beta#5 and pje-2.1#9"}]'

    src = TasksSource("gtd", {"command": ["c"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))
    slugs = {r.from_ for r in res.relations}
    assert slugs == {"beta", "pje-2.1"}  # only the lowercase-led repo-shaped tokens matched


def test_nested_items_path_and_field_map():
    def runner(cmd):
        return '{"data": {"tasks": [{"caret": "z9", "body": "do iris#1"}]}}'

    src = TasksSource(
        "gtd",
        {"command": ["c"], "items": "data.tasks", "map": {"id": "caret", "title": "body"}},
        runner=runner,
    )
    res = src.read(Query(kinds=frozenset({KIND_NODES})))
    assert [n.id for n in res.nodes] == ["z9"]
    assert res.nodes[0].title == "do iris#1"
    assert ("iris", "has-task", "z9") in {(r.from_, r.type, r.to) for r in res.relations}


def test_degrades_on_failure_without_raising():
    def runner(cmd):
        raise RuntimeError("mneme: not found")

    src = TasksSource("gtd", {"command": ["c"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))
    assert not res.ok
    assert res.nodes == []
    assert "unreadable" in res.note


def test_unexpected_shape_degrades():
    def runner(cmd):
        return '{"tasks": []}'  # a dict, but no items path configured → not a list

    src = TasksSource("gtd", {"command": ["c"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))
    assert not res.ok
    assert "unexpected-shape" in res.note


def test_task_without_id_is_skipped():
    def runner(cmd):
        return '[{"text": "no id, references iris#1"}, {"id": "ok", "text": "fine"}]'

    src = TasksSource("gtd", {"command": ["c"]}, runner=runner)
    res = src.read(Query(kinds=frozenset({KIND_NODES})))
    assert [n.id for n in res.nodes] == ["ok"]


def test_produces_nodes_and_chain():
    from iris.core.source import KIND_CHAIN

    assert TasksSource("gtd").produces == frozenset({KIND_NODES, KIND_CHAIN})


# --- F6-T3: chain mode — resolve specific ^anchor to its state (open/done) ---------------------

from iris.core.source import KIND_CHAIN  # noqa: E402

_OPEN = '[{"id": "dogfd1", "text": "review dogfood [DOGFOOD-GATE] gate:dogfood"}, {"id": "other", "text": "x"}]'
_DONE = '[{"id": "mn297done", "text": "mneme open — landed"}]'


def test_chain_resolves_open_anchor_with_gate_text_captured():
    def runner(cmd):
        return _OPEN

    src = TasksSource("gtd", {"command": ["mneme", "task", "list", "--status", "open", "--json"]}, runner=runner)
    res = src.read(Query(text="blocked on ^dogfd1", kinds=frozenset({KIND_CHAIN})))

    assert res.ok
    assert [n.id for n in res.nodes] == ["dogfd1"]  # only the referenced anchor, not the whole queue
    node = res.nodes[0]
    assert node.kind == "task" and node.roles == ["open"]
    assert "gate:dogfood" in node.title  # the gate marker is captured (in the task text)


def test_chain_resolves_done_anchor_via_done_command():
    def runner(cmd):
        return _DONE if "done" in cmd else _OPEN

    src = TasksSource(
        "gtd",
        {
            "command": ["mneme", "task", "list", "--status", "open", "--json"],
            "done_command": ["mneme", "task", "list", "--status", "done", "--json"],
        },
        runner=runner,
    )
    res = src.read(Query(text="see ^mn297done", kinds=frozenset({KIND_CHAIN})))
    assert res.ok and [n.id for n in res.nodes] == ["mn297done"] and res.nodes[0].roles == ["done"]


def test_chain_anchor_not_found_is_not_emitted():
    # An anchor in neither list -> no node (the composer marks it unresolved/unknown).
    def runner(cmd):
        return _OPEN

    src = TasksSource("gtd", {"command": ["mneme", "task", "list", "--json"]}, runner=runner)
    res = src.read(Query(text="ref ^ghost1", kinds=frozenset({KIND_CHAIN})))
    assert res.ok and res.nodes == []


def test_chain_degrades_failing_list_without_sinking():
    def runner(cmd):
        raise RuntimeError("mneme: store missing")

    src = TasksSource("gtd", {"command": ["mneme", "task", "list", "--json"]}, runner=runner)
    res = src.read(Query(text="ref ^dogfd1", kinds=frozenset({KIND_CHAIN})))
    assert not res.ok and "unreadable" in res.note and res.nodes == []
