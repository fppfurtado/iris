# Problem Brief: sensitive database sources — safe, knowledge-aware agent queries

- Frozen at: 2026-11-12
- Mode: mixed
- Distilled from dossier: `.throughline/dossiers/database-as-source-sensitive-db-access.md`
- Brief version: v1
- Status: frozen after approval on 2026-11-12 (operator "sim" to "Congelo `briefs/sensitive-database-source.BRIEF.md` como v1?")
- Independent read: ran — throughline:blind-critic, lenses J3/J5/J6 (2026-11-12); 6 findings, all acted on
  in this draft: writable class restored as J7 with C1 bound to the iris carrier (J6 lens); F3 restated and
  the J5 replay given a positive control (J3); HTML-entity case reclassified J5 (J3/J5); S4 widened to three
  alternatives + DBA-obtainability question (J5); credential facts F11 (J5); instance name removed from F10
- Amendments: none
- Parent frame: `working-state/programs/contexto-digital-integral/costura-iris-fonte.BRIEF.md — extends`
  (this is the frame that Brief's F5 deferred and armed: a database-type source, sensitive, instance only
  in private config). `briefs/item-inbound-context.BRIEF.md — adjacent` (that problem collects the records
  that cite one work item; J5 here collects the records that speak about one database object — same
  "records about a key" shape, a different key). anchored: anchors item-inbound-context.BRIEF.md; hits 12/12 disposed
- persona-input: n/a (no user-facing surface — an agent-facing read; the operator consumes it through the
  agent by declared choice)

## Problem statement
An agent that answers an operational demand by querying an organization's confidential databases has no
access contract that holds, on the data path, what it may write, what may reach its transcript and how
much load one query may impose — and no way to see, at query time, what is already known about the
objects it is querying — so the safety of a shared database, the confidentiality of its contents and the
correctness of the results rest on rules the agent must remember, and the recorded failures recur.

The cost is concrete: a credential pulled into a transcript, a runaway scan cancelled by hand on a shared
production replica, and several wrong conclusions caught only before publication in documents a person
signs (F2). In at least one case the knowledge that would have prevented the wrong first conclusion was
already recorded, but not where the query was being made (F3).

## Jobs in scope
- J1: For each declared database connection, establish the write guarantee that actually holds — enforced
  by the server (a read-only replica or role) or only requested by the client (a read-only transaction) —
  report it with every result, and refuse a connection whose guarantee is weaker than the one declared.
- J2: Keep declared-sensitive objects (tables, columns) out of query results, so they never reach the
  agent's transcript, whatever columns the query asks for.
- J3: Bound the load one query may impose on a shared database (at minimum a time limit), applied to every
  query without the agent having to set it.
- J4: Apply each instance's correctness preconditions (client encoding, object qualification across
  schemas) to every query without the agent having to remember them.
- J5: When a query touches a database object, surface the recorded knowledge about that object and its
  instance — what a column means, where the audit trail of a table lives, which writes bypass the audit —
  joined to the query by the object's identity.
- J6: Serve J1–J5 on the layer's uniform surfaces (CLI and MCP), reachable from any session or repository,
  with credentials outside every repository's working tree and the instance only in private configuration
  (F11 records where they are today).
- J7: On a connection whose role can write (a homologation / test database where writes are part of
  the job), let writes happen only inside a transaction that is rolled back, unless the operator explicitly
  authorizes one — so the guard is not the agent remembering to roll back.

## Non-goals (explicitly out of scope)
- N1: The layer itself performing writes, rolled back or not — boundary: iris is read-only by
  construction (C1). This bounds the iris carrier only, not the problem: J7 stays a job, so a solution that
  uses iris for J1–J6 must carry J7 elsewhere (server, harness or the direct client), and say where.
- N2: Interpreting results (whether a count, an absence or a pattern supports a conclusion) — boundary:
  judgment stays with the consumer; the layer composes and exposes.
- N3: Analytics or BI workloads over the databases — boundary: the job is keyed, bounded operational
  lookups (F7).
