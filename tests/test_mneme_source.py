"""SP-T4 gate: the mneme source returns normalized results from mneme's --json output."""

from __future__ import annotations

import json

from iris.core.source import Query
from iris.sources.mneme import MnemeSource

_CANNED = json.dumps(
    {
        "items": [
            {
                "ref": "journal/2026/x.md#a",
                "title": "T",
                "excerpt": "an excerpt",
                "trust": {"class": "agent-generated", "status": "unverified", "age_days": 3},
            }
        ],
        "entities": [],
        "mode": "query",
    }
)


def test_mneme_source_normalizes_json_into_ground_hits() -> None:
    src = MnemeSource(runner=lambda cmd: _CANNED)
    result = src.read(Query(text="q"))
    assert result.ok
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.ref == "journal/2026/x.md#a"
    assert hit.excerpt == "an excerpt"
    assert "unverified" in hit.trust and "agent-generated" in hit.trust
    assert hit.age == "3d"


def test_mneme_source_reads_via_json_cli() -> None:
    seen: dict[str, list[str]] = {}

    def runner(cmd: list[str]) -> str:
        seen["cmd"] = cmd
        return json.dumps({"items": []})

    MnemeSource(runner=runner).read(Query(text="pro-bono"))
    assert seen["cmd"] == ["mneme", "ground", "--query", "pro-bono", "--json"]
