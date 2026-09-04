# Spec: repo ⋈ open-issues — the first cross-source composition (iris#31)

- Frozen at: 2026-09-04
- Spec version: v1
- Source: Problem Brief `costura-iris-fonte` v1 (frozen 2026-09-04) — **PRD stage skipped** (craft-call:
  bounded single-feature increment on existing federation architecture; the Brief already carries the
  requirement-level content this increment needs — job F4, constraints C6/C7, and the testable success
  criterion S3/L120 — so a PRD would only restate it). Tasks trace to Brief IDs, not `PR*`.
- Status: frozen after approval on 2026-09-04 (operator "Congelar v1 → build")
- Amendments: none

<!-- Non-normative orientation. This Spec turns iris#31 (Brief candidate F4 — the strongest earn-path)
     into design + task plan. It is the FIRST genuine cross-source composition in iris: today
     `federate()` is fan-out + concat with no join. Scope is ONE join — repo ⋈ its open forge issues —
     keyed on repo identity, honoring the ratified seam rule (C6/R1: iris owns the cross-source
     composition; each source owns its within-source read) and the source-agnostic invariant (C7). -->

## Design

### Architecture

Three moving parts on top of the existing `Source` / `federate()` core; the join is a NEW, separate
composition step so `federate()` stays pure fan-out + isolation.

Data flow:

```
mrconfig (sovereign repo registry)
   ├── constellation.read()  → repo Nodes (id = basename(path))          ─┐
   └── tracker.read()        → issue Nodes (kind="issue")                 │  federate() fan-out
                               + Relations(repo-identity → issue)         ─┘  (isolated, concat)
                                                                              │
                                                    compose_repo_issues() ────┘  (NEW: the join)
                                                                              │
                                                    repo ⋈ open-issues  →  CLI `context` / MCP
```

**Module / bounded-context arrangement** (options → decision → consequences):

- **CHOSEN — independent-read + compose-join.** Both sources read *independently* off the shared
  sovereign repo registry (mrconfig); a dedicated composer (`core/compose.py`) joins their fan-out
  outputs by repo identity. Factor mrconfig path-discovery into a shared `sources/_repos.py` helper
  (constellation's `_repo_paths` moves there; the tracker reuses it — shared derivation, not duplicated
  logic).
  - over **composer-orchestrated (constellation feeds the tracker its repo list at runtime)** — rejected:
    it couples the two sources at read time and *breaks the isolation* `federate()` guarantees (a
    constellation failure would starve the tracker). Independent reads keep each source degradable on its
    own.
  - over **join folded into `federate()`** — rejected: entangles the isolation-fan-out responsibility with
    the cross-source join; keeping the join in its own module keeps `federate()` single-responsibility and
    the join independently testable.
  - Consequence: the tracker re-reads mrconfig via the shared helper (so the join key is *derived
    identically* by both sources — genuinely shared, not coincidental). Isolation preserved end-to-end.

**Interaction affordance / placement** (options → decision → consequences) — the composed unit is
user-facing (CLI + MCP):

- **CHOSEN — upgrade the existing `context` surface from juxtaposition to synthesis.** `context` is already
  the "assemble the integral context" command, explicitly marked *"Fase 1 heuristic … juxtaposition"*;
  rendering each repo followed by its open issues is exactly the synthesis it was scaffolded to grow into,
  and it matches the Brief's own earn phrasing (`iris context <repo>`). The join logic lives in the
  composer (not the command), so CLI and MCP share it.
  - over **a dedicated new command (`iris repo <name>` / `iris issues`)** — rejected for this increment: a
    new top-level surface is unearned while `context` is the declared home for integral context; revisit
    only if a repo-scoped view diverges enough from task-context to warrant its own verb.
  - Consequence: `context` gains issue rendering under each repo; the "Fase 1 heuristic" note is retired
    for the repos section (grounding stays as-is).

### Data model

Reuse the existing graph primitives — **no new model type**:

