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
from iris.config import active_config
from iris.core.federation import federate
from iris.core.source import Query

mcp = FastMCP("iris")


@mcp.tool()
def ground(query: str) -> list[dict]:
    """Ground a query across federated sources (read-only)."""
    result = federate(active_config(), Query(text=query))
    return [asdict(hit) for hit in result.hits]


@mcp.tool()
def repos(tag: str | None = None) -> list[dict]:
    """List repos with tags/roles, optionally filtered by tag (read-only)."""
    result = federate(active_config(), Query(tag=tag))
    nodes = [n for n in result.nodes if n.kind == "repo"]
    if tag:
        nodes = [n for n in nodes if tag in n.tags]
    return [asdict(node) for node in nodes]


@mcp.resource("iris://nodes")
def nodes() -> list[dict]:
    """All federated nodes (read-only enumerable)."""
    result = federate(active_config(), Query())
    return [asdict(node) for node in result.nodes]


def tool_names() -> list[str]:
    """Registered tool names — used by the read-only guard (SP-T6)."""
    return list(asyncio.run(mcp.get_tools()).keys())


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()
