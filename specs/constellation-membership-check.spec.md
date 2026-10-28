# Spec: constellation membership & drift check — Resources, resource dependencies, explicit universe

- Frozen at: 2026-10-28
- Spec version: v1.1
- Source: iris#48 (requirements 1–4 and its out-of-scope paragraph). The problem framing and the arrangement
  that assigns this capability to iris are upstream of this repo and private; iris#48 restates the
  requirements generically, and this Spec cites them as `Q1`–`Q4` (the issue's numbered items) plus `Q4a`–`Q4f`
  (the six bullets of item 4, in order). **PRD stage skipped** (craft-call, as in this repo's earlier Specs: a
  bounded increment inside an existing product; iris#48 already carries requirement-level content, so a PRD
  would only restate it).
- Status: frozen after approval on 2026-10-28 (operator: "Pode congelar"). Pre-freeze reads: one blind read
  (J5/J6/J3/J1, 4 findings) + two scoped reads of the fix text (4 and 5 findings), all fixed; the last
  fixes had no reader — accepted by the operator, the build's per-kind fixtures and `review` are the backstop
- Amendments: v1.1 (2026-10-28, after build + review of PR iris#51; operator: "pode fazer o ajuste na
  spec") — text aligned with the built behaviour, no requirement changed: (a) the Resource node carries
  `attrs.host` (its host repo's node id) beside `attrs.host_path`, which SP-T1's acceptance and the Data model
  named differently; (b) SP-T2's host-alias clause moves to the check's joins, since a source never receives
  the `[check]` table; (c) the check queries the `universe` kind alone; (d) a registry that could not be read
  is a skipped dimension, with no drift computed (review finding F1). The build's other open choices are
  recorded in `decisions/0001-constellation-check-build.md`.

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
                 forge-repos   (one CLI call per configured org)        ─┤ federate(kinds={universe})
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
  - `path` (str, local checkout or mrconfig entry path);
  - `descriptor` (bool);
  - `origin` (`"mrconfig"` | `"disk"` | `"forge"`);
  - `exists` (bool, mrconfig entries);
  - `slug` (str — the repo's **forge slug** `<host>/<path>`, see Membership identity);
  - `declared_name` (str, the descriptor's Component `metadata.name`, when a descriptor exists);
  - `archived` (bool, forge only).

  It is backward compatible, since every existing constructor call omits it. `Node` is already unhashable
  (list fields), so a dict field changes nothing there. Node ids are unchanged (the checkout basename for
  repos), so `repos`/`context`/`chain` see the same ids as today. Because a basename is not unique once roots
  are scanned, **the check never joins on node ids**: it joins local repos by `attrs.path` and identities by
  `attrs.slug`. A local repo node therefore also carries `depends_on` (list of raw `dependsOn` refs).
- **Membership identity — ONE key for every check join: the forge slug `<host>/<path>`** (e.g.
  `github.com/some-org/some-repo`; `<path>` is the full repo path, GitLab subgroups included).
  - Local checkout: parsed from the `origin` URL in `.git/config` (scp-style `git@host:path(.git)`,
    `ssh://[user@]host[:port]/path(.git)` and `https://host/path(.git)` forms; no subprocess).
  - Normalisation, applied to every slug: host and path lowercased (the forges treat them
    case-insensitively), `.git` suffix and trailing `/` dropped, port dropped, and the host mapped through
    the optional `[check.host_aliases]` table (an ssh alias such as `gh-work` → the real host). [v1.1] A source
    does not receive the `[check]` table, so the aliases are applied by `compose_membership` to every slug
    before any join; the slug a node carries is unaliased.
  - mrconfig entry whose path does not exist: parsed from the clone URL on its `checkout =` line, so an
    uncloned entry still has its real identity.
  - Forge repo: `<host>/<full path>`, with `host` a required option of each forge source instance
    (private config) and `<full path>` the repo's full path as the forge lists it (mapped field `path`:
    gh `nameWithOwner`, glab `path_with_namespace`), so a GitLab subgroup repo keeps every segment.
  - "A host+org the forge dimension read" means: a forge source with that `host` ran the command for an org
    `<org>` without failing; a local slug falls under it when its path starts with `<org>/` (subgroups
    included, provided the listing command includes them, e.g. glab `--include-subgroups`).
  - Fallback: a checkout with no `origin` (or an mrconfig entry with no parsable URL) gets
    `local:<basename>`; it can never match a forge entry, so it is reported only by the local kinds.
  The **name** of an identity is its last path segment; mirrors (human lists of names) compare by name.
  The `[check.exclude]` keys are normalised slugs, quoted in TOML. Because the slug carries host and org, two genuinely different
  repos with one name in two orgs stay distinct, and the same repo on two forges is two identities (a
  mirror repo is excluded like any other non-member).
- **Entity names (the Resource graph)** — descriptor refs (`dependsOn`, `dependencyOf`) name **entities**
  (`metadata.name`), as in Backstage, not slugs. The composer maps each entity name to its repo through the
  repo's `declared_name`, and from there to its slug. A Resource's host is the repo whose descriptor
  declares it (recorded by the source as that repo's `path`; the composer resolves it to the slug).
- **Resource node** — `Node(kind="resource", id=<metadata.name>, title=<metadata.description or name>,
  roles=[spec.type] if any, source=<source name>, attrs={"host": <host repo node id>, "host_path": <host repo
  path>, "dependency_of": [<consumer entity names>]})` [v1.1: `host` added]. Its relation is `Relation(from_=<resource id>, type="hosted-by",
  to=<host repo node id>)`, for the existing graph readers; the check uses `host_path`.
- **Typed dependency** — each `spec.dependsOn` entry of the Component document is parsed as a Backstage
  entity ref `[<kind>:][<namespace>/]<name>`. The check reads it from the repo node's `attrs.depends_on`.
  For the existing graph readers it also becomes `Relation(from_=<repo node id>, type="dependsOn",
  to=<the raw ref string>)`, keeping the current shape so the existing test and readers hold. A helper
  `parse_entity_ref(ref) -> (kind | None, namespace | None, name)` is the single interpretation point.
  Namespace is ignored: a personal constellation has one namespace.
- **Both ends of a shared resource** — the consumer end is each consumer's `dependsOn: resource:<x>`; the
  host end is the Resource's `spec.dependencyOf` (Backstage's own field), **absent = empty**. The two sets
  must be equal. A Resource no one uses has both sets empty and is not drift, so requiring the comparison
  everywhere costs an unshared resource nothing. A host lists its consumers once per shared resource; the
  reverse view (`dependencyOf`) stays derivable from the consumer relations too (Q2).
- **DriftItem** — `(kind: str, subject: str, detail: str)`. `kind` is from the closed set below.
- **DriftReport** — `items: list[DriftItem]`, `skipped: list[str]` (dimensions that could not run, with
  why), `counts: dict[str, int]` (members, archived, excluded, resources, dependencies).

**Drift kinds (closed set)** and the requirement each serves. Every comparison below is by slug unless it
says otherwise.

| kind | fires when | serves |
|---|---|---|
| `undeclared-member` | a local checkout (mrconfig or roots) has no descriptor, its slug is not excluded, and it is not archived | Q4a |
| `uncloned` | a forge repo, not archived and not excluded, has no local checkout and no mrconfig entry with its slug. When a `stale-remote` item exists under the same host+org, the detail says so: a rename shows as both (the forge keeps no old name to pair them) | Q3, Q4a |
| `stale-remote` | a local checkout's `origin` slug is on a host+org the forge dimension read, but the forge does not list it (renamed, moved or deleted on the forge) | Q4a, Q4c |
| `phantom` | an mrconfig entry's path does not exist on disk | Q4b |
| `unregistered` | a member (local checkout with a descriptor, not archived) has a slug no mrconfig entry carries | Q4b |
| `archived-registered` | a slug the forge reports archived is an mrconfig entry's slug (cloned or not) | Q4c |
| `archived-host` | a Resource's host repo has a slug the forge reports archived | Q4c, Q4d |
| `dangling-dependency` | a `dependsOn: resource:<x>` names no Resource `<x>` declared anywhere in the universe | Q4d |
| `one-end-only` | for a declared Resource, the set of consumers declaring `dependsOn: resource:<x>` differs from its `dependencyOf` set (absent = empty); one item per consumer in the difference, naming which end is missing | Q4e |
| `name-mismatch` | a member's descriptor `metadata.name` differs from its slug's name (a rename not carried into the descriptor) | Q4a, Q4c |
| `exclusion-invalid` | an exclusion entry has an empty reason, or its slug is in no source of the universe — the second half is suppressed while the forge dimension is skipped, since the repo may be forge-only | Q4f |
| `exclusion-promoted` | an excluded slug's checkout carries a descriptor | Q4f |
| `mirror-missing` | a member (not archived) has a name not listed in a configured mirror | Q4a (mirror) |
| `mirror-stale` | a name a mirror lists is the name of no live member | Q4a, Q4c |
| `duplicate-identity` | two different local paths resolve to one slug | BR06 |

"Member" means: a repo in the universe whose local checkout carries a `catalog-info.yaml` (membership =
having a descriptor). A slug the forge reports archived is never a live member; when the forge dimension is
skipped, archived state is unknown and every local repo is treated as live (the skip is reported). An
archived repo's descriptor `lifecycle` is not checked: an archived forge repo is read-only, so its
descriptor cannot be updated after archiving; the forge `archived` flag is the source of truth for that
state, and the drift that would revive it is `archived-registered`.

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
  host = "<forge-host>"                                             # private config only; part of the slug
  orgs = ["<org-or-group>", "..."]                                  # private config only
  command = ["gh", "repo", "list", "{org}", "--json", "nameWithOwner,isArchived", "--limit", "1000"]
  # items = ""                                                      # dotted path to the list
  [sources.forge.map]
  path = "nameWithOwner"  # glab: "path_with_namespace"
  archived = "isArchived" # glab: "archived"
  ```
  Several forges = several instances of this type (e.g. `[sources.forge-a]` with a `gh` command and
  `[sources.forge-b]` with a `glab` command), as the registry already allows.
  One invocation per org, `{org}` substituted. A failing org contributes a note naming the org and marks the
  forge dimension incomplete; the other orgs still count (BR04 at org granularity). The source produces
  only `universe`.
- **Config — `[check]` table** (new; read by `load_config` into `Config.check: dict`):
  ```toml
  [check.exclude]          # repos that are knowingly NOT members: normalised slug = reason
  "forge.example/some-org/some-study-repo" = "study"
  "forge.example/some-org/some-fork" = "third-party"
  [check.host_aliases]     # optional: ssh host alias -> real host
  "gh-alias" = "forge.example"
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
  [v1.1] A registry that could not be read is such a dimension too, and every kind rests on it, so the
  check then computes no drift at all rather than drift against an empty local side.
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

- SP-T1 [v1.1]: shared descriptor parser `sources/_catalog.py` — `parse_descriptor(path)` returns the Component
  metadata (first mapping doc whose `kind` is absent or `Component`), the list of Resource docs, and the raw
  `dependsOn` refs; plus `parse_entity_ref(ref)`. Rewire `constellation._node_from_catalog` onto it and emit
  Resource nodes + `hosted-by` relations; add `Node.attrs`. Rewrite the constellation module docstring to
  the new behavior (replace, not stack). — implements Q1, Q2 — acceptance (EARS):
  - "WHEN a descriptor holds a Component and two Resource documents, the source SHALL emit one repo node,
    two `resource` nodes with `attrs.host` = the repo node id and `attrs.host_path` = its path, and two
    `hosted-by` relations";
  - "WHEN `dependsOn` holds `resource:erp-account`, `component:default/x` and `y`, `parse_entity_ref`
    SHALL return `("resource", None, "erp-account")`, `("component", "default", "x")`, `(None, None, "y")`";
  - "the existing constellation tests SHALL pass unchanged";
  - "WHEN the first document is a Resource and a later one the Component, the repo node SHALL still carry
    the Component's metadata";
  - "WHEN a Resource declares `spec.dependencyOf: [component:a, b]`, its node SHALL carry
    `attrs.dependency_of == ["a", "b"]`".
  Persisted tests in `tests/test_catalog.py` + `tests/test_constellation_source.py`. — depends on: —
- SP-T2 [v1.1]: constellation `roots`/`depth` options + universe-kind behavior + `KIND_UNIVERSE`. Repo nodes carry
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
  - "WHEN a checkout's `.git/config` has `[remote "origin"] url = git@host.example:org/real-name.git` and
    the directory is named `other`, its node SHALL carry `attrs.slug == "host.example/org/real-name"`; the
    `https://host.example/org/sub/real-name.git` form SHALL yield `host.example/org/sub/real-name`, the
    `ssh://git@Host.Example:2222/Org/X.git` form SHALL yield `host.example/org/x`; and, in the check's
    joins, a host listed in `[check.host_aliases]` SHALL be replaced by its target";
  - "IF an mrconfig entry's path does not exist and its `checkout =` line holds a clone URL, THEN its node
    SHALL carry the slug parsed from that URL";
  - "IF a checkout has no `origin`, THEN its slug SHALL be `local:<basename>`";
  - "a local node with a descriptor SHALL carry `attrs.declared_name`".
  Persisted tests with a tmp tree. — depends on: SP-T1
- SP-T3: `forge-repos` source (`sources/forge.py`, registered as `forge-repos`). — implements Q3, Q4c —
  acceptance (EARS):
  - "WHEN configured with two orgs, the source SHALL run the command once per org with `{org}`
    substituted and emit one `repo` node per listed repo with `origin="forge"`, `attrs.slug ==
    "<host>/<full path>"` from the mapped `path` field (a `group/sub/x` path keeps all three segments) and `attrs.archived` from the mapped field";
  - "IF the `host` option is missing, THEN the source SHALL return `ok=False` with a note (no slug can be
    formed)";
  - "IF one org's command fails or emits invalid JSON, THEN the source SHALL still return the other org's
    repos, with `ok=True` and a note naming the failing org and the word `incomplete`";
  - "IF every org fails, THEN `ok=False` with a note";
  - "the module SHALL contain no org, host or instance literal" (grep test over the module source, the
    BR02 check).
  Persisted tests with a fake command. — depends on: SP-T2
- SP-T4: `[check]` table in config — `Config.check` (default `{}`), `exclude`, `host_aliases` and
  `mirrors` parsed as given. — implements Q4f, Q4a (mirror) — acceptance (EARS):
  - "WHEN `sources.toml` has a `[check]` table, `load_config` SHALL expose it as `Config.check`";
  - "WHEN it has none, `Config.check` SHALL be `{}` and every existing config test SHALL pass".
  Persisted test in `tests/test_config.py`. — depends on: —
- SP-T5: `core/membership.py` — `compose_membership(result, check) -> DriftReport` computing every kind in
  the closed set, plus the `skipped` list. — implements Q3, Q4a–Q4f — acceptance (EARS), one persisted
  fixture test per kind in `tests/test_membership.py`:
  - "WHEN the fixture contains exactly one instance of a drift kind, the report SHALL contain exactly one
    item of that kind with that subject" (one case per kind, 15 kinds);
  - "WHEN a checkout directory's basename differs from its slug's name and the forge lists that slug, the
    report SHALL yield no `uncloned` for it and no item under the basename";
  - "WHEN a checkout's `origin` slug is absent from the forge listing of its host+org and the forge lists
    a different slug for the same checkout's renamed repo, the report SHALL yield `stale-remote` for the
    checkout and `uncloned` for the new slug with a detail naming the stale-remote item" (the rename case);
  - "WHEN two local checkouts under different roots share a basename and only one hosts a Resource,
    `archived-host` and `one-end-only` SHALL resolve that Resource to the right one (joined by path)";
  - "WHEN the forge lists `group/sub/x` and a checkout's origin is `group/sub/x`, the report SHALL yield
    neither `uncloned` nor `stale-remote` for it";
  - "WHEN two forge sources list repos with one name under different hosts or orgs, the report SHALL treat
    them as two identities and yield no `duplicate-identity`";
  - "WHEN a Resource has consumers declaring `dependsOn` and no `dependencyOf`, the report SHALL yield one
    `one-end-only` item per consumer";
  - "WHEN the forge dimension is skipped, archived state SHALL be unknown, every local repo SHALL be
    treated as live, and `skipped` SHALL say so";
  - "WHEN a fixture constellation is fully consistent, the report SHALL have no items";
  - "an archived repo SHALL never yield `undeclared-member`, `uncloned`, `unregistered` or
    `mirror-missing`";
  - "a Resource with no consumer and no `dependencyOf` SHALL yield no item";
  - "IF the forge source contributed an `incomplete` or failure note, THEN `skipped` SHALL name the forge
    dimension, `uncloned`, `stale-remote`, `archived-host` and `archived-registered` SHALL be computed only
    over the host+orgs that were read, and no `exclusion-invalid` SHALL fire for an entry whose only defect is naming no repo";
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

  — implements Q1–Q4 (doc surfaces) — acceptance: "the README SHALL contain a `check` section listing all 15
  drift kinds and the three exit codes" (test greps the README for each kind name); "`sources.example.toml`
  SHALL parse with `load_config` and contain no non-placeholder org" (test). — depends on: SP-T6

## Coverage check (every in-scope Q* -> ≥1 task)
- Q1 (Resource entities) -> SP-T1, SP-T7
- Q2 (typed resource dependencies, reverse view derivable) -> SP-T1 (the `dependsOn` relations + resource
  nodes make `dependencyOf` a filter over relations; no dedicated command — see exclusions)
- Q3 (explicit universe: mrconfig ∪ roots ∪ forge orgs, more than one forge) -> SP-T2, SP-T3, SP-T5
- Q4a -> SP-T2, SP-T5 (`undeclared-member`, `uncloned`, `stale-remote`, `name-mismatch`, `mirror-*`)
- Q4b -> SP-T2, SP-T5 (`phantom`, `unregistered`)
- Q4c -> SP-T3, SP-T5 (`archived` flag drives membership, `archived-host`, `archived-registered`,
  `mirror-stale`, `name-mismatch` for renames)
- Q4d -> SP-T5 (`dangling-dependency`, `archived-host`)
- Q4e -> SP-T1, SP-T5 (`one-end-only`: consumer `dependsOn` set vs host `dependencyOf` set, absent = empty)
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
- **A descriptor `lifecycle` of `deprecated` on a live (not archived) repo** — not checked. Deprecating
  before archiving is a legitimate transition state, so a mismatch is not drift by itself; the archived
  direction is covered by the forge flag (see the Data model). Value-rejected: no rule distinguishes a
  stale `deprecated` from a deliberate one.
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
- A checkout's `origin` slug identifies its repo — invalidated if `duplicate-identity` fires (two paths, one
  slug), or if `stale-remote` fires (the forge no longer knows the slug; the fix is `git remote set-url`).
  A checkout with no `origin` gets `local:<basename>`, which matches nothing on the forge by construction.
- A repo kept on two forges is two identities, so the copy without a local checkout reports `uncloned` until
  it is excluded — invalidated as a cost if mirrors become common (then a per-repo mirror declaration
  would earn a place).
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
