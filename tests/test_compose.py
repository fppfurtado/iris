"""SP-T2 acceptance — compose_repo_issues joins issue nodes under repo nodes by identity, in repo
order, and surfaces identity-misses under an `unmatched` note."""

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
