# iris

**Sovereign, read-only agent-context layer.** A small core that **federates** the context sources you
already trust — a knowledge base, a repo/asset registry, and more — and **serves** a unified view of them
to AI agents through a **CLI** and an **MCP** adapter.

Thesis: *federation of sovereign canonicals + bridges by resolved identity* — integral **by federation, not
by a totalizing store**. iris **owns no data**: it reads each source through that source's own interface and
composes the results. **No write path exists anywhere** — read-only by construction.

Named for Iris — the messenger goddess and the rainbow that bridges realms: federation-by-bridges and
context delivery in one symbol.

## Why

Your context already lives in tools you trust — a notes/knowledge base, a repository manifest, a service
catalog. Copying it into yet another store creates a second source of truth that drifts and locks you in.
iris instead reads each canonical **in place**, through its own read interface, and presents one federated
view. Sovereignty (you keep your data where it is), portability (each source stays independently usable),
and programmatic access (CLI + MCP) are load-bearing, not afterthoughts.

## Install

Requires Python **3.11+**. iris ships two console scripts — `iris` (CLI) and `iris-mcp` (MCP server).

iris is not yet published to a package index, so install from a checkout:

```sh
git clone <this-repo> && cd iris

uv tool install .             # with uv (recommended)
# or
pip install .                # with pip
```

For development (runtime + test deps):

```sh
uv sync --extra dev
uv run iris --help
uv run pytest
```

## Configure — `sources.toml`

iris reads a **`sources.toml`** that declares which sources are active and their per-source options.
Federation reads **only** the declared sources, in order; adding or removing a source is a local edit to
this file (plus one source module for a genuinely new source *type*) — no other module is touched.

Copy the example and adapt it:

```sh
cp sources.example.toml sources.toml          # project-local, gitignored
# or place it at ~/.config/iris/sources.toml   # user-level default
```

### Config discovery

`iris` and `iris-mcp` find the active `sources.toml` so they run from any directory. Precedence,
**most-specific first**:

| # | Location | Purpose |
|---|----------|---------|
| 1 | **`IRIS_CONFIG`** env var | Explicit override — used verbatim; errors if it points nowhere (you asked for that path). |
| 2 | **`./sources.toml`** | Project-local config in the current directory. |
| 3 | **`$XDG_CONFIG_HOME/iris/sources.toml`** (default `~/.config/iris/sources.toml`) | User-level default. |

If none exists, iris errors listing the searched locations. Set `IRIS_CONFIG` or create one of the paths.

### Declaring sources

Each `[sources.<name>]` table declares one source instance. `type` selects the implementation (the registry
maps `type` → factory); the remaining keys are that type's options. Two source types ship built-in:

```toml
# A repo/asset registry from an `mr` manifest + Backstage catalog-info.yaml files.
[sources.constellation]
type = "constellation"
# mrconfig = "~/.mrconfig"   # optional; realpath / symlink-aware

# A generic CLI-JSON source: shell out to ANY command that emits JSON and map its
# fields into the model — this is how you plug a knowledge base or notes tool that
# has a `--json` read, by config, with no code change.
[sources.notes]
type = "cli-json"
command = ["notes", "search", "{query}", "--json"]   # {query} substituted per call
items = "results"                                     # dotted path to the item list
[sources.notes.map]
ref = "id"                                            # dotted paths into each item
excerpt = "summary"
# trust = "meta.status"
# age = "meta.age_days"
```

See [`sources.example.toml`](sources.example.toml) for the annotated reference.

## Use — CLI

```sh
iris repos [--tag <tag>]      # list repos with their tags/roles (optionally filtered)
iris ground "<query>"         # ground a query across federated sources
iris context "<task>"         # assemble the integral context relevant to a task
iris chain "<item text>"      # resolve a work item's cross-repo dependency chain in one shot
```

`chain` parses the `<repo>#<n>` and `^<anchor>` references in a work item's prose, fetches each
referenced node's **live state across the repos** (issues incl. closed, anchors incl. done), and
surfaces the OPEN ones as **candidate blockers** — you judge the actual blocker. Refs it cannot resolve
are shown as **UNKNOWN**, never folded into "clear":

```
## candidate blockers (OPEN — you judge the actual blocker)
  - ^dogfd1  review dogfood…  [gate]
  - iris#5  public flip
## resolved (not blocking)
  - iris#6  [closed]  min scrub
## unknown — could NOT resolve (not confirmed clear)
  - agent-kit#1464
```

`chain` needs the `tracker` source to declare a per-issue `view` command (fetching one issue by number
incl. its state) and, to resolve *done* anchors, the `tasks` source to declare a `done_command` — see
[`sources.example.toml`](sources.example.toml).

`context` **synthesizes** rather than juxtaposes: when a `tracker` source is declared, it joins each
repo with its **open issues** (a genuine cross-source composition — the repo comes from one source, its
issues from another) and renders them together:

```
## repos
meta-system  [meta]
  - meta-system#42  wire the new adapter
  - meta-system#47  pin the dependency
## grounding
…
```

All commands are **read-only**. Diagnostic notes are printed to stderr (prefixed `#`), so stdout stays
clean for piping.

## Use — MCP

`iris-mcp` exposes the **same** federated data off the same core, over MCP (stdio transport, zero infra):

- tool **`ground(query)`** — ground a query across federated sources
- tool **`repos(tag?)`** — list repos with tags/roles
- tool **`context(task)`** — repos ⋈ their open issues plus grounding (the same composed join the CLI renders)
- tool **`chain(item)`** — a work item ⋈ its referenced nodes' live state, with candidate blockers and a distinct `unknown_unresolved` (the same composition the CLI renders)
- resource **`iris://nodes`** — all federated nodes (read-only enumerable)

Point your MCP-capable agent at the `iris-mcp` command. Example client config:

```json
{
  "mcpServers": {
    "iris": { "command": "iris-mcp" }
  }
}
```

The MCP SDK is pinned (`fastmcp>=2,<3`) against upstream API churn.

## Read-only by construction

iris has **no write path** — not in the CLI, not in the MCP adapter, not in any source. Sources are read
through their own interfaces; iris composes, it never mutates. A guard test asserts the exposed MCP surface
stays read-only.

## Status

Phase 1 is **stdio-only** and ships the two built-in source types above. HTTP/remote MCP transport and
additional federated sources grow by validated need (tracked in the issue backlog).

## Development

This repo follows the [**throughline**](AGENTS.md) working discipline — see `AGENTS.md` for the operational
floor (worktree-per-session, PR-per-cycle, review-before-land). Tests:

```sh
uv run pytest
```