- An open issue → `Node(id=f"{repo-identity}#{number}", kind="issue", title=<issue title>, source=<tracker
  instance name>)`. The `id` embeds the repo identity so the node is self-locating even detached from its
  relation.
- Its repo membership → `Relation(from_=<repo-identity>, type="has-open-issue", to=<issue node id>)`.
- The composed unit is not persisted — it is assembled on read by `compose_repo_issues()` grouping issue
  nodes under the repo node whose `id` equals the relation's `from_`.

Alternative considered — a dedicated `Issue` dataclass (number, state, url, author) — **rejected (YAGNI)**:
`Node` carries enough (`id`, `title`) for `repo ⋈ open-issues`; only open issues are fetched so `state` is
implicit. Extend the model when a consumer validates a need for more issue fields (armed below).

### Interfaces / contracts

- **`tracker` source** (`src/iris/sources/tracker.py`), registered under type `"tracker"`. Config-driven and
  **source-agnostic** (C7): it declares the forge CLI to invoke (default `gh`, or `glab`) and nothing about
  org/host/instance. `produces = frozenset({KIND_NODES})` (issues are nodes; a `KIND_NODES` query includes
  it, a hits-only query like `ground` skips it — no wasted forge calls). Reuses the `cli_json` runner
  discipline verbatim: injected `runner` for testability, timeout, `IRIS_CALLER` env marker, and
  graceful-degrade (a failing/unauthed/absent forge for a repo → `ok=False` + note, never a raise that
  sinks the federation).
- **Issue resolution = run the forge CLI in each checkout.** For each mrconfig repo path, the tracker runs
  e.g. `gh issue list --state open --limit N --json number,title` with `cwd=<path>` (the `backlog/tracker.py`
  prior-art). The forge repo is resolved from the **checkout's own git remote** — so owner/host/token live
  only in the working copy, never in iris code or `sources.toml`. This is the strongest possible C7 posture.
- **`compose_repo_issues(FederationResult) -> list[RepoWithIssues]`** (`src/iris/core/compose.py`): pure,
  read-only; groups issue nodes under repo nodes by identity, returns repo-ordered units each carrying its
  open issues (empty list when none). Reused by both the CLI `context` command and the MCP adapter (single
  source of truth → no parity drift).

### Tech choices

- **gh/glab via subprocess `--json` (reuse the `cli_json` runner)** — because the forge is *a substitutable
  front over data you own* (Brief F4: the sovereign export is the record; the CLI is the live read), it needs
  no token wired into iris, and gh/glab already resolve the forge from the checkout — over a **forge REST
  client library**, which would pull tokens/hosts into iris, name instances, and duplicate what the CLI does
  (rejected: violates C7 and the sovereignty framing).
- **Repo identity = basename of the mrconfig-registered checkout path, derived identically by both sources**
  — over a **config-declared forge-repo→identity map** (rejected: duplicates the mrconfig source of truth and
  would name repos in config). The residual identity questions (basename collisions across distinct paths;
  a forge name ≠ local dirname; a *declared* canonical-identity protocol) are Brief F6 — deferred + armed
  below, not built here.

### Cross-cutting

- **Isolation:** the tracker degrades per-repo and per-source; a total forge outage yields repos with empty
  issue lists + notes, never a failed `context`.
- **Read-only:** the tracker exposes no write path; extend the read-only guard test (`test_readonly_guard.py`)
  to cover it.
- **C7 / S2 proof:** extend `test_s2_proof.py` so the tracker adapter is asserted to name no org/host/instance
  (the source-agnostic invariant is a *test*, per S2).
- **Telemetry:** `context` already calls `log_request`; the composed path keeps that unchanged.

## Task plan

