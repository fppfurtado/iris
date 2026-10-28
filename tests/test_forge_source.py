"""SP-T3 gate: the forge-repos source — per-org listing, slugs, archived flag, per-org degradation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import iris.sources.forge as forge_module
from iris.core.source import KIND_UNIVERSE, Query
from iris.sources.forge import ForgeReposSource

UNIVERSE = Query(kinds=frozenset({KIND_UNIVERSE}))
OPTS = {
    "host": "forge.example",
    "orgs": ["org-a", "group"],
    "command": ["forge", "list", "{org}", "--json"],
    "map": {"path": "fullPath", "archived": "isArchived"},
}


def _runner(listings: dict[str, object], calls: list[list[str]]):
    def run(argv: list[str]) -> str:
        calls.append(argv)
        value = listings[argv[2]]
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value)

    return run


def _repos(result) -> dict[str, dict]:
    return {n.attrs["slug"]: n.attrs for n in result.nodes if n.kind == "repo"}


def test_runs_once_per_org_and_emits_slugged_repos() -> None:
    calls: list[list[str]] = []
    listings = {
        "org-a": [{"fullPath": "org-a/one", "isArchived": False}, {"fullPath": "org-a/old", "isArchived": True}],
        "group": [{"fullPath": "group/sub/x", "isArchived": False}],
    }
    result = ForgeReposSource("forge", OPTS, runner=_runner(listings, calls)).read(UNIVERSE)
    assert calls == [["forge", "list", "org-a", "--json"], ["forge", "list", "group", "--json"]]
    repos = _repos(result)
    assert set(repos) == {"forge.example/org-a/one", "forge.example/org-a/old", "forge.example/group/sub/x"}
    assert all(a["origin"] == "forge" for a in repos.values())
    assert repos["forge.example/org-a/old"]["archived"] is True
    assert repos["forge.example/org-a/one"]["archived"] is False
    assert result.ok and not result.note


def test_missing_host_is_not_ok() -> None:
    opts = {k: v for k, v in OPTS.items() if k != "host"}
    result = ForgeReposSource("forge", opts, runner=_runner({}, [])).read(UNIVERSE)
    assert result.ok is False
    assert result.note


def test_one_failing_org_keeps_the_other_and_says_incomplete() -> None:
    for bad in (RuntimeError("boom"), "not json"):
        listings = {"org-a": bad, "group": [{"fullPath": "group/y", "isArchived": False}]}
        result = ForgeReposSource("forge", OPTS, runner=_runner(listings, [])).read(UNIVERSE)
        assert set(_repos(result)) == {"forge.example/group/y"}
        assert result.ok is True
        assert "org-a" in result.note and "incomplete" in result.note


def test_every_org_failing_is_not_ok() -> None:
    listings = {"org-a": RuntimeError("x"), "group": "{bad"}
    result = ForgeReposSource("forge", OPTS, runner=_runner(listings, [])).read(UNIVERSE)
    assert result.ok is False
    assert result.note


def test_module_names_no_org_host_or_instance() -> None:
    source = Path(forge_module.__file__).read_text(encoding="utf-8")
    # No hostname-like literal (``something.tld``) and no forge-org path literal in the module.
    code = re.sub(r'"""[\s\S]*?"""', "", source)
    assert not re.search(r"""["'][a-z0-9-]+\.(com|org|net|io|dev|space|br)\b""", code)
    assert not re.search(r"""["'][a-z0-9-]+/[a-z0-9-]+["']""", code)
    for literal in ("github", "gitlab"):
        assert literal not in source.lower()
