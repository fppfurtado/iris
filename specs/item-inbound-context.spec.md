# Spec: item inbound context — `iris inbound <key>`

- Frozen at: 2026-10-29 (v1) · 2026-11-11 (v2)
- Spec version: v2
- Source: Problem Brief `briefs/item-inbound-context.BRIEF.md` v1 (frozen 2026-10-29) — PRD skipped (a feature
  inside an existing product, the same path the F6-mínimo Spec took; tasks cite Brief J*/S* directly)
- Status: v1 frozen after approval on 2026-10-29 (operator "sim" to "Freeze the Spec as v1?"); v2 frozen after
  approval on 2026-11-11 (operator "sim" to the v2 freeze question). Independent read: ran — blind-critic
  J5/J6/J3/J1 (2026-11-11), 6 findings, all disposed in this text
- Amendments: **v2 (2026-11-11, iris#38 SP-T8 · iris#62 part 2 · iris#59 for `inbound`; operator delegated
  the design choice):** (1) the citing TASKS now come from the store's own inbound read, which resolves them
  per task since fppfurtado/mneme#343 (mneme 0.26.2: `knowledge/gtd.md#^<id>`, open and done). iris looks up
  only each task's state, by anchor, through the existing `chain` read. So both halves of the result carry
  ONE identity rule, the store's (BR01), and the `tasks` source's `inbound` mode is retired. Brief:S2b
  expired, as the Brief states it would when N3 landed. (2) The result names what it never searches
  (`not_covered`: forge items citing the key, Brief:N4), so an empty `unknown` is not read as "nothing else
  cites it" (iris#62 part 2; the agent-kit#3065 case). (3) SP-T8's fixtures are redacted recordings pinned
  to the store snapshot `1f760ec`, re-recorded with the fixed store (decisions/0002 D4/D5; mneme#344 landed
  in 0.26.1), and its test file is renamed: `tests/test_earn_datum.py` already holds another Spec's earn datum.
- Extends (not amends): `specs/f6-minimo-cross-repo-dep-chain.spec.md` v1 — reuses its ref parser
  (`parse_refs`) and the `chain`-mode reads of the `tracker` and `tasks` sources UNCHANGED to fetch the item's
  live state and (v2) the citing tasks' state; adds nothing to `iris chain` and edits none of its code paths.

## Design

### Architecture
Flow (v2): `key → parse_key → (1) federate kinds={chain} on the key (the item's own live state) → (2) federate
kinds={inbound} on the key (the store's records citing it: citations AND task anchors) → (3) WHEN (2) named
≥1 task anchor, federate kinds={chain} on those anchors (each task's state) → compose_inbound →
InboundContext → CLI / MCP`.

- **A new sibling verb `iris inbound <key>`** — because its input is a KEY (one `<repo>#<n>` or `^<anchor>`)
  and its answer is "what cites this item", a different contract from both neighbours — over **(a) an item mode
  of `iris context`**: `context` takes free task text that routinely names refs (`context "work on iris#29"`), so
  switching its behaviour on the shape of its input would silently change what existing callers get; and over
  **(b) an inbound arm of `iris chain`**: `chain` takes an item's TEXT and answers "which of the things it cites
  are open" (a blocker view); folding the reverse direction in would mix two inputs (text vs key) and two
  questions in one verb and force an amendment of the frozen F6 Spec. Both rejected options are swappable
  surfaces, not intrinsic flaws: the inbound composition is placed so either could later absorb it by
  calling `compose_inbound`.
- **Extend by addition** in the existing bounded context (cross-source composition), as F6 did — over a new
  module/package: the same context, no ceremony.