- **SP-T1: `tracker` source module.** Add `src/iris/sources/tracker.py` (type `"tracker"`, `produces =
  {KIND_NODES}`), reusing the `cli_json` runner discipline (injected runner, timeout, `IRIS_CALLER`, graceful
  degrade). Factor mrconfig path-discovery into `src/iris/sources/_repos.py` and have both constellation and
  the tracker use it. — serves `costura-iris-fonte:F4`, honors C6 (within-source read) —
  acceptance (EARS): "WHEN `federate()` reads a declared `tracker` source, the SYSTEM SHALL emit one
  `Node(kind='issue')` per open forge issue and one `Relation(<repo-identity>, 'has-open-issue', <issue id>)`,
  resolving issues by running the configured forge CLI with `cwd` set to each mrconfig checkout path." +
  "IF the forge CLI is absent, unauthenticated, or times out for a repo, THEN the SYSTEM SHALL record a note
  and `ok=False` for that read and continue, never raising." — deliverable: persisted tests with an injected
  runner (no gh/glab installed), mirroring `test_cli_json_source.py`. — depends on: —
- **SP-T2: `compose_repo_issues` composer.** Add `src/iris/core/compose.py` joining issue nodes under repo
  nodes by identity. — serves `costura-iris-fonte:C6` (iris owns the cross-source composition) —
  acceptance (EARS): "WHEN the composer runs over a `FederationResult`, the SYSTEM SHALL group each
  `kind='issue'` node under the repo node whose `id` equals the relation's `from_`, and return repo-ordered
  units each carrying its open issues." + "IF an issue's repo-identity matches no repo node, THEN the SYSTEM
  SHALL surface it under an `unmatched` note (the F6 identity-miss signal, made visible not swallowed)." —
  deliverable: persisted composer tests. — depends on: SP-T1
- **SP-T3: render the join in `context` (CLI).** Upgrade `context` so each repo prints followed by its open
  issues, via the composer. Retire the repos-section "Fase 1 heuristic" juxtaposition. — serves
  `costura-iris-fonte:F4` —
  acceptance (EARS): "WHEN `iris context <task>` runs with a `tracker` source declared, the SYSTEM SHALL print
  each matched repo followed by its open issues in one pass, off `compose_repo_issues`." — deliverables:
  persisted CLI test (`test_cli_commands.py`); **user-facing doc**: README usage reflects the composed
  `context` output. — depends on: SP-T2
- **SP-T4: MCP parity.** Expose the same composed `repo ⋈ open-issues` over MCP off the same composer (extend
  the context/nodes surface or add a composed tool). — serves `costura-iris-fonte:C4` (cross-harness uniform
  interface) —
  acceptance (EARS, integration-level — producer/consumer parity across the CLI⋈MCP boundary): "WHERE the MCP
  adapter serves the composed context, the SYSTEM SHALL return the SAME `repo ⋈ open-issues` data the CLI
  renders, produced by the SAME `compose_repo_issues` call." — deliverable: persisted MCP test asserting
  CLI/MCP parity (mirror `test_mcp_adapter.py` / `test_s2_proof.py`). — depends on: SP-T2
