"""FastMCP adapter — the same federation core, exposed over MCP (read-only).

The tools/resource return the SAME federated data the CLI prints, off the same
``federate()`` core. stdio transport, zero-infra. Version of the MCP SDK is pinned
in pyproject (``fastmcp>=2,<3``) against API churn.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from fastmcp import FastMCP

import iris.sources  # noqa: F401  (registers the built-in sources)
from iris.config import Config, active_config
from iris.core.compose import compose_repo_issues
from iris.core.federation import federate
from iris.core.source import KIND_HITS, KIND_NODES, Query
from iris.telemetry import log_request

mcp = FastMCP("iris")


def _source_names(config: Config) -> list[str]:
    return [spec.name for spec in config.sources]


@mcp.tool()
def ground(query: str) -> list[dict]:
    """Ground a query across federated sources (read-only)."""
    config = active_config()
    result = federate(config, Query(text=query, kinds=frozenset({KIND_HITS})))
    log_request("ground", query, hits=len(result.hits), nodes=0, sources=_source_names(config))
    return [asdict(hit) for hit in result.hits]


@mcp.tool()
def repos(tag: str | None = None) -> list[dict]:
    """List repos with tags/roles, optionally filtered by tag (read-only)."""
    config = active_config()
    result = federate(config, Query(tag=tag, kinds=frozenset({KIND_NODES})))
    nodes = [n for n in result.nodes if n.kind == "repo"]
    if tag:
        nodes = [n for n in nodes if tag in n.tags]
    log_request("repos", tag or "", hits=0, nodes=len(nodes), sources=_source_names(config))
    return [asdict(node) for node in nodes]


@mcp.tool()
def context(task: str) -> dict:
    """Assemble repos ⋈ their open issues AND the tasks that reference them, plus grounding, off the
    SAME composer the CLI uses (read-only)."""
    config = active_config()
    result = federate(config, Query(text=task, kinds=frozenset({KIND_NODES, KIND_HITS})))
    composed = compose_repo_issues(result)
    log_request(
        "context", task, hits=len(result.hits), nodes=len(composed.repos), sources=_source_names(config)
    )
    return {
        # Relevance-scope: drop join-less repos (roster noise) — parity with the CLI (iris#38).
        "repos": [
            {
                "repo": asdict(rw.repo),
                "issues": [asdict(i) for i in rw.issues],
                "tasks": [asdict(t) for t in rw.tasks],
            }
            for rw in composed.repos
            if rw.issues or rw.tasks
        ],
        "unmatched": [asdict(i) for i in composed.unmatched],
        "unmatched_tasks": [asdict(t) for t in composed.unmatched_tasks],
        "grounding": [asdict(hit) for hit in result.hits],
        "notes": result.notes + composed.notes,
    }


@mcp.resource("iris://nodes")
def nodes() -> list[dict]:
    """All federated nodes (read-only enumerable)."""
    result = federate(active_config(), Query(kinds=frozenset({KIND_NODES})))
    return [asdict(node) for node in result.nodes]


def tool_names() -> list[str]:
    """Registered tool names — used by the read-only guard (SP-T6)."""
    return list(asyncio.run(mcp.get_tools()).keys())


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()
