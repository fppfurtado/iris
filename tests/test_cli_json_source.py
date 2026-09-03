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