- **SP-T5: earn-datum + config example + invariant proofs.** (a) A persisted, deterministic equivalence test:
  over a fixture, the composed `context` output equals the hand-joined baseline (repos ∪ per-repo open-issue
  lists) — the buildable half of the S3 earn test. (b) A reproducible one-shot comparison note (1 composed
  `iris context <repo>` call vs the N direct calls `iris repos` + `gh issue list` per repo) recorded for the
  `^dogfd1` audit — the *datum*, not the verdict (the publish/hold call is the operator's, Brief N2). (c) Add
  a source-agnostic `[sources.tracker]` block to `sources.example.toml` (no org/host). (d) Extend
  `test_readonly_guard.py` and `test_s2_proof.py` to cover the tracker adapter (read-only + names no private
  instance). — serves `costura-iris-fonte:S3` (earn datum) + `S2`/C7 (invariant proof) —
  acceptance (EARS): "the SYSTEM SHALL provide a persisted test proving the composed `context` output equals
  the manual repos+per-repo-issues join over the fixture" + "the SYSTEM SHALL prove by test that the tracker
  adapter source names no org/host/instance." — depends on: SP-T3

## Coverage check (every build-relevant Brief ID → ≥1 task)

- `F4` (earn-path composition) → SP-T1, SP-T3, SP-T5
- `C6` (iris owns cross-source composition; sources own within-source read) → SP-T1, SP-T2
- `C4` (uniform cross-harness interface — CLI ⋈ MCP parity) → SP-T4
- `C7` / `S2` (source-agnostic adapter, provable by reading the code) → SP-T1, SP-T5
- `S3` (earn datum for the earn-or-retire gate) → SP-T5
- (No `PR*`: PRD stage skipped — see header. No task without a Brief-ID trace = no scope creep.)

## Deliberate exclusions (from the Brief)

- **F6 — a *declared* cross-store identity protocol** (canonical registry; basename-collision resolution;
  forge-name ≠ local-dirname). This increment joins on the shared basename derivation and makes identity
  *misses* visible (SP-T2 `unmatched` note) rather than resolving them. Value-affirmed, deferred (the Brief
  carries F6 forward as an open question shared with the parent `arranjo.BRIEF`). — `Trigger-source: an
  identity-miss surfaced by the SP-T2 `unmatched` note in real use, OR a second store whose identity does not
  align by basename — fires when the coincidence-free join is empirically insufficient.`
- **A dedicated `Issue` model type** (extra issue fields: state/url/author/labels). Value-affirmed, deferred
  (grow-by-validated-need). — `Trigger-source: a consumer validates a need for an issue field beyond
  id/title — fires when a command/agent composes that field by hand.`
- **N1 — re-deciding the layer's existence / retire arm (R4).** Boundary, out of scope: this Spec builds the
  *earn* candidate; the retire disposition is the Brief's armed N1, downstream of the `^dogfd1` verdict — not
  a deferral of anything this effort would otherwise build.
- **N2 — the publish/hold verdict itself.** Boundary: this Spec produces the earn *datum* (SP-T5); the
  decision is the operator's, on `^dogfd1`.

## Risks / unknowns

- **glab JSON field parity vs gh.** gh `issue list --json number,title` and glab differ in output shape /
  `@me` support (per `backlog/tracker.py` notes). Mitigation: the config-driven `map` (like `cli_json`)
  absorbs field-name differences; SP-T1 tests both shapes via the injected runner.
- **Basename collisions** (two mrconfig repos with the same directory basename). Mitigation: SP-T2 surfaces
  matches transparently; a collision shows as issues grouped under the shared identity — visible, and the
  F6 trigger above fires on it.
- **Forge call cost at scale** (one `gh issue list` per repo across a large mrconfig). Mitigation:
  `produces={KIND_NODES}` skips the tracker for hits-only queries; a repo/tag filter on `context` bounds the
  fan-out. Not optimized further until measured.

## Assumptions & invalidators

- **The checkout's git remote resolves the forge repo for gh/glab.** — invalidated if a mrconfig repo has no
  forge remote (then the tracker degrades that repo to a note — acceptable, not a failure).
- **basename is a good-enough join key for the earn datum.** — invalidated if the earn comparison (SP-T5)
  shows mis-joins material enough to distort the repo⋈issues result → escalate F6 (armed).
- **`gh`/`glab` is present in the environment where iris runs.** — invalidated if not; the tracker degrades to
  notes and `context` still returns repos (isolation holds).

## Open questions

- **F6 (cross-store identity protocol)** — RESOLVED FOR THIS INCREMENT as the shared-basename derivation
  (Interfaces / Tech choices), with the fuller declared protocol deferred + armed (Deliberate exclusions).
  Not re-opened here.
- **Does the composed `context` BEAT N direct calls (the `^dogfd1` earn verdict)?** — explicitly deferred to
  the operator's `^dogfd1` decision (Brief N2); this Spec delivers the datum (SP-T5), not the verdict.
