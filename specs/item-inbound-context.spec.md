# Spec: item inbound context — `iris inbound <key>`

- Frozen at: — (withheld, draft)
- Spec version: — (withheld pending approval)
- Source: Problem Brief `briefs/item-inbound-context.BRIEF.md` v1 (frozen 2026-10-29) — PRD skipped (a feature
  inside an existing product, the same path the F6-mínimo Spec took; tasks cite Brief J*/S* directly)
- Status: DRAFT — freeze pending approval
- Amendments: none
- Extends (not amends): `specs/f6-minimo-cross-repo-dep-chain.spec.md` v1 — reuses its ref parser
  (`parse_refs`) and the `chain`-mode reads of the `tracker` and `tasks` sources UNCHANGED to fetch the item's
  live state; adds nothing to `iris chain` and edits none of its code paths.

## Design

### Architecture
Flow: `key → parse_key → (1) federate kinds={chain} (the item's own live state, existing reads) + (2) federate
kinds={inbound} (the records citing the key) → compose_inbound → InboundContext → CLI / MCP`.

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
- **Two federation passes, not one combined mode** — because each existing source already routes by kind with a
  single mode per read (BR07); a combined `{chain, inbound}` read would need a second mode-combination branch in
  each source. Cost accepted: the task lists are read twice (≈4 knowledge-store CLI calls per `inbound` run).
  Re-evaluate if that cost is felt (S1 latency is recorded in SP-T8).

### Data model
- New kind `KIND_INBOUND = "inbound"` (core/source.py): a caller consuming the records that CITE a given key.
- New `Ref`-level helper `parse_key(key: str) -> Ref | None` (sources/_repos.py): the WHOLE stripped input must
  be exactly one ref (`<repo>#<n>` or `^<anchor>`), parsed by the existing patterns; anything else → `None`.
- Inbound records reuse `Node` (no new field):
  - a citing task → `Node(kind="task", id=<anchor id>, title=<task text>, roles=["open"|"done"], source=<name>)`;
  - a citing journal entry / note → `Node(kind="citation", id=<locator as the store returns it>,
    title=<locator>, roles=[<link type>], source=<name>)`.
- `FederationResult` gains `degraded: list[str]` — the names of sources that raised or returned `ok=False`
  (additive; `notes` unchanged). Lets a composer mark a source UNKNOWN by name rather than by parsing notes.
- New composed result `InboundContext` (frozen, core/compose.py): `key: str`, `item: Node | None` (the item's
  live state; `None` when unresolved), `tasks: list[Node]`, `citations: list[Node]`, `unknown: list[str]` (source
  names whose inbound or state read degraded), `notes: list[str]`.

### Interfaces / contracts
- `tasks` source, inbound mode (`Query.kinds ∋ inbound`): reads the open list (`command`) and the done list
  (`done_command`), and emits each task whose text's `parse_refs` CONTAINS the query key's `Ref` (equality on the
  typed Ref — so `iris#3` never matches `iris#34`, and `^ab` never matches `^abc`). A task citing itself
  (anchor key == its own id) is not emitted. Per-list isolation as in chain mode.
- `cli-json` source, inbound mode — **only when an `inbound` stanza is configured**:
  `[sources.<name>.inbound] command = [... "{key}" ...]`, `items = ""` (path to the array, empty = top level),
  `[sources.<name>.inbound.map] locator = "source"`, `type = "type"`, and optional `skip = ["<locator prefix>", …]`
  (records whose locator starts with a prefix are dropped — used to drop the task file the `tasks` source already
  resolves per task). `produces` gains `inbound` only when the stanza exists (an un-configured instance is never
  read for an inbound query). A read failure returns `ok=False` + note (never raises).
- `compose_inbound(key, state: FederationResult, inbound: FederationResult) -> InboundContext`.
- CLI `iris inbound <key>`: sections `## item` (key, state, title; or `unknown — could not resolve`), `## tasks
  citing <key>` (`^<id>  [open|done]  <first line>`), `## citations` (`<locator>  [<type>]`), `## unknown` (each
  degraded source name — never folded into "no citations"). Invalid key → message on stderr, exit 2. No records
  and nothing unknown → `# no records cite <key>` on stderr, exit 0.
- MCP tool `inbound(key) -> dict` with `key`, `item`, `tasks`, `citations`, `unknown`, `notes` — the same
  composer as the CLI (parity). Invalid key → `{"error": "..."}`.
- Telemetry: `log_request("inbound", key, nodes=<tasks+citations>, extra={"unknown": n})`, as the other verbs.

### Tech choices
- No new dependency; the knowledge-store inbound read is configured, not coded (BR02) — over a dedicated
  `mneme` adapter, which would name a private tool in the public core.

### Cross-cutting
- Read-only (BR03): no new write path; the read-only guard test covers the new MCP tool.
- Degradation (BR04): every new read isolates its failure to its own part of the result.

### Durable invariants
None new. The inbound match is an instance of the existing BR06 (identity-mediated join, docs/domain.md) — no
new cross-cutting rule is established.

## Task plan
- SP-T1: `KIND_INBOUND` + `parse_key` — implements Brief:J1, Brief:C3 — acceptance (EARS): "WHEN the input is
  exactly one `<repo>#<n>` or `^<anchor>` (surrounding whitespace allowed), `parse_key` SHALL return that `Ref`";
  "IF the input is empty, carries more than one ref, or carries any other text, THEN `parse_key` SHALL return
  `None`" — persisted unit tests in tests/test_refs.py — depends on: —
