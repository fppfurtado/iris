"""SP-T5 earn-datum — the buildable half of Brief S3: ONE composed iris call
(compose_repo_issues ∘ federate) equals the N-direct-call baseline (repos from constellation +
open issues per repo from the tracker, hand-joined by identity). This is the deterministic proof
that the federation composition returns exactly the union a manual repos+per-repo-issues sequence
returns — the datum the ^dogfd1 earn-or-retire decision reads (the publish/hold verdict is the
operator's, Brief N2)."""

from __future__ import annotations

from pathlib import Path

import iris.sources  # noqa: F401  (register built-in sources)
from iris.config import load_config
from iris.core.compose import compose_repo_issues
from iris.core.federation import federate
from iris.core.registry import DEFAULT
from iris.core.source import KIND_HITS, KIND_NODES, Query

_FAKE_ISSUES = "import json; print(json.dumps([{'number': 5, 'title': 'T'}]))"
# A GTD list whose texts reference repos by <repo>#<n> — the hand-join carrier (iris#29 arm-a).
_FAKE_TASKS = (
    "import json; print(json.dumps(["
    "{'id': 't1', 'text': 'do alpha#9 today'},"
    "{'id': 't2', 'text': 'spans alpha#1 and beta#2'},"
    "{'id': 't3', 'text': 'no repo here, personal errand'}]))"
)


def _config(tmp_path: Path, *, with_tasks: bool = False) -> Path:
    a = tmp_path / "alpha"
    a.mkdir()
    b = tmp_path / "beta"
    b.mkdir()
    mr = tmp_path / ".mrconfig"
    mr.write_text(f"[{a}]\ncheckout = x\n\n[{b}]\ncheckout = y\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    body = (
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mr}"\n\n'
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{mr}"\n'
        f'command = ["python3", "-c", "{_FAKE_ISSUES}"]\n'
    )
    if with_tasks:
        body += f'\n[sources.gtd]\ntype = "tasks"\ncommand = ["python3", "-c", "{_FAKE_TASKS}"]\n'
    cfg.write_text(body, encoding="utf-8")
    return cfg


def test_composed_call_equals_manual_direct_call_join(tmp_path):
    config = load_config(_config(tmp_path))

    # The task the session is assembling context for — names both repos, so both are in scope
    # (iris#36: the tracker fans out only to the repos the query cites).
    task = "reconcile alpha#5 against beta#5"

    # ONE composed iris call.
    composed = compose_repo_issues(
        federate(config, Query(text=task, kinds=frozenset({KIND_NODES, KIND_HITS})))
    )
    composed_map = {rw.repo.id: sorted(i.id for i in rw.issues) for rw in composed.repos}

    # N direct calls, hand-joined: constellation's repos + the tracker's issues per identity —
    # exactly what a session does by hand today (`iris repos` + `gh issue list` per cited repo). The
    # manual baseline reads the tracker under the SAME scoping query, so the equality stays honest.
    sources = {s.name: s for s in DEFAULT.resolve(config)}
    repos = [
        n.id
        for n in sources["constellation"].read(Query(kinds=frozenset({KIND_NODES}))).nodes
        if n.kind == "repo"
    ]
    tracker = sources["tracker"].read(Query(text=task, kinds=frozenset({KIND_NODES})))
    manual: dict[str, list[str]] = {r: [] for r in repos}
    for rel in tracker.relations:
        if rel.type == "has-open-issue" and rel.from_ in manual:
            manual[rel.from_].append(rel.to)
    manual_map = {k: sorted(v) for k, v in manual.items()}

    # The single composed call returns exactly the manual join — the earn datum.
    assert composed_map == manual_map
    assert composed_map == {"alpha": ["alpha#5"], "beta": ["beta#5"]}


def test_composed_gtd_join_equals_manual_hand_cross(tmp_path):
    """arm-a earn datum (iris#29): ONE composed call's repo⋈tasks equals the hand-cross a session does
    today — read `mneme task list`, scan each task for `<repo>#<n>`, file it under that repo."""
    config = load_config(_config(tmp_path, with_tasks=True))

    # ONE composed iris call.
    composed = compose_repo_issues(
        federate(config, Query(kinds=frozenset({KIND_NODES, KIND_HITS})))
    )
    composed_tasks = {rw.repo.id: sorted(t.id for t in rw.tasks) for rw in composed.repos}

    # N direct calls, hand-joined: constellation's repos + the task list, crossed by identity via the
    # `has-task` relations the tasks source derived from each task's text — the manual composition
    # arm-a removes.
    sources = {s.name: s for s in DEFAULT.resolve(config)}
    repos = [
        n.id
        for n in sources["constellation"].read(Query(kinds=frozenset({KIND_NODES}))).nodes
        if n.kind == "repo"
    ]
    gtd = sources["gtd"].read(Query(kinds=frozenset({KIND_NODES})))
    manual: dict[str, list[str]] = {r: [] for r in repos}
    for rel in gtd.relations:
        if rel.type == "has-task" and rel.from_ in manual:
            manual[rel.from_].append(rel.to)
    manual_tasks = {k: sorted(v) for k, v in manual.items()}

    assert composed_tasks == manual_tasks
    # t1 under alpha; t2 under both alpha and beta; t3 (no repo ref) under neither.
    assert composed_tasks == {"alpha": ["t1", "t2"], "beta": ["t2"]}
    assert composed.unmatched_tasks == []
