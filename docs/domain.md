# Domain Model — iris (sovereign agent-context layer)

Source of the ubiquitous vocabulary, aggregates, and **durable domain rules**. The truth of *what always
holds in the domain* — distinct from an effort's frozen Spec, which carries *what we were authorized to
build in that effort* (per-effort acceptance does NOT live here).

## Domain overview

iris is a read-only layer that **federates** context from several sovereign canonicals (a repo registry, a
knowledge base, …) and **composes** them into one uniform, cross-harness read surface (a CLI and an MCP
server). It owns transport and cross-source composition; it never owns a source's data or re-implements a
source's within-source logic. Global premise: **every read is non-mutating** — iris models its inputs as
frozen value objects and exposes no write path to any source.

## Ubiquitous language

### Source
- **Definition:** a read-only adapter that maps one sovereign canonical into iris's normalized model,
  implementing the `Source` protocol (`name`, `produces`, `read(Query)`).
- **Relations:** registered by `type` in the `Registry`; read by `Federation`. Owns its within-source read
  and resolution; never the cross-source composition.

### Federation
- **Definition:** reading every declared source independently and concatenating the results, with per-source
  isolation (a failing source becomes a note, not a crash).
- **Relations:** fan-out over `Source`s; produces a `FederationResult`. Distinct from Composition.

### Composition
- **Definition:** deriving a joined, cross-source unit from the federated results (e.g. `repo ⋈ open-issues`,
  `repo ⋈ referencing-tasks`) — the value iris adds over calling each source directly.
- **Relations:** operates on a `FederationResult`; the seam rule (BR01) assigns it to iris, not to any source.
- **Aliases/Synonyms:** the seam; cross-source join.

### Node
- **Definition:** a federated entity — a repo, a system, a concept, an issue — with `id`, `kind`, `title`,
  `tags`, `roles`, `source`.
- **Relations:** the graph vertex; linked by `Relation`.

### Relation
- **Definition:** a directed edge between two nodes (`from_`, `type`, `to`), keyed by node identity.
- **Relations:** the graph edge; the carrier of a Composition's join (e.g. `has-open-issue`).

### GroundHit
- **Definition:** a grounding excerpt with provenance (`ref`, `excerpt`, `trust`, `age`) from a knowledge
  source.
- **Relations:** the `hits` result-kind; consumed by `ground`.

### Kind
- **Definition:** a result-kind label declaring what a source emits / a caller consumes (`nodes`, `hits`,
  `chain`). `chain` = the live state of the SPECIFIC nodes an item references (issues incl. closed,
  anchors incl. done), distinct from `nodes` (a repo's open satellites).
- **Relations:** drives kind-aware federation (BR07) — a source producing none of a query's kinds is skipped.

### Identity
- **Definition:** the key by which an entity is matched ACROSS sources for a Composition (today: a repo's
  basename, derived identically by every source from the shared sovereign repo registry).
- **Relations:** mediates cross-context joining (BR06). A *declared* cross-store identity protocol beyond the
  shared derivation is an open domain question (Brief F6).

### Repo
- **Parent:** Node (`kind="repo"`).
- **Definition:** a repository entity from the repo-registry source, identified by its checkout basename.

### Issue
- **Parent:** Node (`kind="issue"`).
- **Definition:** a tracker issue from a forge (gh/glab). In a `context` read only OPEN issues are
  modeled, bound to a repo by a `has-open-issue` Relation. In a `chain` read (F6-mínimo, iris#43) a
  SPECIFICALLY-REFERENCED issue is modeled regardless of state, carrying its lifecycle state
  (`roles=["open"]` | `["closed"]`) — closed matters there (a discharged gate in a dependency chain).

### Task
- **Parent:** Node (`kind="task"`).
- **Definition:** a task-list item (a GTD/next-action) from a knowledge base. In a `context` read only
  OPEN tasks are modeled, bound to each repo they name by a `has-task` Relation — repo linkage is not a
  store field but derived from the `<repo>#<number>` references in the task's text (BR06: identity, not a
  carried key); a task naming no repo stays outside the join. In a `chain` read a SPECIFICALLY-REFERENCED
  anchor (`^<id>`) is resolved regardless of state, carrying its lifecycle state (`roles=["open"]` |
  `["done"]`).

## Aggregates and Entities

This domain has **no mutable aggregate / consistency boundary**: iris's model types are frozen, read-only
value objects (it never mutates a source, only reads and composes). The nearest structural wholes are the
`FederationResult` (the concatenated fan-out) and a composed `repo ⋈ open-issues` unit — both *derived on
read*, never persisted, so neither owns an invariant a write could violate. Name an aggregate here only if a
future capability introduces mutable, transactionally-consistent state (none exists today).

## Invariants and business rules (DURABLE)

Stable rules that hold across **all** features — domain knowledge, not derivable from a Spec.

- **BR01 (the seam rule / R1):** iris owns (a) the uniform cross-harness transport (MCP + CLI) and (b) the
  cross-source composition/federation; each source owns its data and its within-source reads/resolution. iris
  RE-EXPOSES a source read (transport) and COMPOSES across sources — it never re-implements a source's logic.
- **BR02 (source-agnostic adapters):** every source adapter is source-agnostic/public by construction — it
  names no private instance (store, org, host); the concrete instance lives only in private config
  (`sources.toml`). Verifiable by reading the adapter code.
- **BR03 (read-only):** iris only reads and composes; no source exposes a write path.
- **BR04 (per-source isolation):** a source that raises or reports failure contributes a note and degrades
  gracefully; one failing source never sinks the federation.
- **BR05 (converge, not sum N+1):** the layer absorbs / derives / federates; it does not duplicate the read
  of a canonical. A surface that only re-exposes a single source's read does not reduce surfaces-to-trust —
  its cost is justified only when composition across >1 source earns it.
- **BR06 (identity-mediated cross-context):** cross-context joining is mediated by resolved identity, never by
  positional or incidental coincidence.
- **BR07 (kind-aware federation):** a query declares the result-kinds it will consume; a source that produces
  none of them is skipped (no wasted read of a discarded result).

> **The line (do not re-own the Spec).** PER-EFFORT acceptance — the EARS conditions of ONE feature — lives
> in that effort's frozen Spec, never copied here. This doc = domain truth; the Spec = what we were
> authorized to build now.