- **(v2) Who decides which TASKS cite the key — three candidates:**
  - **(A) iris parses the task lists itself** (v1: the `tasks` source's `inbound` mode, `parse_refs` over
    each task's text). Rejected. When v1 froze it was the only way to get per-task granularity, because the
    store resolved tasks per FILE (Brief:N3). Since mneme#343 the store resolves them per task. Keeping (A)
    re-implements a within-source resolution the source now owns, contrary to BR01. It also leaves the two
    halves of one result on two different identity rules (iris#59: `iris#3a` and `owner/iris#38` count in
    one half and not the other). The disqualifier is intrinsic to (A) once the store resolves per task, so
    it cannot be swapped out.
  - **(B) the store's inbound read names the citing tasks, and the config says which of its locators are
    tasks** (chosen). The `cli-json` inbound stanza declares a `tasks` locator prefix. A record whose locator
    starts with it is a citing task, and the rest of the locator is the task's anchor. iris then reads only
    that task's state, by anchor, through the existing `chain` read of the `tasks` source. One identity rule,
    the store's, covers both halves. No adapter names a store (BR02): the prefix is private config.
  - **(C) the composer recognises any locator of the shape `…#^<id>` as a task.** Rejected. It would bind
    the core to one store's locator format by coincidence of shape, not by declared identity (BR06). A second
    store whose block locators happen to use `#^` would have its blocks misread as tasks. The flaw is
    intrinsic to matching on shape.
- **Three federation passes** (v2), sequential because pass (3) needs pass (2)'s anchors. Each source already
  routes by kind with one mode per read (BR07), so no mode-combination branch is added. Store calls per run:
  1 for the item's state on an issue key (the forge; an anchor key adds the 2 task-list reads), 1 for the
  inbound read, and 2 task-list reads only when ≥1 task cites the key. That is no more than v1 (≈3–4), since
  pass (2) no longer reads the task lists. Re-evaluate if the latency SP-T8 records is felt.
- **Accepted loss (v2):** degradation is coarser. When the store's inbound read fails, both tasks and
  citations become unknown together (v1 kept them on separate reads). The source is still named in `unknown`
  (BR04), so nothing is read as "no citations".

### Data model
- `KIND_INBOUND = "inbound"` (core/source.py): a caller consuming the records that CITE a given key. Unchanged.
- `parse_key(key: str) -> Ref | None` (sources/_repos.py): the WHOLE stripped input must be exactly one ref
  (`<repo>#<n>` or `^<anchor>`), parsed by the existing patterns; anything else → `None`. Unchanged.
- Inbound records reuse `Node` (no new field):
  - a citing journal entry / note → `Node(kind="citation", id=<locator as the store returns it>,
    title=<locator>, roles=[<link type>], source=<name>)`. Unchanged.
  - (v2) a citing task, as the store's inbound read returns it → `Node(kind="task", id=<anchor id>, title="",
    roles=[], source=<name>)`, where the anchor is the locator minus the configured `tasks` prefix.
    `compose_inbound` fills `title` and `roles` (`"open"` | `"done"`) from pass (3). A task that pass (3)
    does not resolve keeps `roles=[]`, and the surfaces render it as state unknown. It is never dropped,
    because the store said it cites the key.
- `FederationResult.degraded: list[str]`: the names of sources that raised or returned `ok=False`. Unchanged.
- `InboundContext` (frozen, core/compose.py): `key`, `item: Node | None`, `tasks: list[Node]`,
  `citations: list[Node]`, `unknown: list[str]`, `notes: list[str]`, and (v2) two fields that say what the
  absence of a record covers. `searched: list[str]` holds the names of the configured sources read for
  `inbound`, derived from the config at run time (each source whose `produces` contains `inbound`).
  `not_covered: list[str]` holds what no configured source searches, fixed by the verb's design: forge items
  citing the key (cross-forge fan-in, Brief:N4), and the citation forms outside identity under Brief:C3 (a
  forge URL, a bare `#<n>`). Both are returned on every result.
  - Candidates for `not_covered` (v2): (a) one fixed entry for forge fan-in (the first draft). Rejected: it
    hides that a configured source with no inbound read is not searched either, and that URL and bare-`#<n>`
    citations are never matched (blind read, 2026-11-11). The flaw is intrinsic, since a fixed list cannot
    follow the config. (b) every configured source without an inbound read, named as not covered. Rejected:
    a source read only for state (the forge, the task lists) is not a citation source, and naming it "not
    searched" says something false about the state it supplied. (c) chosen: a positive `searched` list from
    the config, plus the fixed `not_covered` classes.

### Interfaces / contracts
- (v2) `tasks` source: the `inbound` mode is removed and `produces` no longer contains `inbound`. Its `chain`
  mode (`_read_referenced`: the state of the specific `^anchors` a text names, open and done lists, per-list
  isolation) is what pass (3) calls, unchanged.
