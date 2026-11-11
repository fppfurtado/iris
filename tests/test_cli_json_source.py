"""SP-T4 gate: the generic cli-json source returns normalized results from a configured
--json CLI, per its field-map."""

from __future__ import annotations

import json
import subprocess

from iris.core.source import Query
from iris.sources.cli_json import CliJsonSource, _make_default_runner

_CANNED = json.dumps(
    {
        "items": [
            {"ref": "r1", "excerpt": "E", "trust": {"status": "unverified", "age_days": 3}},
        ]
    }
)

_OPTIONS = {
    "command": ["notes", "search", "{query}", "--json"],
    "items": "items",
    "map": {"ref": "ref", "excerpt": "excerpt", "trust": "trust.status", "age": "trust.age_days"},
}


def test_cli_json_normalizes_via_field_map() -> None:
    src = CliJsonSource("notes", _OPTIONS, runner=lambda cmd: _CANNED)
    result = src.read(Query(text="q"))
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.ref == "r1"
    assert hit.excerpt == "E"
    assert hit.trust == "unverified"  # dotted path trust.status
    assert hit.age == "3d"  # from trust.age_days


def test_cli_json_substitutes_query_in_command() -> None:
    seen: dict[str, list[str]] = {}

    def runner(cmd: list[str]) -> str:
        seen["cmd"] = cmd
        return json.dumps({"items": []})

    CliJsonSource("x", {"command": ["tool", "--q", "{query}", "--json"]}, runner=runner).read(
        Query(text="pro-bono")
    )
    assert seen["cmd"] == ["tool", "--q", "pro-bono", "--json"]


def test_cli_json_name_is_instance_name() -> None:
    assert CliJsonSource("notes", {}).name == "notes"


def test_default_runner_injects_iris_caller_into_subprocess_env(monkeypatch) -> None:
    """The default subprocess runner injects the generic IRIS_CALLER=iris marker into the
    CHILD environment so a source CLI can detect it was invoked by iris."""
    captured: dict[str, object] = {}

    class _Completed:
        stdout = "{}"

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        return _Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    _make_default_runner(1.0)(["some-tool", "--json"])

    env = captured["env"]
    assert env["IRIS_CALLER"] == "iris"
    # generic: merged OVER a copy of the parent environment, not a special-cased one
    assert "PATH" in env


# --- SP-T3: inbound mode — the records citing a key ----------------------------------------------

from iris.config import Config, SourceSpec  # noqa: E402
from iris.core.federation import federate  # noqa: E402
from iris.core.registry import Registry  # noqa: E402
from iris.core.source import KIND_HITS, KIND_INBOUND  # noqa: E402

_INBOUND = {
    "command": ["notes", "backlinks", "{key}", "--json"],
    "items": "",
    "map": {"locator": "source", "type": "type"},
    "skip": ["lists/tasks.md"],
}
_RECORDS = json.dumps(
    [
        {"source": "journal/2026-09-08.md#a-block", "type": "refs"},
        {"source": "lists/tasks.md", "type": "refs"},
        {"source": "notes/decision.md", "type": "refs"},
    ]
)


def test_inbound_substitutes_key_and_emits_citations_minus_skip() -> None:
    seen: dict[str, list[str]] = {}

    def runner(cmd: list[str]) -> str:
        seen["cmd"] = cmd
        return _RECORDS

    src = CliJsonSource("notes", {**_OPTIONS, "inbound": _INBOUND}, runner=runner)
    res = src.read(Query(text="iris#34", kinds=frozenset({KIND_INBOUND})))
    assert res.ok
    assert seen["cmd"] == ["notes", "backlinks", "iris#34", "--json"]
    assert [(n.kind, n.id, n.title, n.roles) for n in res.nodes] == [
        ("citation", "journal/2026-09-08.md#a-block", "journal/2026-09-08.md#a-block", ["refs"]),
        ("citation", "notes/decision.md", "notes/decision.md", ["refs"]),
    ]
    assert res.hits == []