- SP-T2: `tasks` source inbound mode — implements Brief:J2, Brief:C3, Brief:S2b, Brief:S4 — acceptance (EARS):
  "WHEN a query declares `inbound`, the `tasks` source SHALL emit every open AND done task whose parsed refs
  contain the key, with `roles` = its list state"; "the source SHALL NOT emit a task that only contains the key as
  a prefix of another ref (`iris#3` vs `iris#34`, `^ab` vs `^abc`)"; "IF one list is unreadable, THEN the source
  SHALL still emit the other list's matches and report `ok=False` with a note" — persisted tests in
  tests/test_tasks_source.py with a fake runner — depends on: SP-T1
- SP-T3: `cli-json` source inbound mode — implements Brief:J3, Brief:C2 — acceptance (EARS): "WHERE an `inbound`
  stanza is configured, the source SHALL substitute `{key}` and emit one `Node(kind="citation")` per returned
  record, minus records whose locator starts with a `skip` prefix"; "WHERE no `inbound` stanza is configured, the
  source's `produces` SHALL NOT contain `inbound` and federation SHALL NOT read it for an inbound query"; "IF the
  command fails or returns a non-array, THEN the source SHALL return `ok=False` with a note, not raise" —
  persisted tests in tests/test_cli_json_source.py — depends on: SP-T1
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
- SP-T8: earn datum on recorded real data — implements Brief:S1, Brief:S2, Brief:S2b, Brief:S4 — acceptance (EARS):
  "WHEN `compose_inbound` runs over the recorded fixtures for iris#5, iris#29, iris#38, iris#12 and iris#34
  (captured 2026-10-29: `gh issue view`, `mneme task list` open+done, `mneme backlinks`), the composed tasks and
  citations SHALL equal the expected sets below, no extras and no misses"; "for iris#34 the result SHALL name task
  `^8g58ft` [open], where the recorded `backlinks` names only `knowledge/gtd.md`"; and a recorded latency of one
  live `iris inbound iris#38` run in the test's docstring — persisted test tests/test_earn_datum.py (fixtures under
  tests/fixtures/inbound/) — depends on: SP-T5
  Expected sets (hand-assembled 2026-10-29; the parser-independent raw search `grep -rlE "iris#N([^0-9]|$)|
  fppfurtado/iris/issues/N([^0-9]|$)" knowledge journal` returned the same FILES in every case):
  - iris#5 — tasks: none · citations: journal 2026-08-14, 2026-09-06, 2026-09-10 (1 block each) + note
    `iris-dogfood-publish-hold-decision-state` (4 records)
  - iris#29 — tasks: none · citations: 7 records over journal 2026-09-05, -06, -08, -09 + the same note
  - iris#38 — tasks: none · citations: 4 records over journal 2026-09-08, -09 + the same note
  - iris#12 — tasks: none · citations: 5 records over journal 2026-09-04, -05, -08, -09
  - iris#34 — tasks: `^8g58ft` [open] · citations: the 3 non-task records of `backlinks` (the `knowledge/gtd.md`
    record dropped by `skip`)

## Coverage check (every in-scope Brief item → ≥1 task)
- J1 → SP-T1 (key) + SP-T5 (state, via the existing chain reads)
- J2 → SP-T2 · J3 → SP-T3 · J4 → SP-T4, SP-T5 · J5 → SP-T6, SP-T7
- C1 → Architecture (composition in the layer; within-source reads stay in the sources) · C2 → SP-T3, SP-T4,
  Cross-cutting · C3 → SP-T1, SP-T2
- S1 → SP-T8 · S2 → SP-T5, SP-T8 · S2b → SP-T2, SP-T8 · S3 → SP-T4, SP-T5, SP-T6 · S4 → SP-T2, SP-T8
- No task without a Brief item.

## Deliberate exclusions (from the Brief)
- Brief:N1 (thread re-expose), N2 (interpretation), N3 (per-task links in the store — fppfurtado/mneme#343),
  N5 (callers) — carried as written; nothing here builds them.
- Brief:N4 (forge fan-in) — carried as the Brief armed it (`Trigger-source: #12 · …`); no task.
- Brief "anchor key" (J1 accepts `^<anchor>`): carried; no recorded fixture exercises an anchor-keyed item
  with a citing task today (the F7 pair `^fl1p26`/`^dogfd1` is no longer in the task lists — probe
  2026-10-29), so anchor matching is covered by SP-T1/SP-T2 unit tests only.

## Risks / unknowns
- When mneme#343 lands, `backlinks` may return the task blocks too, duplicating SP-T2's tasks under another
  locator — mitigation: the `skip` prefix already drops the task file; re-check SP-T8 then (S2b expires by the
  Brief's own statement).
- The `{key}` substitution passes `^anchor` / `repo#n` as one argv element (no shell) — no injection surface.

## Assumptions & invalidators
- On the 5 recorded items, every journal/note citation came from one `backlinks` call and only iris#34 has a
  citing task — so today the join's lasting value is S2 (live state ⋈ citations), and S2b is shown on one item.
  Invalidated if a use of `inbound` shows the agent still calling `backlinks` or `gh` directly for the same
  item (then the join is not carrying its weight).
- The two-pass federation cost is acceptable — invalidated if SP-T8's recorded latency exceeds a few seconds.

## Open questions
- Whether to also list the forge's own same-forge cross-references in `## item` (Brief open question) — resolved:
  not built. Value-rejected: the forge's own item read (Brief:N1's direct call) already returns them in one call; re-exposing them is the transport N1 rejects.
- Which surface carries the read (Brief open question) — resolved in Architecture: a new sibling verb.