- `cli-json` source, inbound mode — **only when an `inbound` stanza is configured**:
  `[sources.<name>.inbound] command = [... "{key}" ...]`, `items = ""` (path to the array, empty = top level),
  `[sources.<name>.inbound.map] locator = "source"`, `type = "type"`, optional `skip = ["<locator prefix>", …]`
  (records whose locator starts with a prefix are dropped), and (v2) optional `tasks = "<locator prefix>"`. A
  record whose locator starts with `tasks` and whose remainder is a whole anchor body (the `[a-z0-9]+` of the
  existing `^<anchor>` pattern) is emitted as a task node (data model above), not as a citation. A record
  whose remainder is empty or not an anchor body is emitted as a citation, with one note naming the prefix,
  so a mis-set prefix shows instead of turning every task into `[state unknown]`. **`tasks` is classified
  BEFORE `skip`**: a `skip` prefix never drops a record the `tasks` prefix claims, so an old
  `skip = ["<task file>"]` left in a config cannot hide every task. `produces` gains `inbound` only when the
  stanza exists. A read failure returns `ok=False` + note (never raises).
- (v2) `compose_inbound(key, state: FederationResult, inbound: FederationResult, task_state: FederationResult |
  None = None) -> InboundContext`. A task node from `inbound` takes `title` and `roles` from the
  `task_state` node with the same id. A task whose anchor equals an anchor key is dropped (the item is never
  its own citing task). Tasks and citations keep `inbound` order, de-duplicated by (kind, id). `unknown`
  names every source degraded in any of the three passes.
