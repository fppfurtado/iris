"""SP-T2 + iris#29 arm-a acceptance — compose_repo_issues joins issue AND task nodes under repo nodes
by identity, in repo order, and surfaces identity-misses (per satellite kind) under `unmatched` notes."""

from __future__ import annotations

from iris.core.compose import compose_repo_issues
from iris.core.federation import FederationResult
from iris.core.model import Node, Relation


def _repo(name: str) -> Node:
    return Node(id=name, kind="repo", title=name, source="constellation")


def _issue(identity: str, number: int, title: str) -> tuple[Node, Relation]:
    node_id = f"{identity}#{number}"
    return (
        Node(id=node_id, kind="issue", title=title, source="tracker"),
        Relation(from_=identity, type="has-open-issue", to=node_id),
    )


def _task(task_id: str, text: str, *identities: str) -> tuple[Node, list[Relation]]:
    node = Node(id=task_id, kind="task", title=text, source="gtd")
    rels = [Relation(from_=ident, type="has-task", to=task_id) for ident in identities]
    return node, rels


def test_groups_issues_under_their_repo_in_repo_order():
    ia1, ra1 = _issue("alpha", 1, "a1")
    ia2, ra2 = _issue("alpha", 2, "a2")
    ib1, rb1 = _issue("beta", 7, "b7")
    result = FederationResult(
        nodes=[_repo("alpha"), _repo("beta"), ia1, ia2, ib1],
        relations=[ra1, ra2, rb1],
    )
    comp = compose_repo_issues(result)

    assert [rw.repo.id for rw in comp.repos] == ["alpha", "beta"]  # repo order preserved
    assert [n.id for n in comp.repos[0].issues] == ["alpha#1", "alpha#2"]
    assert [n.id for n in comp.repos[1].issues] == ["beta#7"]
    assert comp.unmatched == []
    assert comp.notes == []


def test_repo_with_no_issues_yields_empty_list():
    result = FederationResult(nodes=[_repo("alpha")], relations=[])
    comp = compose_repo_issues(result)
    assert comp.repos[0].repo.id == "alpha"
    assert comp.repos[0].issues == []


def test_identity_miss_surfaced_as_unmatched_not_dropped():
    ig1, rg1 = _issue("ghost", 3, "orphan issue")
    ia1, ra1 = _issue("alpha", 1, "a1")
    result = FederationResult(
        nodes=[_repo("alpha"), ia1, ig1],  # no "ghost" repo node
        relations=[ra1, rg1],
    )
    comp = compose_repo_issues(result)

    assert [n.id for n in comp.repos[0].issues] == ["alpha#1"]
    assert [n.id for n in comp.unmatched] == ["ghost#3"]
    assert comp.notes and "unmatched: 1 open issue" in comp.notes[0]
    assert "ghost" in comp.notes[0]


def test_groups_tasks_under_their_repo_alongside_issues():
    ia1, ra1 = _issue("alpha", 1, "a1")
    t1, rt1 = _task("aa", "work alpha#1", "alpha")
    t2, rt2 = _task("bb", "spans alpha#9 and beta#3", "alpha", "beta")
    result = FederationResult(
        nodes=[_repo("alpha"), _repo("beta"), ia1, t1, t2],
        relations=[ra1, *rt1, *rt2],
    )
    comp = compose_repo_issues(result)

    assert [n.id for n in comp.repos[0].issues] == ["alpha#1"]
    # the task lands under alpha (with the issue) AND under beta — one task, two repos
    assert [n.id for n in comp.repos[0].tasks] == ["aa", "bb"]
    assert [n.id for n in comp.repos[1].tasks] == ["bb"]
    assert comp.unmatched_tasks == []


def test_task_with_no_repo_reference_appears_nowhere():
    # a task carrying no `has-task` relation is outside the join entirely — not under a repo, not unmatched
    t, _ = _task("lone", "clean /storage, no repo")  # no identities → no relations
    result = FederationResult(nodes=[_repo("alpha"), t], relations=[])
    comp = compose_repo_issues(result)
    assert comp.repos[0].tasks == []
    assert comp.unmatched_tasks == []


def test_task_referencing_unknown_repo_surfaces_as_unmatched():
    t, rt = _task("gh", "chase ghost#4", "ghost")  # no `ghost` repo node
    result = FederationResult(nodes=[_repo("alpha"), t], relations=rt)
    comp = compose_repo_issues(result)

    assert comp.repos[0].tasks == []
    assert [n.id for n in comp.unmatched_tasks] == ["gh"]
    note = next(n for n in comp.notes if "outside the constellation" in n)
    assert "ghost" in note


# --- F6-T4: compose_referenced_nodes — item ⋈ referenced-nodes + data-derived blocker marking ---

from iris.core.compose import ReferencedChain, compose_referenced_nodes, is_gate_marked  # noqa: E402
from iris.core.federation import FederationResult  # noqa: E402
from iris.core.model import Node  # noqa: E402


def _chain_result():
    return FederationResult(
        nodes=[
            Node(id="iris#6", kind="issue", title="min scrub", roles=["closed"]),
            Node(id="iris#5", kind="issue", title="public flip", roles=["open"]),
            Node(id="dogfd1", kind="task", title="review dogfood gate:dogfood", roles=["open"]),
        ]
    )


def test_marks_open_refs_as_blockers_closed_as_resolved_nonblocker():
    item = "flip gated on iris#6, ^dogfd1 and iris#5"
    chain = compose_referenced_nodes(item, _chain_result())

    assert isinstance(chain, ReferencedChain)
    assert {n.id for n in chain.resolved} == {"iris#6", "iris#5", "dogfd1"}
    # iris#6 CLOSED -> discharged, NOT a blocker; ^dogfd1 + iris#5 OPEN -> candidate blockers
    assert {n.id for n in chain.blocker_candidates} == {"dogfd1", "iris#5"}
    assert "iris#6" not in {n.id for n in chain.blocker_candidates}
    assert chain.unresolved == []


def test_unresolved_ref_is_unknown_not_clear():
    # iris#99 resolves to no node (fetch failed / unknown). Even with the other refs closed, a
    # non-empty unresolved means "nothing blocks" cannot be asserted (the failure-mode guard).
    result = FederationResult(
        nodes=[Node(id="iris#6", kind="issue", title="done", roles=["closed"])],
        notes=["tracker: chain: 1 ref(s) unreadable"],
    )
    chain = compose_referenced_nodes("iris#6 and iris#99", result)
    assert chain.blocker_candidates == []  # no KNOWN blocker...
    assert chain.unresolved == ["iris#99"]  # ...but an UNKNOWN ref remains -> not 'clear'
    assert any("unreadable" in n for n in chain.notes)


def test_gate_marker_detected_for_presentation_emphasis():
    node = Node(id="dogfd1", kind="task", title="[DOGFOOD-GATE] review; Trigger-source: X", roles=["open"])
    assert is_gate_marked(node)
    assert not is_gate_marked(Node(id="x", kind="task", title="ordinary task", roles=["open"]))


def test_dedups_repeated_refs():
    item = "iris#5 blocks and again iris#5"
    chain = compose_referenced_nodes(item, _chain_result())
    assert [n.id for n in chain.resolved] == ["iris#5"]
    assert [n.id for n in chain.blocker_candidates] == ["iris#5"]
