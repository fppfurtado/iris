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


def _config(tmp_path: Path) -> Path:
    a = tmp_path / "alpha"
    a.mkdir()
    b = tmp_path / "beta"
    b.mkdir()
    mr = tmp_path / ".mrconfig"
    mr.write_text(f"[{a}]\ncheckout = x\n\n[{b}]\ncheckout = y\n", encoding="utf-8")
    cfg = tmp_path / "sources.toml"
    cfg.write_text(
        f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mr}"\n\n'
        f'[sources.tracker]\ntype = "tracker"\nmrconfig = "{mr}"\n'
        f'command = ["python3", "-c", "{_FAKE_ISSUES}"]\n',
        encoding="utf-8",
    )
    return cfg


def test_composed_call_equals_manual_direct_call_join(tmp_path):
    config = load_config(_config(tmp_path))

    # ONE composed iris call.
    composed = compose_repo_issues(
        federate(config, Query(kinds=frozenset({KIND_NODES, KIND_HITS})))
    )
    composed_map = {rw.repo.id: sorted(i.id for i in rw.issues) for rw in composed.repos}

    # N direct calls, hand-joined: constellation's repos + the tracker's issues per identity —
    # exactly what a session does by hand today (`iris repos` + `gh issue list` per repo).
    sources = {s.name: s for s in DEFAULT.resolve(config)}
    repos = [
        n.id
        for n in sources["constellation"].read(Query(kinds=frozenset({KIND_NODES}))).nodes
        if n.kind == "repo"
    ]
    tracker = sources["tracker"].read(Query(kinds=frozenset({KIND_NODES})))
    manual: dict[str, list[str]] = {r: [] for r in repos}
    for rel in tracker.relations:
        if rel.type == "has-open-issue" and rel.from_ in manual:
            manual[rel.from_].append(rel.to)
    manual_map = {k: sorted(v) for k, v in manual.items()}

    # The single composed call returns exactly the manual join — the earn datum.
    assert composed_map == manual_map
    assert composed_map == {"alpha": ["alpha#5"], "beta": ["beta#5"]}