- CLI `iris inbound <key>`: sections `## item` (key, state, title; or `unknown — could not resolve`), `## tasks
  citing <key>` (`^<id>  [open|done]  <first line>`; (v2) `^<id>  [state unknown]` for an unresolved task),
  `## citations` (`<locator>  [<type>]`), `## unknown` (each degraded source name — never folded into "no
  citations"), and (v2) `## searched` (each `searched` name) and `## not searched` (each `not_covered` entry),
  both always printed. Invalid key → message on stderr, exit 2. No records and nothing unknown → (v2)
  `# no records in <searched names> cite <key>` on stderr, exit 0.
- MCP tool `inbound(key) -> dict` with `key`, `item`, `tasks`, `citations`, `unknown`, `notes`, and (v2)
  `searched`, `not_covered` — the same composer as the CLI (parity). Invalid key → `{"error": "..."}`.
- Telemetry: `log_request("inbound", key, nodes=<tasks+citations>, extra={"unknown": n})`, as the other verbs.

### Tech choices
- No new dependency; the knowledge-store inbound read is configured, not coded (BR02) — over a dedicated
  `mneme` adapter, which would name a private tool in the public core. (v2) The `tasks` locator prefix is
  configured for the same reason.

### Cross-cutting
- Read-only (BR03): no new write path; the read-only guard test covers the MCP tool.
- Degradation (BR04): every read isolates its failure to its own part of the result (v2: the tasks and the
  citations now share one read, see the accepted loss above).

### Durable invariants
None new. The inbound match is an instance of BR06 (identity-mediated join) and, in v2, of BR01 (the store
resolves which of its records cite the key, tasks included). No new cross-cutting rule is established;
`not_covered` belongs to this verb's contract only.

## Task plan
- SP-T1: `KIND_INBOUND` + `parse_key` — implements Brief:J1, Brief:C3 — acceptance (EARS): "WHEN the input is
  exactly one `<repo>#<n>` or `^<anchor>` (surrounding whitespace allowed), `parse_key` SHALL return that `Ref`";
  "IF the input is empty, carries more than one ref, or carries any other text, THEN `parse_key` SHALL return
  `None`" — persisted unit tests in tests/test_refs.py — depends on: —
- SP-T2 [v1; superseded in v2 by SP-T9 + SP-T10, built in PR #58, its mode removed by SP-T10]: `tasks` source
  inbound mode — implements Brief:J2, Brief:C3, Brief:S2b, Brief:S4 — acceptance (EARS, v1): "WHEN a query
  declares `inbound`, the `tasks` source SHALL emit every open AND done task whose parsed refs contain the key,
  with `roles` = its list state"; "the source SHALL NOT emit a task that only contains the key as a prefix of
  another ref (`iris#3` vs `iris#34`, `^ab` vs `^abc`)"; "IF one list is unreadable, THEN the source SHALL still
  emit the other list's matches and report `ok=False` with a note" — persisted tests in
  tests/test_tasks_source.py with a fake runner — depends on: SP-T1
- SP-T3: `cli-json` source inbound mode — implements Brief:J3, Brief:C2 — acceptance (EARS): "WHERE an `inbound`
  stanza is configured, the source SHALL substitute `{key}` and emit one `Node(kind="citation")` per returned
  record, minus records whose locator starts with a `skip` prefix"; "WHERE no `inbound` stanza is configured, the
  source's `produces` SHALL NOT contain `inbound` and federation SHALL NOT read it for an inbound query"; "IF the
  command fails or returns a non-array, THEN the source SHALL return `ok=False` with a note, not raise".
  Identity (Brief:C3/S4) on this half is the store's own within-source resolution (BR01): the source passes the
  key through and does not re-match records, because a citation record carries no text to parse. It is held by
  SP-T8's prefix-pair fixtures, not by this task — persisted tests in tests/test_cli_json_source.py — depends on: SP-T1
- SP-T4: `FederationResult.degraded` — implements Brief:J4, Brief:S3 — acceptance (EARS): "WHEN a source raises or
  returns `ok=False`, federation SHALL append its name to `degraded`, in addition to the existing notes" — persisted
  test in tests/test_federation.py — depends on: —
- SP-T5: `compose_inbound` + `InboundContext` — implements Brief:J4, Brief:S2, Brief:S3 — acceptance (EARS): "WHEN
  the state pass resolved the key, `InboundContext.item` SHALL carry its live state, and `tasks`/`citations` SHALL
  carry the inbound pass's records in source order, de-duplicated by (kind, id)"; "IF a source in either pass is in
  `degraded`, THEN its name SHALL appear in `unknown`"; "IF the state pass resolved nothing for the key, THEN
  `item` SHALL be `None`" — persisted tests in tests/test_compose.py — depends on: SP-T2, SP-T3, SP-T4
- SP-T6: CLI `iris inbound` + MCP `inbound` — implements Brief:J5, Brief:S3 — acceptance (EARS): "WHEN `iris
  inbound <key>` runs, it SHALL print the `## item`, `## tasks citing`, `## citations` and `## unknown` sections
  defined in Interfaces, omitting an empty section, and the MCP tool SHALL return the same records from the same
  composer"; "IF the key is invalid, THEN the CLI SHALL exit 2 with a message and the MCP tool SHALL return an
  `error`"; "WHILE any source is unknown, the output SHALL NOT state that no records cite the key" — persisted
  tests in tests/test_cli_commands.py and tests/test_mcp_adapter.py; the read-only guard (tests/test_readonly_guard.py)
  passes with the new tool — depends on: SP-T5
- SP-T7: docs — implements Brief:J5 — deliverables: README (the `inbound` verb in the command list and the
  `cli-json` `inbound` stanza in the sources section); `sources.example.toml` (an `inbound` stanza on the
  knowledge-store example); docs/domain.md — a glossary entry **InboundContext** stating the norm: *the `item ⋈
  citing-records` composition — the records in other sources that cite one item by its parsed identity, joined to
  the item's live state; a degraded source is unknown, never "no citations"*; and the **Kind** entry naming
  `inbound` among the result-kinds; the stated-behavior prose (module docstrings) of `tasks.py` and `cli_json.py`
  rewritten to name the new mode, replaced not stacked — acceptance (EARS): "WHEN the docs check runs
  (tests/test_docs_check.py), it SHALL pass with the new verb listed" — depends on: SP-T6
- SP-T8 [v2]: earn datum on recorded real data — implements Brief:S1, Brief:S2, Brief:S4 — acceptance (EARS):
  "WHEN `compose_inbound` runs over the recorded fixtures for iris#5, iris#29, iris#38, iris#12 and iris#34, the
  composed tasks and citations SHALL equal the expected sets below, no extras and no misses"; "for iris#34 the
  result SHALL name task `^8g58ft` [open], resolved from the store's per-task record and the recorded open list";
  "WHEN the recorded prefix pairs run — `iris#1` vs `iris#12` and `iris#3` vs `iris#34` — the shorter key's result
  SHALL contain none of the longer key's tasks or citations" (Brief:C3/S4: one rule now covers both halves, so
  the pairs hold it on both); and a recorded latency of one live `iris inbound iris#38` run in the test's
  docstring — persisted test **tests/test_inbound_earn_datum.py** (fixtures under tests/fixtures/inbound/) —
  depends on: SP-T5, SP-T10
  Fixtures (decisions/0002 D4): **redacted** recordings, pinned to the store snapshot at commit `1f760ec` (the
  commit the v1 expected sets were assembled from) and re-recorded with a store CLI that carries
  fppfurtado/mneme#344 and #343 (≥ 0.26.2) over that snapshot. Kept: every task of both lists with its text
  reduced to its ref tokens; each record's locator as its file path plus a hash of its block slug (a task
  record keeps its `#^<anchor>`, which is an id and carries no text); each record's link type; the item states
  the forge returns. Nothing else from the private store is committed.
  Deliverable, before the expected sets are trusted: the **record-level, parser-independent oracle** (outside
  this repo: it reads the private store; its result is recorded in the test docstring) re-run over the same
  snapshot with the re-recorded inbound reads. It finds every raw line in the journal, the notes **and (v2)
  the task list** citing the key in three forms (`<repo>#<n>` with or without an `<owner>/` prefix, the forge
  URL, a bare `#<n>`) and maps each to the store record that contains it (a task line to its `#^<anchor>`
  record). It MUST pass its positive control first. Every raw `<repo>#<n>` line outside all returned records,
  owner-qualified included (Brief:C3: the same identity), is a MISS and fails SP-T8. The URL and bare forms
  are out of identity under Brief:C3 and are recorded with the line. The task expected sets are confirmed by
  this scan of the recorded task list, which is independent of both the store's rule and iris's `parse_refs`
  (Brief:S1's per-task scan). (v1 status: the oracle's positive control passed on 2026-10-29, with one MISS, a
  heading-only citation of iris#29, filed as mneme#344 and fixed in 0.26.1. Its `<repo>#<n>` pattern already
  matched the owner-qualified form, so the 7 keys had no owner-qualified-only line at that snapshot.)
  Deliverable (v2, the deciding assumption below): over the pinned snapshot, count the tasks of both lists
  with no anchor, and record, for each task the expected sets name, that the re-recorded inbound read returns
  it as `#^<anchor>`. Record the command and its output in the test docstring.
  Expected sets (v1's hand-assembled sets plus the one block the oracle found missing; to be confirmed by the
  oracle over the re-recorded reads, never widened to match output):
  - iris#5 — tasks: none · citations: journal 2026-08-14, 2026-09-06, 2026-09-10 (1 block each) + note
    `iris-dogfood-publish-hold-decision-state` (4 records)
  - iris#29 — tasks: none · citations: 8 records over journal 2026-09-05, -06, -08, -09 + the same note (v1's 7
    plus the 2026-09-06 block that cites iris#29 only in its heading)
  - iris#38 — tasks: none · citations: 4 records over journal 2026-09-08, -09 + the same note
  - iris#12 — tasks: none · citations: 5 records over journal 2026-09-04, -05, -08, -09
  - iris#34 — tasks: `^8g58ft` [open] · citations: the 3 non-task records of the inbound read