- N4: Composing one answer across two databases of the same system by a shared entity key (e.g. a
  replica's rows joined to a separate audit-history database). Value plausible, evidence n=1 (F8) —
  deferred:
Trigger-source: #12 · session journal or this tracker — fires when (outside) a session hand-composes a keyed join across two databases of one system for a second time
- N5: Non-sensitive databases as the driver (e.g. a personal SQLite book) — boundary: they may fall under
  the same adapter later as passthrough, but they do not shape this problem.
- N6: Deciding what the custody owner permits an agent to read — boundary: the layer enforces a declared
  policy (J2); what the policy contains is the owner's call (open question).
- N7: Other institutional sources the same sessions consult (a service-desk API, an issue tracker) —
  boundary: separate sources, already tooled elsewhere.

## Constraints
- C1 (inherited invariant, binds the iris carrier): read-only by construction — no write path in any
  iris surface or source. It constrains what iris may carry, not which jobs the problem has (N1, J7).
- C2 (inherited, parent C6/C7): the layer owns the uniform interface and cross-source composition; each
  source keeps its data and within-source reads; every adapter is public and names no instance, and the
  concrete instance lives only in private configuration.
- C3 (custody): the data belongs to its organization, whose custody owner is not necessarily the
  operator; nothing that identifies an instance (hosts, schemas, object names, rows) enters the public
  repository — code, tests, fixtures or docs — and credentials stay outside every repository.
- C4 (enforcement locus): a guarantee (J1–J4) counts only where it is enforced on the data path — by the
  server or by the layer — never by the agent's choice of query. A direct client left open to the same
  connection bypasses any layer-side guarantee; closing that bypass sits outside the layer (harness or
  server configuration) and is a dependency the solution must name, not assume.

## Success criteria
- S1 — verifiable (replay of the recorded failures): for each recorded failure in the J2–J5 classes (F2),
  a replay against the case-study configuration prevents it: the sensitive column is absent from the
  result (J2); the runaway query stops at the bound (J3); the encoding false zero does not occur and the
  object resolves in the right schema (J4). For a J5 case the replay passes only if (a) the recorded note is
  keyed to the very object the query touched (a positive control: a query on that object returns it, a
  query on an unrelated object does not) and (b) with the note in hand, the replayed first conclusion
  changes — surfacing a note alone does not pass. The replay set is written down as the expected result
  before design.
- S2 — verifiable (write guarantee): on every declared connection an attempted write fails, and the result
  states which guarantee held (server-enforced or client-requested); a connection declared
  server-enforced that turns out client-requested is refused.
- S3 — verifiable (no instance in public): no adapter, test, fixture or doc in the public repository names
  an instance (checkable by reading the code and a grep over the instance's identifiers kept privately).
- S4 — verifiable (earn against the alternatives): each of J1–J4 and J7 is compared against three
  alternatives to a layer build — the best existing read-only database server for agents (F4); database-
  native controls (a dedicated role, column privileges, views hiding sensitive columns); and a harness
  hook on the direct client (the only one that also closes C4's bypass). The layer builds a job itself
  only where it beats every feasible alternative, or where none composes with J5; the comparison, each
  alternative's feasibility and the verdict are recorded.
- S5 — deliberative: the custody owner (or the operator acting under the owner's rules) accepts the
  read-surface policy declared for the case-study instance.

## Key facts and provenance
- F1: In the case study (an institutional case-management system), the agent reaches three connection
  classes with three different write guarantees: production read replicas, where writes are refused by
  the server regardless of role (`pg_is_in_recovery = t`); a homologation database where the agent's role
  owns the tables and only a `BEGIN … ROLLBACK` discipline prevents writes; and the production primary,
  which the agent cannot reach at all (writes go through a human change ticket). — basis: retrieved
  (probes in a case-study session, 2026-11-11; iris#34 comment of 2026-11-11).
- F2: Recorded failures 2026-10-23 → 2026-11-12, classified by job (10 entries: hand classification by
  the framer over the case-study repo's harness-memory notes and iris#34's comments; small n, not a
  census): J2 ×1 (a `select *` on an integration-config table put stored credentials into the transcript,
  on a read-only replica, 11-10); J3 ×1 (an unbounded text filter became a parallel full scan on a shared
  production replica and was cancelled by hand, 10-23); J4 ×2 (a server-encoding mismatch made an
  accented regex return a false zero, 11-10; the same table lives in different schemas across instances,
  11-11); J5 ×3 (accents stored as HTML entities in a document-content column made a text search miss half
  the hits even with the right encoding, 11-04 — a property of the data, known only as a note; a column's
  meaning read from its name produced a wrong conclusion nearly published, 11-11; an absence in the
  application audit log was read as "nothing changed" while the audit lives in a separate database and
  direct administrator writes leave no audit, 11-12); outside the jobs ×2 (aggregate counts summed by eye,
  10-23; a "this is expected" claim drawn from a category name and refuted by a count, 11-10 — judgment,
  N2); plus one standing risk without an incident (homologation writes guarded only by rollback, N1). —
  basis: retrieved (case-study harness memory and iris#34 comments, read 2026-11-12).
- F3: The class behind the 11-12 J5 failure (direct batch updates that leave no audit trail) had been
  recorded on 2026-10-28 in the same repository's harness-memory store, and that store's index line for it
  was loaded into the 11-12 session. But the index line described one instance (a court-unit migration)
  by its own tables; the general lesson ("direct writes leave no application audit") sat only in the note's
  body, keyed to nothing the 11-12 query touched. The first conclusion was still "nothing changed",
  corrected only after searching the change-ticket queue. n=1: the knowledge reached the session but was not
  keyed to the object being queried, so it was not applied. — basis: retrieved (memory note and index
  line dated 10-28, file mtime; journal block 2026-11-12; checked 2026-11-12 after the blind read).
- F4: Existing database servers for agents already cover part of J1–J3: one popular Postgres MCP server has
  a restricted mode that limits the agent to read-only transactions plus an execution-time limit; policy
  servers offer per-table/column rules or masking; the reference Postgres MCP server was deprecated after
  its read-only mode was bypassed with multi-statement input. The recurring guidance is to enforce
  read-only in a database role and to treat a SQL parser alone as no security boundary. — basis:
  retrieved (web search: crystaldba/postgres-mcp README mirrors; glama.ai listings of pgguard-mcp and a
  deprecated-server fork; hoop.dev blog — 2026-11-12; vendor claims, unverified against the projects).
- F5: Today the knowledge J5 needs lives in a per-repository harness-memory store (13 database-related
  notes in the case-study repository's store), loaded by an index, unversioned and scoped to one
  repository; other repositories that query the same databases have none. — basis: retrieved (probe of
  the memory stores, 2026-11-12).
- F11: Credentials in the case study: one personal directory-login password authenticates the read
  replicas, the audit-history database and other read entries, all held in the client's password file; the
  writable homologation role's password lives in a gitignored env file inside a repository's working tree
  (not tracked, but inside the tree). A per-connection guarantee therefore holds only where the server
  enforces it: the same credential reaches several classes. — basis: retrieved (case-study access notes;
  `git check-ignore` on the env file, 2026-11-12).
- F6: iris's earn history: three isolated-facet candidates were disconfirmed as passthrough; what earned
  was a keyed join over co-identifiable sources. The parent Brief nonetheless judged a sensitive source's
  re-exposure valuable as transport alone (its C6: a uniform, sovereign interface instead of a scattered
  client and password file). — basis: retrieved (iris#11 comment 2026-09-04; parent Brief F5, C6).
- F7: The case study's query shape is keyed point lookups and small joins (by process number or ids),
  run with a time limit and an explicit client encoding, to verify state before or after a change. —
  basis: retrieved (query catalog, iris#34 comment of 2026-11-11).
- F8: One session (2026-11-12) answered a request by composing a production replica with a separate
  audit-history database of the same system (by entity id) and with change tickets, and dated an
  unaudited write by calibrating transaction ids against neighbouring timestamped inserts (validated on 2
  known-time cases). — basis: retrieved (iris#34 comment of 2026-11-12; journal 2026-11-12).
- F9: iris already composes "the records that cite one key" (its inbound read) for two key types — a
  forge item and a knowledge-store anchor; a database object is not one of them. — basis: retrieved
  (`specs/item-inbound-context.spec.md`, `docs/domain.md`, 2026-11-12).
- F10: The need recurred four times in case-study sessions (2026-10-28, 11-06, 11-11, 11-12) without the
  frame running, each time displaced by the deadline of the live case that brought the need. — basis:
  retrieved (iris#34 thread, read whole 2026-11-12).

## Deliberate exclusions (from the dossier)
- Dossier J1 (write policy per connection class) — carried split: the read-only classes as J1, the
  writable class as J7; C1 bounds only the iris carrier (N1). (The blind read caught that an earlier draft
  dropped the writable class by C1, a property of one carrier while the vehicle is open.)
- Dossier open question Q2 (where the Brief lives) — resolved by the operator (2026-11-12): evaluated as
  an iris product problem, with the case study as its use case; not carried.
- Dossier open question Q1 (custody) — carried as an open question below and as N6 / S5; it does not
  block the product problem.

## Solution-space status (NOT a solution)
- Vehicle: open — the jobs could be served by an existing server plus server-side roles and harness
  configuration, by a layer adapter, by a knowledge join alone, or by a mix.
- Settled when: S4's comparison against the best existing server is recorded (cheapest disconfirming test:
  configure that server in restricted mode against a read replica and replay the J2–J4 cases of F2), and
  J5's replay (F3's case) shows whether a note keyed by object identity changes the first conclusion.

## Open questions carried forward
- What may an agent read from the case-study databases at all (credentials only, or also personal data
  and secret proceedings), given that query results transit the model provider? — the custody owner's
  call; it sets the content of J2's policy.
- Does the parent Brief's transport value for a sensitive source (its C6, F6 here) still hold when an
  existing server already supplies a uniform interface (F4)? This Brief leaves it open; S4 answers it.
- Where does J5's knowledge live as a source — the knowledge store, a per-instance card in private
  configuration, or the repositories' notes — and how is a database object identified across them?
- Is the database-native alternative obtainable at all? On a standby replica, roles, grants and views
  are created on the primary, which only the organization's DBA reaches (F1), so it rests on a request the
  custody owner must accept.
- Does the layer's result model (nodes and excerpts) carry tabular results, or does a database source need
  a new result kind?
