"""Env-gated request log — OFF by default, preserving the read-only-by-construction thesis.

iris ships read-only: it never writes to the filesystem as part of serving a read. This
module keeps that true. :func:`log_request` is a COMPLETE no-op unless the operator opts
in by setting ``IRIS_REQUEST_LOG`` to a filesystem path; only then does a read append one
JSON line describing the request (its op, query, and result counts — never the results'
content). Any write failure is swallowed: telemetry must never break a read.

Telemetry lives here, at the adapter boundary (called from ``cli.py`` and ``mcp_adapter.py``)
— never in the federation core, which stays pure.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

_ENV_VAR = "IRIS_REQUEST_LOG"


def log_request(op: str, query: str, hits: int, nodes: int, sources: list[str]) -> None:
    """Append one JSON line describing a request to ``$IRIS_REQUEST_LOG``, if set.

    When ``IRIS_REQUEST_LOG`` is unset this is a complete no-op — no file is created and
    nothing is written, so the shipped default stays read-only by construction. When it is
    set to a path, one line ``{"ts", "op", "query", "hits", "nodes", "sources"}`` is
    appended (parent dirs created if missing). Never raises: any failure to log is swallowed
    so telemetry can never break a read.
    """
    path = os.environ.get(_ENV_VAR)
    if not path:
        return
    try:
        record = {
            "ts": datetime.now().astimezone().isoformat(),
            "op": op,
            "query": query,
            "hits": hits,
            "nodes": nodes,
            "sources": sources,
        }
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        # Telemetry must never break a read — swallow any logging failure.
        pass