- SP-T9 [v2]: `cli-json` inbound `tasks` prefix — implements Brief:J2, Brief:C2, Brief:C3 — acceptance (EARS):
  "WHERE the `inbound` stanza declares `tasks = <prefix>`, the source SHALL emit each record whose locator
  starts with the prefix and has a non-empty remainder as `Node(kind="task", id=<remainder>, title="",
  roles=[])`, and SHALL NOT also emit it as a citation"; "WHERE `tasks` is not declared, every record SHALL be
  emitted as in SP-T3"; "IF a record starts with the prefix and its remainder is empty or not a whole anchor
  body, THEN it SHALL be emitted as a citation and the result SHALL carry a note naming the prefix"; "WHERE a
  `skip` prefix also covers a record the `tasks` prefix claims, the record SHALL be emitted as a task (`tasks`
  is classified before `skip`)" — persisted tests in tests/test_cli_json_source.py with a fake runner —
  depends on: SP-T3
- SP-T10 [v2]: retire the `tasks` inbound mode; third pass + task state in `compose_inbound` — implements
  Brief:J2, Brief:J4, Brief:S3, Brief:S4 — acceptance (EARS): "the `tasks` source's `produces` SHALL NOT contain
  `inbound`, and its inbound-mode code and tests SHALL be removed"; "WHEN the inbound pass returns ≥1 task node,
  the surfaces SHALL run a `chain` pass whose text names exactly those anchors (`^<id>` each), and
  `compose_inbound` SHALL give each task the `title` and `roles` of the `task_state` node with its id"; "WHEN the
  inbound pass returns no task node, the surfaces SHALL NOT run the third pass"; "IF a task's anchor is absent
  from `task_state`, THEN the task SHALL stay in `tasks` with `roles=[]`, and the CLI SHALL render it
  `[state unknown]`"; "IF the key is an anchor and a task node's id equals it, THEN that task SHALL NOT be in
  `tasks`"; "IF a source degrades in the third pass, THEN its name SHALL appear in `unknown`" — persisted tests
  in tests/test_compose.py, tests/test_tasks_source.py, tests/test_cli_commands.py and tests/test_mcp_adapter.py
  (CLI and MCP share the three-pass helper, parity) — depends on: SP-T9
