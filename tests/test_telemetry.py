"""Env-gated request log: writes exactly one well-formed JSON line only when
``IRIS_REQUEST_LOG`` names a path, and is a complete no-op (no file created) when unset —
the invariant that keeps the shipped default read-only by construction."""

from __future__ import annotations

import json
from pathlib import Path

from iris.telemetry import log_request


def test_log_request_writes_one_json_line(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "nested" / "requests.jsonl"  # parent dir does not yet exist
    monkeypatch.setenv("IRIS_REQUEST_LOG", str(log_path))

    log_request("ground", "pro-bono", hits=2, nodes=0, sources=["notes", "constellation"])

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1  # exactly one line

    record = json.loads(lines[0])  # well-formed JSON
    assert record["op"] == "ground"
    assert record["query"] == "pro-bono"
    assert record["hits"] == 2
    assert record["nodes"] == 0
    assert record["sources"] == ["notes", "constellation"]
    assert isinstance(record["ts"], str) and record["ts"]  # ISO-8601 timestamp present


def test_log_request_is_noop_when_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("IRIS_REQUEST_LOG", raising=False)
    would_be = tmp_path / "requests.jsonl"

    log_request("ground", "q", hits=1, nodes=0, sources=[])

    assert not would_be.exists()  # complete no-op: no file created
