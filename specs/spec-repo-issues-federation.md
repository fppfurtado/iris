# Spec: repo ⋈ open-issues — the first cross-source composition (iris#31)

- Frozen at: 2026-09-04
- Spec version: v3 (DRAFT — not frozen)
- Source: Problem Brief `costura-iris-fonte` v1 (frozen 2026-09-04) — **PRD stage skipped** (craft-call:
  bounded single-feature increment on existing federation architecture; the Brief already carries the
  requirement-level content this increment needs — job F4, constraints C6/C7, and the testable success
  criterion S3/L120 — so a PRD would only restate it). Tasks trace to Brief IDs, not `PR*`.
- Status: frozen after approval on 2026-09-04 (operator "Congelar v1 → build"); v2 frozen after approval on
  2026-11-19 (operator "sim"); v3 draft 2026-11-19, awaiting the pre-freeze read and the operator's approval
- Amendments: **v3 (2026-11-19, iris#81).** The tracker serves a registry that spans more than one forge: one
  tracker instance carries an optional per-host table `forges."<host>"` whose keys (`command`, `view`, `items`,
  `map`, `states`) override the top-level ones for the repos whose forge slug has that host; a repo with no
  command for the read's mode (`command` for `context`, `view` for `chain`), from its entry or the top level, is
  UNSERVED and counted unreadable (never skipped silently); and the issue state
  read by `view` is normalised through a `states` value map to the canonical `open` / `closed`, an unmapped value
  carrying no state (UNKNOWN). Why: glab returns `state: "opened"` (probed 2026-11-19 on a real GitLab issue),
  which the old path stored as the role and the chain composer read as discharged — an OPEN issue reported as no
  blocker, silently; and an instance that runs its CLI in every repo fails on the other forge's repos, so a mixed
  registry marked degraded every `chain`/`inbound`/`context` read that named a repo of the other forge, even when
  the answer was right. The v1 Risks claim
  that "the config-driven `map` absorbs" glab differences was false for values: `map` remaps field paths, not
  values. A host now appears in the PRIVATE `sources.toml`; Brief `costura-iris-fonte` C7 allows it ("a instância
  concreta … vive só na config privada"), and the adapter and the public example still name none. Changed:
  Interfaces / contracts (tracker contract; issue resolution); Tech choices (REST rejection reason; new "Forge
  per host"); Cross-cutting (C7 proof); Risks (glab parity); Assumptions. Added: SP-T8 [v3], SP-T9 [v3]. Recommendation
  read twice before drafting (blind-critic J3/J5/J6/J1: 1 High — a multi-instance host filter skipped an unserved
  repo silently, which reversed that option — 7 Medium, 9 Low, all disposed in this text); draft read once
  pre-freeze over the three iris#81 drafts (blind-critic J1/J3/J6: 0 High, 4 Medium, 9 Low), then a delta read of
  the fixes (0 High, 2 Medium, 5 Low); this Spec's findings disposed in this text.
  **v2 (2026-11-19, iris#60; approved by the operator, "sim" to the freeze question).** The repo join identity changes from the
  checkout basename to the repo's **forge name** (the last segment of the forge slug of its `origin`, or of its
  `checkout =` clone URL), with the basename kept only as a fallback for an entry with no slug; a name two
  registry entries would share is ambiguous (refs to it are UNKNOWN); and the tracker can pin its forge CLI to
  that slug (`{slug}`). Changed: Data flow; Tech choices (Repo identity); Deliberate exclusions (F6 narrowed — the
  *forge-name ≠ local-dirname* case is now in scope, the *declared* protocol stays deferred); Risks
  (collisions); Assumptions; Open questions (F6). Added: SP-T6 [v2], SP-T7 [v2]. Pre-freeze read: one blind read (J5/J6/J3/J1), 3
  findings (CLI remote not pinned; collision fallback guessed; `declared_name` rejection under-evidenced), all
  fixed in this draft; the fixes had no reader. Why: the F6 exclusion's
  second trigger arm fired — "a second store whose identity does not align by basename": the knowledge
  store cites repos by forge name (2026-11-19 count over `~/mneme`: 370 refs written `dotfiles#n` /
  `pje-2.2#n` / `relatorios-gestaoclick#n`, 0 written `chezmoi#n` / `pje-2.1#n` / `relatorios-h3#n`), and 3
  of the 31 registry repos have a checkout directory named differently from the forge repo. Observed
  effects: `iris chain dotfiles#67` and `iris chain pje-2.2#2023` → unknown; `iris inbound chezmoi#67` → "no
  records in mneme cite" while the store holds 9 citations under `dotfiles#67` (an undisclosed false
  absence). The forge name is derivable for all 31 (probe 2026-11-19: every entry carries a forge slug; no
  two share a last segment), so no declared protocol is needed for this case (Brief `f6-minimo` N2 —
  "identidade não-inferível" — does not fire). Approval: operator "sim" (2026-11-19).

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
   ├── constellation.read()  → repo Nodes (id = forge name [v2])         ─┐
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
  **source-agnostic** (C7): the adapter names no org, host or instance; the config declares the forge CLI to
  invoke (default `gh`, or `glab`) and, [v3] when the registry spans several forges, which CLI serves which
  host (`forges."<host>"`, private config only — SP-T8). `produces = frozenset({KIND_NODES, KIND_CHAIN})` (issues are nodes; a `KIND_NODES` query includes
  it, a hits-only query like `ground` skips it — no wasted forge calls). Reuses the `cli_json` runner
  discipline verbatim: injected `runner` for testability, timeout, `IRIS_CALLER` env marker, and
  graceful-degrade (a failing/unauthed/absent forge for a repo → `ok=False` + note, never a raise that
  sinks the federation).
- **Issue resolution = run the forge CLI in each checkout.** For each mrconfig repo path, the tracker runs
  e.g. `gh issue list --state open --limit N --json number,title` with `cwd=<path>` (the `backlog/tracker.py`
  prior-art). The forge repo is resolved from the **checkout's own git remote** (or `{slug}`, v2) — so owner and
  token live only in the working copy, never in iris code or `sources.toml`. [v3] A host may appear in the
  private `sources.toml` only as a `forges` key that routes a repo to its CLI; it never enters adapter code or
  the public example (C7).
- **`compose_repo_issues(FederationResult) -> list[RepoWithIssues]`** (`src/iris/core/compose.py`): pure,
  read-only; groups issue nodes under repo nodes by identity, returns repo-ordered units each carrying its
  open issues (empty list when none). Reused by both the CLI `context` command and the MCP adapter (single
  source of truth → no parity drift).

### Tech choices

- **gh/glab via subprocess `--json` (reuse the `cli_json` runner)** — because the forge is *a substitutable
  front over data you own* (Brief F4: the sovereign export is the record; the CLI is the live read), it needs
  no token wired into iris, and gh/glab already resolve the forge from the checkout — over a **forge REST
  client library**, which would pull tokens into iris, name instances in code, and duplicate what the CLI does
  (rejected: violates C7 and the sovereignty framing).
- **[v3] Forge per host = one tracker instance with a `forges."<host>"` table** — matched by exact host; each
  key the entry carries overrides the top-level one, and a key it omits is inherited (the per-key override of
  git's URL-scoped config, `http.<url>.*`).
  Weighed:
  - over **several tracker instances, each with a `hosts` filter** — rejected: an instance that skips a repo
    not on its host cannot tell "not mine" from "nobody's", so a repo no instance serves would vanish silently
    (in `context` it would read as "no open issues"). Making that visible would need the instances to report
    skipped repos and the core to cross-check them — tracker coverage logic in the core. One instance knows every
    host it serves, so UNSERVED is local and cheaper.
  - over **classifying "not my forge" from the CLI's stderr** — rejected: forge vocabulary in the adapter,
    fragile across CLI versions.
  - over **a dispatch script in the private dotfiles** — rejected: it fixes one machine, sits outside iris's
    tests, and re-implements the list-shape mapping.
- **[v3] Issue state = a `states` value map, raw (lowercased) → canonical** — the identity on `open` / `closed`
  always applies beneath a supplied table, and any other value maps to no state (UNKNOWN). Weighed:
  - over **an `open_states` list** — equal cost, and with the composer's vocabulary guard (`f6-minimo` v1.1 F6-T7) both
    fail loud on an unknown value. The map is chosen on a tie-break: it can also name a closed synonym, which a
    list of open values cannot; no forge today returns one (gh `OPEN`/`CLOSED`, glab `opened`/`closed`).
  - over **normalising `opened` in the composer** — rejected: forge vocabulary in the core (BR01/BR02).
- **Repo identity [v2] = the repo's forge name — the last path segment of the forge slug
  (`_repos.forge_slug`) of the checkout's `origin` remote, or, when the checkout is absent, of the clone URL in
  its registry `checkout =` command — derived identically by every source from the shared registry
  (`_repos.identity_map`).** An entry with no forge slug falls back to its checkout basename. A name that two
  or more registry entries would take — forge name against forge name, or a fallback basename against
  another entry's forge name — is **ambiguous**: no entry takes it, each such entry's repo node is keyed by
  its registry path (unique by construction, matched by no `<repo>#<n>` ref), and a ref to the ambiguous name
  resolves to UNKNOWN with a note, never to one of the entries (BR06; Brief `f6-minimo` C3). Weighed:
  - over **the checkout basename (v1)** — rejected by evidence: the knowledge store keys repos by forge name
    (370 vs 0 refs, Amendments), so a basename join misses every repo whose directory was renamed (3 of 31).
    Intrinsic, not swappable: the basename is a local choice the other stores never see.
  - over **the full slug `<host>/<path>`** — rejected: prose refs and the store's key are `<repo>#<n>`, with
    no host or owner, so a full-slug id would match no ref. (The membership check keeps the full slug as its
    own key, unchanged.)
  - over **the descriptor's `metadata.name` (`declared_name`)** — rejected: it equals the forge name for
    every member today (`iris check` on 2026-11-19 reports `name-mismatch` = 0), so it adds no join
    information, and keying the tracker by it would make the tracker read descriptors too — a second owner of
    the constellation's read (BR05). Kept in view for one risk the forge name does not cover: a stale
    `origin` after a forge rename (Assumptions), which the membership check already reports.
  - over **a config-declared map, or accepting the basename as an alias** — rejected: a map names repos in
    config (C7) and duplicates the registry; an alias is unearned (0 refs written with the checkout name) and
    would give one repo two ids in the join.
  The *declared* canonical-identity protocol stays Brief F6 — deferred + armed below.

### Cross-cutting

- **Isolation:** the tracker degrades per-repo and per-source; a total forge outage yields repos with empty
  issue lists + notes, never a failed `context`.
- **Read-only:** the tracker exposes no write path; extend the read-only guard test (`test_readonly_guard.py`)
  to cover it.
- **C7 / S2 proof:** extend `test_s2_proof.py` so the tracker adapter is asserted to name no org/host/instance
  (the source-agnostic invariant is a *test*, per S2). [v3] `test_docs_check.py` also asserts that every
  tracker `forges` key in `sources.example.toml` is a placeholder (`<…>`), the precedent it already holds for
  `forge-repos` and `check.exclude`.
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

- **SP-T6 [v2]: repo identity = forge name.** Add `identity_map(mrconfig) -> dict[Path, str]` to
  `src/iris/sources/_repos.py` — for each registry entry, the last segment of `local_slug(path, checkout)`;
  the checkout basename when the slug is `local:…` or when another entry yields the same forge name — and
  make `constellation` (repo node ids, so `attrs.host` / `hosted-by` follow) and `tracker` (list and chain
  modes) key repos through it. A repo found only under an on-disk root takes the forge name of its own
  `origin` (basename fallback); the membership check keeps joining by `attrs.path` / `attrs.slug`. The tracker
  substitutes `{slug}` (the entry's forge slug `<host>/<path>`) in its configured `command` and `view`, so the
  forge CLI reads the very repo the identity names instead of choosing a remote itself;
  `sources.example.toml` shows `-R {slug}` for gh and `-R https://{slug}` for glab (both probed 2026-11-19). —
  serves
  `costura-iris-fonte:F4`, `f6-minimo:J2` ("token→repo via o registro de repos (identidade por slug)") —
  acceptance (EARS):
  - "WHEN a registry checkout's directory is named `a` and its `origin` is `<host>/<owner>/b`, the SYSTEM
    SHALL key the repo as `b` in the constellation node id, the tracker's issue ids and relations, and the
    `chain` resolution of `b#<n>`";
  - "WHEN a registry checkout is absent, the SYSTEM SHALL derive its forge name from the clone URL in its
    `checkout =` command";
  - "IF an entry has no forge slug, THEN the SYSTEM SHALL key it by its checkout basename";
  - "IF two or more registry entries would take the same name (forge name or fallback basename), THEN the
    SYSTEM SHALL key each such repo node by its registry path, SHALL resolve a ref to that name as UNKNOWN in
    `chain` and `inbound` with a note naming the ambiguous name, and the constellation SHALL emit the same
    note";
  - "WHERE a tracker `command` or `view` carries `{slug}`, the SYSTEM SHALL pass that repo's forge slug in
    its place";
  - "WHEN `iris inbound b#<n>` runs for such a repo, the item SHALL resolve from the tracker AND the store's
    citations of `b#<n>` SHALL be returned in the same result" (the 2026-11-19 split, closed);
  - "the existing tests SHALL pass, with fixtures whose directory equals their forge name unchanged".
  — deliverable: persisted tests in `tests/test_repos_helper.py` (or the module's existing test file),
  `tests/test_tracker_source.py`, `tests/test_constellation_source.py`, plus one CLI-level `inbound` test.
  — depends on: SP-T1
- **SP-T7 [v2]: docs made false by v2.** — serves `costura-iris-fonte:C6` — deliverables: `docs/domain.md`
  (Identity: the `context`/`chain`/`inbound` join identity is the forge name, basename fallback; Repo:
  "identified by its forge name"); the `_repos.py` and `constellation.py` module docstrings ("Node ids stay
  the checkout basename"); `docs/earn-datum-repo-issues.md` "Identity beyond the shared basename" line;
  README wherever it states the identity rule. Acceptance: "no statement in `docs/`, `README.md` or `src/iris/`
  SHALL name the checkout basename as the join identity of `context`/`chain`/`inbound` except as the fallback"
  (statements that a basename is not unique, e.g. `core/membership.py`, stay). — depends on: SP-T6
- **SP-T8 [v3]: forge per host + state values.** In `src/iris/sources/tracker.py`: (a) read an optional
  `forges` table; each key is a host, lowercased on load and matched exactly against the host of the repo's forge
  slug as `forge_slug` normalises it (lowercased, port stripped); two keys equal after lowercasing → the later is
  ignored with a note naming it. An ssh alias stays as written in the slug: keying the alias routes the repo, but
  a CLI given `-R https://{slug}` still cannot reach an alias host, so the remote must carry the real host (as the
  example already says). (b) Per repo, resolve each of `command`, `view`, `items`, `map`, `states` from the
  matching entry, else from the top level; `map` and `states` merge per key over the top level; a `local:` slug
  (no host) uses the top level. (c) UNSERVED, per mode: in `context` a repo with no resolved `command`; in `chain`
  a ref whose repo has no resolved `view`. It adds to the existing unreadable count (`N/M repos unreadable`,
  `chain: N ref(s) unreadable`), sets `ok=False`, and adds ONE note per host (listing how many repos or refs),
  naming the host, or saying `no forge host` for a `local:` slug, and carrying "no `view` command" (chain, the v2 wording) / "no
  `command`" (context, new); the whole-source return ("chain: no `view` command configured (BR04)", `tracker.py`) becomes this per-ref rule. (d) A
  `forges` value that is not a table carrying `command` or `view` (e.g. an unquoted host key that TOML nested) is
  a config error: the entry is ignored. Config errors (here, the duplicate key in (a), and the bad `states`
  target in (e)) are found when the source is built and reported on every read that names ≥1 ref (a read that
  names none spawns nothing and stays `ok=True`, as today): a note naming each key, and `ok=False`, so the
  tracker lands in `degraded` and a broken config is never read as a clean answer. (e) In `chain`, the raw state is lowercased
  and looked up in `states` (keys and targets lowercased on load) over the identity on `open` / `closed`; a
  `states` target outside `open` / `closed` is a config error (that mapping ignored). An unmapped value yields
  `roles=[]` and a note naming the raw value (`state '<raw>' not mapped`); a state that is absent, `null` or
  `""` is MISSING — `roles=[]` and no such note — so a missing field and an unmapped value stay
  distinguishable. (f) The ambiguity note is emitted once per read, as today. — serves
  `costura-iris-fonte:F4`, `costura-iris-fonte:C7`, `f6-minimo:J3` — acceptance (EARS):
  - "WHERE `forges."<h>"` is declared and a repo's slug host is `<h>`, the SYSTEM SHALL run that entry's
    `command` (context) or `view` (chain) for the repo, with its `items` / `map` / `states` merged per key over
    the top level";
  - "WHERE a repo's slug host matches no `forges` key, or its slug is `local:`, the SYSTEM SHALL use the top-level
    keys";
  - "IF a repo has no resolved `command` (context) or a ref's repo has no resolved `view` (chain), THEN the SYSTEM
    SHALL add it to the unreadable count, set `ok=False`, and add one note per host naming it (or `no forge
    host`) that contains "no `view` command" (chain) or "no `command`" (context)";
  - "IF two `forges` keys are equal after lowercasing, THEN the SYSTEM SHALL use the first and ignore the later;
    AND every read naming ≥1 ref SHALL carry a note naming it and `ok=False`";
  - "WHEN a mixed registry is read with every host served, the SYSTEM SHALL return the issues of both forges with
    `ok=True` and no unreadable note";
  - "WHEN `view` returns state `opened` and `states` maps `opened = "open"`, the node SHALL carry `roles=['open']`;
    WHEN it returns `closed` with that same table, `roles=['closed']`; WHEN it returns `OPENED` with `states = {
    Opened = "open" }`, `roles=['open']`; WHEN it returns a value neither `states` nor the identity maps,
    `roles=[]` and a note naming the value; WHEN the `view` JSON's state is absent, `null` or `""`, `roles=[]` and
    no such note" (the two stay distinguishable);
  - "IF a `forges` value carries neither `command` nor `view`, or a `states` target is outside `open` / `closed`,
    THEN the SYSTEM SHALL ignore it, AND every read naming ≥1 ref SHALL carry a note naming its key and
    `ok=False`";
  - "the existing tests SHALL pass unchanged (the no-`view` note keeps its v2 wording)". With no `forges` and no
    `states`, v3 differs from v2 in two deliberate ways only: a chain read with no `view` whose refs all fall
    outside the registry is now `ok=True` (no ref was unserved), and an unserved context repo gets a host note
    beside the count.
  — deliverable: persisted tests in `tests/test_tracker_source.py` (injected runner, two hosts, a `local:` repo),
  one CLI-level `chain` test over a mixed registry. — depends on: SP-T6, `f6-minimo` F6-T7 (the guard the
  `states` choice relies on)
- **SP-T9 [v3]: docs made false by v3.** — serves `costura-iris-fonte:C6`, `C7` — deliverables: the
  `tracker.py` module docstring ("never an org, host, or instance" → the adapter names none; the private config
  may route by host) and its `view` comment (absent → per-ref, not whole-source); `sources.example.toml` (the
  tracker block's "NEVER an org/host/instance" text; the `view` comment "Omit to leave `chain` disabled for this
  source" → a host is chain-enabled by its own or the top-level `view`; an UNCOMMENTED `forges."<forge-host>"` glab entry, so the
  docs check parses it: `glab issue list --output json -R https://{slug}`, `glab issue view
  {number} -F json -R https://{slug}`, `number = "iid"`, `states = { opened = "open" }`); README (the chain
  `view` requirement becomes per host); `docs/domain.md` Issue (canonical state values open|closed; an
  unrecognised value is unknown — this task owns the Issue entry); `tests/test_docs_check.py` placeholder
  assertion for tracker `forges` keys, run over the example as `load_config` parses it, asserting ≥1 key so it
  cannot pass vacuously. Acceptance: "no
  statement in `docs/`, `README.md`, `sources.example.toml` or `src/iris/` SHALL say the config never names a
  host", and the docs check passes with the placeholder assertion. — depends on: SP-T8

## Coverage check (every build-relevant Brief ID → ≥1 task)

- `F4` (earn-path composition) → SP-T1, SP-T3, SP-T5, SP-T6 [v2], SP-T8 [v3]
- `C6` (iris owns cross-source composition; sources own within-source read) → SP-T1, SP-T2, SP-T7 [v2], SP-T9 [v3]
- `C4` (uniform cross-harness interface — CLI ⋈ MCP parity) → SP-T4
- `C7` / `S2` (source-agnostic adapter, provable by reading the code) → SP-T1, SP-T5, SP-T8 [v3], SP-T9 [v3]
- `S3` (earn datum for the earn-or-retire gate) → SP-T5
- (No `PR*`: PRD stage skipped — see header. No task without a Brief-ID trace = no scope creep.)

## Deliberate exclusions (from the Brief)

- **F6 — a *declared* cross-store identity protocol** (canonical registry; forge-name-collision
  resolution). [v2] The *forge-name ≠ local-dirname* case left this exclusion (it fired, see Amendments) and
  is built by SP-T6; the join stays a derivation, and identity *misses* stay visible (SP-T2 `unmatched`
  note). Value-affirmed, deferred (the Brief carries F6 forward as an open question shared with the parent
  `arranjo.BRIEF`). — `Trigger-source: a forge-name collision inside the registry (the SP-T6 note) in real use,
  OR a store whose identity does not align by forge name — fires when the derived join is empirically
  insufficient.`
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
  absorbs field-name differences; SP-T1 tests both shapes via the injected runner. [v3] Field PATHS only: `map`
  does not remap VALUES, and glab's state `opened` was read as discharged. Values go through `states` (SP-T8).
  Flags differ too: glab's JSON switch is `--output json` on `issue list` and `-F json` on `issue view` (on
  `list`, `-F` is `--output-format`) — probed 2026-11-19, shown in the example (SP-T9).
- **Name collisions [v2]** (two registry entries that would take one name, e.g. one forge name on two hosts).
  Mitigation: SP-T6 makes the name ambiguous — no entry takes it, refs to it are UNKNOWN with a note — and the
  F6 trigger above fires on that note. None today (probe 2026-11-19, 31 entries).
- **Forge call cost at scale** (one `gh issue list` per repo across a large mrconfig). Mitigation:
  `produces={KIND_NODES}` skips the tracker for hits-only queries; a repo/tag filter on `context` bounds the
  fan-out. Not optimized further until measured.

## Assumptions & invalidators

- **The checkout's git remote resolves the forge repo for gh/glab.** — invalidated if a mrconfig repo has no
  forge remote (then the tracker degrades that repo to a note — acceptable, not a failure).
- **[v2] The forge name is the key every store cites a repo by.** — invalidated if a store is found keying a
  repo by another name (its directory, a declared alias) → the F6 trigger above fires.
- **[v2] Without `{slug}` in its command, the forge CLI chooses the remote itself.** Today glab picks `origin`
  in the one multi-remote registry checkout (probed 2026-11-19, 4 remotes); a CLI that picked another remote
  would label a different project's issue with this repo's identity. — invalidated by any CLI that does not
  resolve `origin`; mitigated by `{slug}` (SP-T6), which the private config should use.
- **[v2] A checkout's `origin` names the repo's current forge home.** — invalidated by a stale remote after a
  forge rename (the membership check's `stale-remote` kind reports it); until fixed, the old forge name is
  the join identity.
- **[v3] A repo's forge is named by its slug host.** — invalidated by two forges behind one host, or a remote
  written with an ssh alias (it routes only if the alias is keyed, and a `{slug}` CLI cannot reach it; either
  way the read fails loud, never silent).
- **`gh`/`glab` is present in the environment where iris runs.** — invalidated if not; the tracker degrades to
  notes and `context` still returns repos (isolation holds).

## Open questions

- **F6 (cross-store identity protocol)** — RESOLVED FOR THIS INCREMENT as a shared derivation — the forge
  name since v2, the basename in v1 (Tech choices) — with the fuller declared protocol deferred + armed
  (Deliberate exclusions).
- **Does the composed `context` BEAT N direct calls (the `^dogfd1` earn verdict)?** — explicitly deferred to
  the operator's `^dogfd1` decision (Brief N2); this Spec delivers the datum (SP-T5), not the verdict.