def test_without_inbound_stanza_produces_lacks_inbound_and_is_not_read() -> None:
    calls: list[list[str]] = []

    def runner(cmd: list[str]) -> str:
        calls.append(cmd)
        return json.dumps({"items": []})

    plain = CliJsonSource("notes", _OPTIONS, runner=runner)
    assert KIND_INBOUND not in plain.produces
    assert KIND_INBOUND in CliJsonSource("notes", {**_OPTIONS, "inbound": _INBOUND}).produces

    registry = Registry()
    registry.register("cli-json", lambda name, opts: plain)
    config = Config(sources=[SourceSpec(name="notes", type="cli-json", options={})])
    federate(config, Query(text="iris#34", kinds=frozenset({KIND_INBOUND})), registry)
    assert calls == []
    # the hits path is unchanged for that instance
    federate(config, Query(text="q", kinds=frozenset({KIND_HITS})), registry)
    assert calls == [["notes", "search", "q", "--json"]]


def test_inbound_failure_or_non_array_degrades_without_raising() -> None:
    def boom(cmd: list[str]) -> str:
        raise RuntimeError("store missing")

    failed = CliJsonSource("notes", {**_OPTIONS, "inbound": _INBOUND}, runner=boom).read(
        Query(text="iris#34", kinds=frozenset({KIND_INBOUND}))
    )
    assert not failed.ok and "unreadable" in failed.note and failed.nodes == []

    shaped = CliJsonSource("notes", {**_OPTIONS, "inbound": _INBOUND}, runner=lambda cmd: '{"a": 1}').read(
        Query(text="iris#34", kinds=frozenset({KIND_INBOUND}))
    )
    assert not shaped.ok and "not an array" in shaped.note


# --- SP-T9 (Spec v2): the ``tasks`` locator prefix — the store names the citing tasks -------------

_TASKS_INBOUND = {**_INBOUND, "tasks": "lists/tasks.md#^"}
_TASK_RECORDS = json.dumps(
    [
        {"source": "journal/2026-09-08.md#a-block", "type": "refs"},
        {"source": "lists/tasks.md#^8g58ft", "type": "refs"},
        {"source": "lists/tasks.md#^", "type": "refs"},
        {"source": "lists/tasks.md#^Not-An-Anchor", "type": "refs"},
        {"source": "lists/tasks.md", "type": "refs"},
    ]
)


def _read(inbound: dict, records: str):
    src = CliJsonSource("notes", {**_OPTIONS, "inbound": inbound}, runner=lambda cmd: records)
    return src.read(Query(text="iris#34", kinds=frozenset({KIND_INBOUND})))


def test_tasks_prefix_emits_task_nodes_by_anchor_not_citations() -> None:
    res = _read({**_TASKS_INBOUND, "skip": []}, json.dumps([{"source": "lists/tasks.md#^8g58ft", "type": "refs"}]))
    assert res.ok
    assert [(n.kind, n.id, n.title, n.roles) for n in res.nodes] == [("task", "8g58ft", "", [])]
    assert res.note == ""


def test_without_tasks_prefix_every_record_is_as_sp_t3() -> None:
    res = _read({**_INBOUND, "skip": []}, json.dumps([{"source": "lists/tasks.md#^8g58ft", "type": "refs"}]))
    assert [(n.kind, n.id) for n in res.nodes] == [("citation", "lists/tasks.md#^8g58ft")]


def test_prefix_without_an_anchor_remainder_is_a_citation_with_a_note() -> None:
    res = _read({**_TASKS_INBOUND, "skip": []}, _TASK_RECORDS)
    kinds = [(n.kind, n.id) for n in res.nodes]
    assert ("task", "8g58ft") in kinds
    assert ("citation", "lists/tasks.md#^") in kinds
    assert ("citation", "lists/tasks.md#^Not-An-Anchor") in kinds
    assert "tasks prefix" in res.note and "lists/tasks.md#^" in res.note


def test_tasks_is_classified_before_skip() -> None:
    # The leftover ``skip`` of the task file also covers the task records; they are still tasks.
    res = _read(_TASKS_INBOUND, _TASK_RECORDS)
    assert ("task", "8g58ft") in [(n.kind, n.id) for n in res.nodes]
    # A record ``tasks`` does not claim keeps the ``skip`` behaviour.
    assert "lists/tasks.md" not in [n.id for n in res.nodes]
