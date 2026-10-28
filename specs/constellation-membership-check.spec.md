# Spec: constellation membership & drift check — Resources, resource dependencies, explicit universe

- Frozen at: — (withheld, draft)
- Spec version: — (withheld pending approval)
- Source: iris#48 (requirements 1–4 and its out-of-scope paragraph). The problem framing and the arrangement
  that assigns this capability to iris are upstream of this repo and private; iris#48 restates the
  requirements generically, and this Spec cites them as `Q1`–`Q4` (the issue's numbered items) plus `Q4a`–`Q4f`
  (the six bullets of item 4, in order). **PRD stage skipped** (craft-call, as in this repo's earlier Specs: a
  bounded increment inside an existing product; iris#48 already carries requirement-level content, so a PRD
  would only restate it).
- Status: DRAFT — freeze pending approval
- Amendments: none

<!-- Non-normative orientation. Today the constellation source reads the mrconfig and the FIRST document
     of each catalog-info.yaml, and turns every spec.dependsOn into an untyped relation. This increment
     (1) reads `kind: Resource` entities and typed `dependsOn: resource:` refs, (2) widens the repo universe
     beyond the mrconfig — on-disk roots and forge orgs — for a dedicated universe-kind read, and (3) adds a
     read-only `iris check` command that reports membership drift as a closed set of drift kinds, with an
     exit code a scheduler can act on. Scheduling, liveness alerting and issue-on-drift stay with whoever
     deploys the check (iris#48 out-of-scope). -->

## Design

### Architecture

```
sources.toml ──► constellation (mrconfig [+ roots, universe-kind only]) ─┐
                 forge-repos   (one CLI call per configured org)        ─┤ federate(kinds={nodes,universe})
                                                                          │   (BR04 isolation, BR07 routing)
                 [check] table: exclusions, mirrors ──────────────┐      │
                                                                   ▼      ▼
                                              core/membership.py: compose_membership() → DriftReport
                                                                   │
                                                     CLI `iris check` (text | --json, exit 0/1/2)
```

**Module / bounded-context arrangement** (options → decision → consequences):

- **CHOSEN — constellation extended (descriptor parsing + on-disk roots) + a NEW `forge-repos` source + a
  NEW composer module `core/membership.py`.**
  - Descriptor parsing (multi-document, `kind: Resource`, typed `dependsOn`) moves to a shared helper
    `sources/_catalog.py`, used by the constellation source for both mrconfig repos and on-disk repos.
  - On-disk roots are an option of the constellation source. The local filesystem is the same canonical it
    already reads, so no new external dependency is added.
  - The forge is a separate source: a different external dependency (a forge CLI over the network) that must
    degrade on its own (BR04).
  - The drift computation is a composition across sources (BR01: iris owns the composition), so it lives in
    the core. It goes in its own module and not in `core/compose.py`, which holds the `context`/`chain`
    joins: a different consumer and a different result type.
  - over **a separate `repo-roots` source for the disk scan** — rejected: it would re-read the same local
    canonical as constellation and duplicate the descriptor read for every repo present in both. The
    swappable part (where the scan code sits) is not the issue; the intrinsic cost is two sources owning
    one canonical, against BR05.
  - over **folding the forge listing into constellation** — rejected: a network failure on the forge would
    then sink the mrconfig read that `repos`/`context` depend on (BR04 breach). This is intrinsic to sharing
    one `read()`.
  - over **a standalone check script outside the federation** (read config, call helpers directly) —
    rejected: it bypasses per-source isolation and config-driven sources (BR02/BR04), and would be a second
    entry point owning the same reads (BR05).
  - over **computing drift inside the constellation source** — rejected: drift needs the forge data too, so
    it is a cross-source composition by definition (BR01).
  - Consequence: `repos`, `context` and `chain` are untouched. Their queries do not ask for the new
    universe kind, so the forge source is skipped (BR07) and constellation returns its mrconfig set exactly
    as today. New resource nodes are filtered out by every existing consumer (`n.kind == "repo"`, verified in
    `core/compose.py`, `_present.py`, `mcp_adapter.py`).

**Interaction affordance / placement:** not applicable. There is no UI surface; the CLI command is a
headless read whose primary consumer is a scheduler (exit code + JSON) and secondarily a human (text).

### Data model

- **`Node.attrs`** — new optional field `attrs: dict = field(default_factory=dict)` on the existing frozen
  `Node`. It carries source facts the check needs:
  - `path` (str, local checkout);
  - `descriptor` (bool);
  - `origin` (`"mrconfig"` | `"disk"` | `"forge"`);
  - `archived` (bool, forge only);
  - `exists` (bool, mrconfig entries);
  - `remote_name` (str, local checkouts: the last path segment of the `origin` remote URL with any `.git`
    suffix removed, read from `.git/config` without a subprocess; absent when there is no `origin`);
  - `declared_name` (str, the descriptor's Component `metadata.name`, when a descriptor exists);
  - `lifecycle` (str, the descriptor's `spec.lifecycle`, when present).

  It is backward compatible, since every existing constructor call omits it. `Node` is already unhashable
  (list fields), so a dict field changes nothing there.
- **Resource node** — `Node(kind="resource", id=<metadata.name>, title=<metadata.description or name>,
  roles=[spec.type] if any, source=<source name>, attrs={"host": <repo identity>})`. Its relation is
  `Relation(from_=<resource id>, type="hosted-by", to=<repo identity>)`.
- **Typed dependency** — each `spec.dependsOn` entry of the Component document is parsed as a Backstage
  entity ref `[<kind>:][<namespace>/]<name>`. It becomes `Relation(from_=<repo>, type="dependsOn",
  to=<the raw ref string>)`, keeping the current shape so the existing test and readers hold. A helper
  `parse_entity_ref(ref) -> (kind | None, namespace | None, name)` is the single interpretation point.
  Resource identity is the bare `name` (namespace ignored: a personal constellation has one namespace).
- **Host-end declaration** — a Resource document MAY carry Backstage's `spec.dependencyOf` (entity refs of
  its consumers). It is read with the same `parse_entity_ref` and kept on the resource node as
  `attrs.dependency_of` (list of consumer names). Where present, it is the host end of the declaration that
  the consumers' `dependsOn: resource:<name>` must match.
- **Membership identity** — the composer keys a local checkout by `remote_name` when present, else by the
  checkout basename, and a forge repo by its listed name. This is the check's join key only: `_repos.identity`
  (the basename) stays the key of `context`/`chain`, which this increment does not touch. A forge repo listed
  in two orgs or forges under one name is one identity (a mirror), not a duplicate.
- **DriftItem** — `(kind: str, subject: str, detail: str)`. `kind` is from the closed set below.
- **DriftReport** — `items: list[DriftItem]`, `skipped: list[str]` (dimensions that could not run, with
  why), `counts: dict[str, int]` (members, archived, excluded, resources, dependencies).

**Drift kinds (closed set)** and the requirement each serves:

| kind | fires when | serves |
|---|---|---|
| `undeclared-member` | a local checkout (mrconfig or roots) has no descriptor and is not on the exclusion list | Q4a |
| `uncloned` | a forge repo, not archived and not excluded, has no local checkout in the universe | Q3, Q4a |
| `phantom` | an mrconfig entry's path does not exist on disk | Q4b |
| `unregistered` | a member (local checkout with a descriptor, not archived) is absent from the mrconfig | Q4b |
| `archived-host` | a Resource is hosted by a repo the forge reports archived | Q4c, Q4d |
| `dangling-dependency` | a `dependsOn: resource:<x>` names no Resource `<x>` declared anywhere in the universe | Q4d |
| `one-end-only` | a Resource that declares `dependencyOf` and its consumers disagree: a listed consumer lacks `dependsOn: resource:<x>`, or a repo with `dependsOn: resource:<x>` is not listed | Q4e |
| `archived-registered` | a repo the forge reports archived is still an mrconfig entry (a new machine would re-clone it) | Q4c |
| `name-mismatch` | a member's descriptor `metadata.name` differs from its membership identity (a rename not carried into the descriptor) | Q4a, Q4c |
| `exclusion-invalid` | an exclusion entry has an empty reason, or names no repo in the universe — the "names no repo" half is suppressed while the forge dimension is skipped, since the repo may be forge-only | Q4f |
| `exclusion-promoted` | an excluded repo carries a descriptor | Q4f |
| `mirror-missing` | a member (not archived) is not listed in a configured mirror | Q4a (mirror) |
| `mirror-stale` | a name a mirror lists is not a member, or is archived | Q4a, Q4c |
| `duplicate-identity` | two different local paths share one membership identity | BR06 |

"Member" means: a repo in the universe whose local checkout carries a `catalog-info.yaml` (membership =
having a descriptor). An archived repo is never counted as a live member. A Resource with no dependent is
not drift when it declares no `dependencyOf`: a resource can be legitimately unshared. An archived repo's
descriptor `lifecycle` is not checked: an archived forge repo is read-only, so its descriptor cannot be
updated after archiving; the forge `archived` flag is the source of truth for that state, and the drift it
must catch is the mrconfig entry that would revive it (`archived-registered`).

### Interfaces / contracts

- **Config — constellation source options** (all optional; omitted = today's behavior):
  ```toml
  [sources.constellation]
  type = "constellation"
  # mrconfig = "~/.mrconfig"
  roots = ["~/src", "~/projects"]   # scanned ONLY for a universe-kind query
  depth = 2                          # max directory depth below each root (default 2)
  ```
  Disk scan rule: a directory is a checkout iff it contains a `.git` **directory** (a `.git` file is a
  linked worktree and is skipped). The scan does not descend into a found checkout, and it skips any
  directory named `.worktrees`. Symlinks are not followed. A root that is itself a checkout counts as one
  (so a single repo kept outside any projects tree can be listed as its own root).
- **Config — forge source** (new `type = "forge-repos"`; names no org in code, BR02):
  ```toml
  [sources.forge]
  type = "forge-repos"
  orgs = ["<org-or-group>", "..."]                                  # private config only
  command = ["gh", "repo", "list", "{org}", "--json", "name,isArchived", "--limit", "1000"]
  # items = ""                                                      # dotted path to the list
  [sources.forge.map]
  name = "name"          # glab: "path"
  archived = "isArchived" # glab: "archived"
  ```
  Several forges = several instances of this type (e.g. `[sources.forge-a]` with a `gh` command and
  `[sources.forge-b]` with a `glab` command), as the registry already allows.
  One invocation per org, `{org}` substituted. A failing org contributes a note naming the org and marks the
  forge dimension incomplete; the other orgs still count (BR04 at org granularity). The source produces
  only `universe`.
- **Config — `[check]` table** (new; read by `load_config` into `Config.check: dict`):
  ```toml
  [check.exclude]          # repos that are knowingly NOT members: identity = reason
  some-study-repo = "study"
  some-fork = "third-party"
  [[check.mirrors]]        # human-maintained member lists that must mirror membership
  path = "~/path/to/charter.md"
  pattern = '(?<!~~)`([a-z0-9][a-z0-9._-]*)`(?!~~)'   # group 1 = a listed name
  ```
  No default exclusions and no default mirrors.
- **Kind** — new `KIND_UNIVERSE = "universe"` in `core/source.py`. Constellation declares
  `produces = {nodes, universe}`; forge-repos declares `{universe}`. On a query whose kinds include
  `universe`, constellation adds the on-disk repos and resource nodes for every descriptor it reads. On a
  query without `universe`, it returns exactly today's result plus Resource nodes and typed relations for
  mrconfig repos (harmless to consumers, which filter `kind == "repo"`).
- **Composer** — `compose_membership(result: FederationResult, check: dict) -> DriftReport`, pure (no I/O
  except reading mirror files, which it reports as `skipped` on failure).
- **CLI** — `iris check [--json]`:
  - text: one `## <kind>` section per non-empty kind with `- <subject>  <detail>` lines, then
    `# skipped: <dimension> — <why>` notes on stderr, then a one-line summary;
  - `--json`: `{"drift": [{"kind","subject","detail"}], "skipped": [...], "counts": {...}}`;
  - exit code: **0** = no drift and every dimension ran; **1** = at least one drift item (whether or not
    something was skipped); **2** = no drift found but at least one dimension was skipped (never reported
    as clean).
  - Telemetry: one `log_request("check", ...)` like the other commands.

### Tech choices

- **PyYAML `safe_load_all`** (already a dependency) for multi-document descriptors — over a Backstage
  catalog library: none exists in the Python stack, and the entity-ref grammar needed is one regex-sized
  helper.
- **Forge CLIs (`gh`/`glab`) via a configured command**, the pattern the tracker source already uses —
  over direct REST calls: REST would need token handling and per-forge clients in iris, while the CLIs
  already hold the user's auth (and BR02 keeps the instance in config). The pattern is proven in this repo.
- **Filesystem walk with `os.scandir`** (stdlib) — over `git` subprocess discovery (`git rev-parse` per
  directory): the `.git`-directory test is exact for this purpose and costs no process per directory.

### Cross-cutting

- **Fail-honest:** a dimension that could not run (forge unreachable, a mirror file unreadable, no roots
  configured while `uncloned` needs a universe beyond the mrconfig) is listed in `skipped` and drives exit 2.
  It is never folded into "clean".
- **Read-only (BR03):** no command writes anything; the check reports only.
- **Source-agnostic (BR02):** no org, host, path or repo name appears in code, defaults, tests' expected
  output or docs examples beyond placeholders. Test fixtures use neutral names.

### Durable invariants

Not applicable as a new cross-cutting invariant. The rules this increment establishes (membership =
having a descriptor; the closed drift-kind set; fail-honest exit 2) each live at one chokepoint
(`compose_membership` / the `check` command), not across a set of surfaces. They are recorded as domain
rules in the glossary (SP-T7), without a carrier. Existing BR02/BR04/BR07 apply unchanged.

## Task plan

- SP-T1: shared descriptor parser `sources/_catalog.py` — `parse_descriptor(path)` returns the Component
  metadata (first mapping doc whose `kind` is absent or `Component`), the list of Resource docs, and the raw
  `dependsOn` refs; plus `parse_entity_ref(ref)`. Rewire `constellation._node_from_catalog` onto it and emit
  Resource nodes + `hosted-by` relations; add `Node.attrs`. Rewrite the constellation module docstring to
  the new behavior (replace, not stack). — implements Q1, Q2 — acceptance (EARS):
  - "WHEN a descriptor holds a Component and two Resource documents, the source SHALL emit one repo node,
    two `resource` nodes with `attrs.host` = the repo identity, and two `hosted-by` relations";
  - "WHEN `dependsOn` holds `resource:erp-account`, `component:default/x` and `y`, `parse_entity_ref`
    SHALL return `("resource", None, "erp-account")`, `("component", "default", "x")`, `(None, None, "y")`";
  - "the existing constellation tests SHALL pass unchanged";
  - "WHEN the first document is a Resource and a later one the Component, the repo node SHALL still carry
    the Component's metadata";
  - "WHEN a Resource declares `spec.dependencyOf: [component:a, b]`, its node SHALL carry
    `attrs.dependency_of == ["a", "b"]`".
  Persisted tests in `tests/test_catalog.py` + `tests/test_constellation_source.py`. — depends on: —
- SP-T2: constellation `roots`/`depth` options + universe-kind behavior + `KIND_UNIVERSE`. Repo nodes carry
  `attrs` (`path`, `descriptor`, `origin`, and `exists` for mrconfig entries). — implements Q3, Q4b —
  acceptance (EARS):
  - "WHEN a query's kinds include `universe`, the source SHALL add every checkout found under the roots
    within `depth`, with `origin="disk"`";
  - "WHEN a configured root is itself a checkout, it SHALL be reported as one";
  - "WHEN a query's kinds exclude `universe`, the source SHALL return the same repo node set as before
    this change";
  - "IF a directory contains a `.git` file (not directory), THEN it SHALL NOT be reported as a checkout";
  - "the scan SHALL NOT descend into a found checkout nor into a `.worktrees` directory";
  - "IF an mrconfig path does not exist, THEN its node SHALL carry `attrs.exists=False`";
  - "WHEN a checkout's `.git/config` has `[remote "origin"] url = git@host:org/real-name.git` and the
    directory is named `other`, its node SHALL carry `attrs.remote_name == "real-name"`";
  - "a local node with a descriptor SHALL carry `attrs.declared_name` and, when present, `attrs.lifecycle`".
  Persisted tests with a tmp tree. — depends on: SP-T1
- SP-T3: `forge-repos` source (`sources/forge.py`, registered as `forge-repos`). — implements Q3, Q4c —
  acceptance (EARS):
  - "WHEN configured with two orgs, the source SHALL run the command once per org with `{org}`
    substituted and emit one `repo` node per listed repo with `origin="forge"` and `attrs.archived` from
    the mapped field";
  - "IF one org's command fails or emits invalid JSON, THEN the source SHALL still return the other org's
    repos, with `ok=True` and a note naming the failing org and the word `incomplete`";
  - "IF every org fails, THEN `ok=False` with a note";
  - "the module SHALL contain no org, host or instance literal" (grep test over the module source, the
    BR02 check).
  Persisted tests with a fake command. — depends on: SP-T2
- SP-T4: `[check]` table in config — `Config.check` (default `{}`), `exclude` and `mirrors` parsed as
  given. — implements Q4f, Q4a (mirror) — acceptance (EARS):
  - "WHEN `sources.toml` has a `[check]` table, `load_config` SHALL expose it as `Config.check`";
  - "WHEN it has none, `Config.check` SHALL be `{}` and every existing config test SHALL pass".
  Persisted test in `tests/test_config.py`. — depends on: —
- SP-T5: `core/membership.py` — `compose_membership(result, check) -> DriftReport` computing every kind in
  the closed set, plus the `skipped` list. — implements Q3, Q4a–Q4f — acceptance (EARS), one persisted
  fixture test per kind in `tests/test_membership.py`:
  - "WHEN the fixture contains exactly one instance of a drift kind, the report SHALL contain exactly one
    item of that kind with that subject" (one case per kind, 14 kinds);
  - "WHEN a checkout directory's basename differs from its `remote_name` and the forge lists `remote_name`,
    the report SHALL yield neither `uncloned` nor `undeclared-member`/`unregistered` under the basename";
  - "WHEN the same name is listed by two forge sources, the report SHALL yield no `duplicate-identity`";
  - "WHEN a fixture constellation is fully consistent, the report SHALL have no items";
  - "an archived repo SHALL never yield `undeclared-member`, `uncloned`, `unregistered` or
    `mirror-missing`";
  - "a Resource with no dependent SHALL yield no item";
  - "IF the forge source contributed an `incomplete` or failure note, THEN `skipped` SHALL name the forge
    dimension, `uncloned`, `archived-host` and `archived-registered` SHALL be computed only over what was
    read, and no `exclusion-invalid` SHALL fire for an entry whose only defect is naming no repo";
  - "IF a mirror file cannot be read, THEN `skipped` SHALL name that mirror and no `mirror-*` item SHALL
    be emitted for it".
  — depends on: SP-T1, SP-T2, SP-T3, SP-T4
- SP-T6: CLI `iris check [--json]` + exit codes + telemetry, and an **integration test** that drives the
  real path end-to-end: a tmp `sources.toml` with constellation (mrconfig + roots) and forge-repos (a fake
  CLI script), run through the Typer app. This is the cross-boundary acceptance: source → federate →
  composer → CLI. — implements Q4 — acceptance (EARS):
  - "WHEN the fixture has drift, `iris check` SHALL exit 1 and the text output SHALL contain a `## <kind>`
    section per drift kind present";
  - "WHEN `--json` is given, stdout SHALL parse as JSON with keys `drift`, `skipped`, `counts`, and each
    drift item SHALL have `kind`, `subject`, `detail`";
  - "WHEN there is no drift and nothing skipped, it SHALL exit 0";
  - "IF there is no drift but the fake forge fails, THEN it SHALL exit 2 and SHALL NOT print a clean
    summary";
  - "WHEN `iris repos` runs on the same config, its output SHALL be identical to its output with the
    forge source and roots removed" (the isolation regression).
  Persisted in `tests/test_cli_check.py`. — depends on: SP-T5
- SP-T7: docs.
  - **User-facing:** `README.md` documents `iris check` (purpose, config, drift kinds, exit codes), and
    `sources.example.toml` gains the `roots`/`depth` options, the `forge-repos` block and the `[check]`
    table with placeholder values only.
  - **Glossary** (`docs/domain.md`, norm not prose): the Ubiquitous-language section comes to define
    **Resource** (a Node kind for a non-code entity, hosted by the repo whose descriptor declares it),
    **Member** (a repo whose checkout carries a descriptor; archived repos are not live members),
    **Universe** (the union of registry, roots and forge repos, read only for a universe-kind query),
    **Drift** (the closed kind set of this Spec, by reference) and **Exclusion list** / **Mirror**. The
    **Kind** entry lists `universe`. The **Repo** entry, which today says "from the repo-registry source",
    comes to admit disk and forge origins. Read these against the existing Node/Relation/Identity entries:
    no clash is intended. These are system-regime statements (iris's own definitions), so they carry no
    world mark.

  — implements Q1–Q4 (doc surfaces) — acceptance: "the README SHALL contain a `check` section listing all 14
  drift kinds and the three exit codes" (test greps the README for each kind name); "`sources.example.toml`
  SHALL parse with `load_config` and contain no non-placeholder org" (test). — depends on: SP-T6

## Coverage check (every in-scope Q* -> ≥1 task)
- Q1 (Resource entities) -> SP-T1, SP-T7
- Q2 (typed resource dependencies, reverse view derivable) -> SP-T1 (the `dependsOn` relations + resource
  nodes make `dependencyOf` a filter over relations; no dedicated command — see exclusions)
- Q3 (explicit universe: mrconfig ∪ roots ∪ forge orgs, more than one forge) -> SP-T2, SP-T3, SP-T5
- Q4a -> SP-T5 (`undeclared-member`, `uncloned`, `mirror-*`)
- Q4b -> SP-T2, SP-T5 (`phantom`, `unregistered`)
- Q4c -> SP-T3, SP-T5 (`archived` flag drives membership, `archived-host`, `archived-registered`,
  `mirror-stale`, `name-mismatch` for renames)
- Q4d -> SP-T5 (`dangling-dependency`, `archived-host`)
- Q4e -> SP-T1, SP-T5 (`one-end-only`, over the host-end `dependencyOf` declaration)
- Q4f -> SP-T4, SP-T5 (`exclusion-invalid`, `exclusion-promoted`)
- Q4 (the command) -> SP-T6
- No task without a Q*: `duplicate-identity` serves BR06 (identity-mediated joining), which the universe
  union depends on; it is not scope creep but a precondition of Q3.

## Deliberate exclusions
- **Scheduling, the check's own liveness alert and opening an issue on drift** — iris#48 out-of-scope;
  deployment concerns of whoever runs the check, and they are tracked by that deployer outside this repo.
  Value-rejected: not this public core's job; the core's part of that contract is the exit code and the JSON (SP-T6).
- **A dedicated reverse-dependency command (`dependencyOf` view)** — Q2 requires it to be *derivable*, which
  the typed relations satisfy; a command to print it has no consumer yet.
  Value-rejected: no reader for a reverse view exists yet; adding one is a one-function change when one appears.
- **MCP exposure of `check`** — the consumers are a scheduler and a human at a terminal; the MCP tools serve
  agent context reads. Value-rejected: no agent consumer named; parity can be added by need.
- **A shared resource declared at NEITHER end** (a coupling with no `dependsOn` and no `dependencyOf`) —
  leaves no declaration to read, so no check can see it. Value-rejected: no signal exists to compute it.
- **One-end matching for a Resource that declares no `dependencyOf`** — the host end is optional, so such a
  Resource is checked only for dangling references. Value-rejected: requiring `dependencyOf` everywhere
  would flag every legitimately unshared resource; a host that wants both ends checked declares it.
- **Reading descriptors of forge-only repos remotely** (without a local checkout) — such repos surface as
  `uncloned`, which is the actionable signal (clone it or exclude it). Value-rejected: a remote content read per repo adds
  forge API coupling for no decision it changes.

## Risks / unknowns
- **glab JSON listing shape** — the field names (`path`, `archived`) and the JSON flag of `glab repo list`
  are taken from its help, not from a run against a real group. Mitigation: the map is configurable; SP-T3
  tests use a fake command; the operator's config validates it at first run.
- **Disk scan cost** on large roots — bounded by `depth` (default 2) and by not descending into checkouts;
  the scan runs only on a universe-kind query (`check`), never on `repos`/`context`.
- **Mirror pattern brittleness** — a mirror is human prose; the regex is the operator's to tune per
  mirror, and a wrong pattern shows as a burst of `mirror-*` items, never as silence.

## Assumptions & invalidators
- The `origin` remote name identifies a checkout's repo, and a name is unique across owned orgs —
  invalidated if `duplicate-identity` fires, or if two genuinely different repos share a name across orgs
  (they would be merged into one identity). A checkout with no `origin` falls back to its basename.
- A `.git` directory marks a primary checkout and a `.git` file a linked worktree — invalidated by a
  submodule checkout under a root (its `.git` is a file, so it would be skipped). Acceptable: submodules are
  not constellation members.
- The upstream convention that membership = having a descriptor holds for every owned repo — invalidated
  if the first real run reports `undeclared-member` items that are members by intent. Those are then
  backfill work, which is the check doing its job.

## Open questions
- Should `exclusion-invalid` also fire on a reason outside a fixed vocabulary (e.g. `study` / `third-party`)?
  Deferred: free text with a non-empty check is enough until the list grows past a glance (resolved here as
  "non-empty only").