- SP-T11 [v2]: `searched` + `not_covered` — implements Brief:J4, Brief:N5 consequence (iris#62 part 2) —
  acceptance (EARS): "the SYSTEM SHALL return `searched` on every `InboundContext`, holding exactly the names of
  the configured sources whose `produces` contains `inbound`"; "the SYSTEM SHALL return `not_covered` on every
  `InboundContext`, holding exactly the forge fan-in entry and the out-of-identity forms entry (forge URL, bare
  `#<n>`)"; "WHEN `iris inbound` runs, the CLI SHALL print the `## searched` and `## not searched` sections,
  whether or not any record was found, and the MCP tool SHALL return both fields"; "WHEN no record cites the
  key and nothing is unknown, the CLI SHALL print `# no records in <searched names> cite <key>`"; "WHERE no
  configured source produces `inbound`, `searched` SHALL be empty and the CLI SHALL NOT print that no records
  cite the key" — persisted tests in tests/test_compose.py, tests/test_cli_commands.py,
  tests/test_mcp_adapter.py — depends on: SP-T5
- SP-T12 [v2]: docs made false by v2 — implements Brief:J5 — deliverables: docs/domain.md — the
  **InboundContext** entry's Relations rewritten to the norm *the citing records, tasks included, are the ones
  the store's inbound read returns (BR01); iris reads only each citing task's state, by anchor, through the
  `chain` read; the result also names what it never searches (`not_covered`)*; the **Task** entry's `inbound`
  sentence rewritten to *in an `inbound` read a task is one the store's inbound read names as citing the key; its
  list state comes from the `chain` read, and it is never the item itself* (it now states that iris parses the
  task text, which v2 makes false); README (the `tasks` key of the `inbound` stanza, the `## searched` and
  `## not searched` sections); `sources.example.toml` (the example's `skip` replaced by `tasks`); the module docstrings of
  `tasks.py` (two modes, not three) and `cli_json.py` (the `tasks` prefix), replaced not stacked; the
  docstrings of the CLI and MCP `inbound` commands — acceptance (EARS): "WHEN the docs check runs
  (tests/test_docs_check.py), it SHALL pass"; "the glossary SHALL NOT state that iris parses task text for an
  `inbound` read" — depends on: SP-T10, SP-T11

## Coverage check (every in-scope Brief item → ≥1 task)
- J1 → SP-T1 (key) + SP-T5 (state, via the existing chain reads)
- J2 → SP-T9 + SP-T10 (v2; SP-T2 superseded) · J3 → SP-T3 · J4 → SP-T4, SP-T5, SP-T10, SP-T11 · J5 → SP-T6, SP-T7, SP-T12
- C1 → Architecture (composition in the layer; within-source reads stay in the sources, v2 tasks included) ·
  C2 → SP-T3, SP-T4, SP-T9, Cross-cutting · C3 → SP-T1, SP-T9, SP-T8 (one rule on both halves, held by fixtures)
- S1 → SP-T8 · S2 → SP-T5, SP-T8 · S3 → SP-T4, SP-T5, SP-T6, SP-T10 · S4 → SP-T8 (both halves, prefix pairs), SP-T10
- **S2b → expired** (v2). The Brief states S2b "expires when N3 lands upstream"; N3 (mneme#343) landed in
  mneme 0.26.2. No task carries it. SP-T2 showed it in v1.
- No task without a Brief item.

## Deliberate exclusions (from the Brief)
- Brief:N1 (thread re-expose), N2 (interpretation), N3 (per-task links in the store — landed upstream as
  fppfurtado/mneme#343; v2 consumes it), N5 (callers) — carried as written; nothing here builds them.
- Brief:N4 (forge fan-in) — fired on 2026-10-30 (agent-kit#3065) and now carried by **iris#62 part 1**, which
  routes it through a Brief amendment. No task here builds it. SP-T11 makes its absence visible in every result.
- Identity of the owner-qualified form (`<owner>/<repo>#<n>`): Brief:C3 counts it as the item's identity, since
  iris's parser accepts it. The store's rule does not index it today (probed 2026-11-11: three journal blocks
  citing `fppfurtado/media-context#3` and `fppfurtado/agent-kit#348` only in that form are not returned by
  `backlinks` on the bare key; 57 `<x>/<repo>#<n>` matches in the KB, and in the task list only one, `TJPA-368/pje-2.2#1998`,
  whose prefix is a ticket key, not an owner). The store's rule governs both halves (BR01), so the gap belongs to the store: filed as
  **fppfurtado/mneme#358**. It is not an exclusion and nothing narrows J2. SP-T8's oracle counts an
  owner-qualified-only line as a MISS, so the gap fails the earn datum loudly if a recorded key ever has one.
- iris#59 — v2 removes the two-rule divergence inside `inbound`. The divergence between iris's `_REPO_REF` and
  the store's rule remains for `context` and `chain`, outside this Spec. iris#59 stays open for that residue.
- Brief "anchor key" (J1 accepts `^<anchor>`): carried; no recorded fixture exercises an anchor-keyed item
  with a citing task today, so anchor matching is covered by SP-T1/SP-T10 unit tests only.

## Risks / unknowns
- (v2) A task the store names but neither list holds (the lists read after the store, a task edited in between)
  shows as `[state unknown]`, never as gone: SP-T10.
- (v2) The live config must declare the `tasks` prefix. Without it, the store's task records arrive as
  citations, or are dropped where an old `skip` names the task file, and the result loses its tasks with no
  error. `tasks` is classified before `skip`, so a leftover `skip` no longer hides them, but the key must be
  set. Rollout: the operator's private `sources.toml` (dotfiles, chezmoi) replaces `skip = ["knowledge/gtd.md"]`
  with `tasks = "knowledge/gtd.md#^"` in the same cycle, as a dotfiles PR, before the MCP restart.
- If the SP-T8 oracle finds a MISS (a raw `<repo>#<n>` line outside every record the store returned), the gap is
  in the store's inbound-link index, not in this composition, which only carries the store's answer: SP-T8
  then fails by design, and the gap is filed upstream to the store before the expected set is amended — never
  by widening the expected set to match the output.
- The `{key}` substitution passes `^anchor` / `repo#n` as one argv element (no shell) — no injection surface.

## Assumptions & invalidators
- On the 5 recorded items, every journal/note citation came from one store inbound read and only iris#34 has a
  citing task — so the join's lasting value is S2 (live state ⋈ citations). Invalidated if a use of `inbound`
  shows the agent still calling the store or `gh` directly for the same item.
- (v2) The store resolves every citing task per task, open and done. Probed on the LIVE store, 2026-11-11:
  `mneme backlinks <key> --json` returned `knowledge/gtd.md#^<id>` for the done tasks ^5m8f1u (expedidor#468),
  ^fayp8k (agent-kit#2183), ^hc6dct (gnucash-workbench#13), ^eqbata (drive-sync#92) and the open ^8g58ft
  (iris#34); `mneme task list --status open|done --json` showed 32 open and 7 done tasks, 0 without an `id`.
  This is not yet shown on the pinned snapshot: SP-T8's anchor-count deliverable shows it there. Invalidated if a
  task citing a key is returned only as its file, or if a task carries no anchor. SP-T8's iris#34 fixture would
  then fail.
- The three-pass cost is acceptable — invalidated if SP-T8's recorded latency exceeds a few seconds.

## Open questions
- Whether to also list the forge's own same-forge cross-references in `## item` (Brief open question) — resolved:
  not built. Value-rejected: the forge's own item read (Brief:N1's direct call) already returns them in one call; re-exposing them is the transport N1 rejects.
  (v2 note: iris#62 part 1 reopens forge fan-in as a Brief question; it does not reopen this one by itself.)
- Which surface carries the read (Brief open question) — resolved in Architecture: a new sibling verb.
