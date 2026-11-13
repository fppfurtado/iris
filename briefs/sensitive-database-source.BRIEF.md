# Problem Brief: sensitive database sources — safe, knowledge-aware agent queries

- Frozen at: 2026-11-12 (v1; v2 the same day); v3 2026-11-13
- Mode: mixed
- Distilled from dossier: `.throughline/dossiers/database-as-source-sensitive-db-access.md`
- Brief version: v3
- Status: v1 frozen after approval on 2026-11-12 (operator "sim" to "Congelo `briefs/sensitive-database-source.BRIEF.md` como v1?"); v2 frozen after approval on 2026-11-12 (operator "Sim" to "Posso congelar `briefs/sensitive-database-source.BRIEF.md` como v2?"); v3 frozen after approval on 2026-11-13 (operator "Congelar v3 (Recomendado)" to "Posso congelar briefs/sensitive-database-source.BRIEF.md como v3?", which summarized the rate-comparison tests, the branch on test 1's verdict with no BR05 exception, and F12/F13 — the structure confirmed)
- Independent read: v1 — ran — throughline:blind-critic, lenses J3/J5/J6 (2026-11-12); 6 findings, all acted on
  in that draft: writable class restored as J7 with C1 bound to the iris carrier (J6 lens); F3 restated and
  the J5 replay given a positive control (J3); HTML-entity case reclassified J5 (J3/J5); S4 widened to three
  alternatives + DBA-obtainability question (J5); credential facts F11 (J5); instance name removed from F10.
  v2 — ran — throughline:blind-critic, lenses J3/J5/J6 (2026-11-12); 5 findings, all acted on in this
  draft: the forward test leaked the answer (the post-failure note carries it) → held-out case + a same-content
  unkeyed arm (J3); the "override whatever the keying" reading was missing → named as an outcome, and F3 now
  records the second override (J5/J1); "lost to a decoy" understated it → "set aside twice" (J3); the
  problem statement said "nowhere a session reaches" while the ticket queue was reached → "in no note a
  session loads"; S1 part (b) conflicted with the leak → bound to a case the note was not written from. C3
  clean
  v3 — ran — throughline:blind-critic, 2026-11-13, over the v3 drafts in sequence (one read per structure and
  fix round): J1/J3 + conformance (9 findings: F12 over-claimed a rate from n = 3; "two blind gradings" was one;
  "exact replay" hid the changed setting; post-hoc forking paths; S1(b) single-replay; …), J1/J3 narrow (A1–A3),
  J1/J3/J6 on the no-budget split (11: an iris surface without J5 conflicted with BR05; Brief vs PRD on building
  J5 early; "composes with J5" left as a J1–J4 ground; …), a pre-freeze J1/J6 read (2 High: keep-a-path renamed
  the J5 ground; the C6/R1 earn-or-retire citation did not cover the case), J1/J6/J3 on the branch structure
  (6 Medium: J6 reach/custody dropped on the second branch; leftovers; the three-run attempt could set the
  branch; product commitment stale), and two narrow delta reads (calibration-stop rule; J6 reach carrier;
  PR2 on the second branch). All findings acted on in the draft; C3 clean throughout
- Amendments: v1→v2 (2026-11-12, approved): F3 restated from the 11-12 session transcript (a general
  lesson about the audit store was in the agent's context and was overridden; the object-specific knowledge
  existed in no note); the F2 11-12 entry corrected to match; the problem statement's F3 sentence restated;
  the J5 half of "Settled when" re-pointed from replaying F3's case to two tests (a general lesson keyed vs in
  context, on F3's case; object-specific knowledge keyed vs unkeyed, on a held-out case); S1's J5 part (b)
  bound to a case the note was not written from. Why: v1's F3 was built
  from the memory index and the journal, not from the transcript, and the transcript contradicts it (found by
  a blind J3 read of the load-realistic replay design, verified against the transcript). Operator approval of
  the amendment direction: "Sim" (2026-11-12) to the recommended amendment; freeze of v2 approved: "Sim" (2026-11-12).
  v2→v3 (2026-11-13, draft): the two J5 questions of "Settled when" restated from "does keying change the
  first conclusion" to "does keying reduce the rate of the wrong first conclusion", over repeated fresh runs;
  the outcome sentence restated to match; S1 part (b) restated as a rate over repeated runs; F12 added (the
  measurement that motivates it). Why, test 1: on a replay of F3's original request with the context
  reproduced, the unkeyed arm repeated the failure in only 1 of 3 runs (F12; the rate is undetermined), and
  PRD v2's gate (the unkeyed arm fails in ≥ 2 of 3 first) passes rarely unless the
  failure rate is high. Why, test 2: no test-2 data exists; the same gate at n = 3 is unreliable on any case
  whose failure rate is not high, which on a held-out case is unknown — a design argument, not a result. Why,
  S1(b): one replay per case is one draw (F12), so a single changed conclusion cannot pass it. The amendment
  is set after seeing test 1's result, so the new test runs on fresh runs and the 3 + 3 already measured are
  not pooled into it. Amendment direction: delegated by the operator in session d84ee9e5 (2026-11-13; the
  decided next step recorded in iris#34's comment of that day: amend so test 1 asks whether keying reduces
  the failure rate). Then (same day, before any freeze): "Settled when" split in two (the J1–J4 vehicle no
  longer waits on J5's value; J5 settled by one supported reduction or two answers of no reduction of at
  least the stated minimum; J5 built only as a separable increment until then; an in-use signal can prompt
  the tests, never answer them); the outcome sentence restated to "no reduction of at least the stated
  minimum was observed"; F13 added. Why: the tests need a per-call budget the operator does not have (F13),
  and holding the whole vehicle on them would stop the J1–J4 jobs, whose value F2 already records, behind a
  measurement that cannot run (F13 as then worded; superseded by the last step below). Direction: the operator's "Pode seguir" (2026-11-13) to the recommended path
  "no further spend: decouple the J1–J4 carrier decision from J5's value; J5 a separable increment evaluated
  in use". That direction is narrowed here, and the narrowing is surfaced to the operator: "evaluated in use"
  becomes "an in-use signal may prompt the tests, never answer them", because an in-use signal does not hold
  content fixed while keying varies; and J5 is not built before its value is settled (an in-use evaluation of
  a built J5 would need it built first). S4's "none composes with J5" ground is bound to a settled J5. Freeze
  of v3: approved 2026-11-13 (Status).
  Then (same day, before any freeze): the operator obtained budget for the first test. "Settled when" for the
  J1–J4 vehicle now waits on test 1's verdict, which sets only whether the layer is in the first build
  (SUPPORTED → J5 and J6 in the layer; otherwise the first build is entirely outside the layer); while J5 is
  not built the layer has no surface for this source (BR05); F13 updated. Why: a blind read found that
  keeping a layer surface without J5 required an exception to BR05 that no ratified decision covers, and a
  "keep a path for J5" rule that re-introduced J5 as a ground for the J1–J4 elimination. With test 1
  runnable, the layer's presence can follow evidence instead. Direction: the agent's recommendation
  ("US$ 20 for test 1 only; if not SUPPORTED, go straight to the outside-the-layer first build"), followed by
  the operator obtaining that budget; the structure itself is confirmed at the v3 freeze. This last step
  supersedes the earlier same-day split (J1–J4 vehicle never waiting on J5; J5 always a later increment).
  J6 is read in three parts in "Settled when": its transport part (the layer's uniform surfaces) waits with
  J5 on the second branch; its reach from any session and its credential custody do not.
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
signs (F2). In one case a general lesson already in the agent's context was overridden by a misread column,
and the object-specific knowledge that would have prevented the wrong conclusion was recorded in no note a
session loads (F3).

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
  query on an unrelated object does not) and (b) with the note in hand, the rate of the wrong first
  conclusion falls, over repeated replays compared with the same case replayed without the note (one replay
  is one draw, F12) — surfacing a note alone does not pass. Part (b) is judged on a case the note was NOT written
  from: a note written after a failure, from that failure's answer, would pass (b) on its own case by
  carrying the answer. The replay set is written down as the expected result before design.
- S2 — verifiable (write guarantee): on every declared connection an attempted write fails, and the result
  states which guarantee held (server-enforced or client-requested); a connection declared
  server-enforced that turns out client-requested is refused.
- S3 — verifiable (no instance in public): no adapter, test, fixture or doc in the public repository names
  an instance (checkable by reading the code and a grep over the instance's identifiers kept privately).
- S4 — verifiable (earn against the alternatives): each of J1–J4 and J7 is compared against three
  alternatives to a layer build — the best existing read-only database server for agents (F4); database-
  native controls (a dedicated role, column privileges, views hiding sensitive columns); and a harness
  hook on the direct client (the only one that also closes C4's bypass). The layer builds a job itself
  only where it beats every feasible alternative; "none composes with J5" counts as a ground only once J5's
  value is settled and J5 is to be built (F13). The comparison, each alternative's feasibility and the
  verdict are recorded.
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
  application audit (queried in its separate history database) and a document status flag still set were
  read as "not executed", while the change had been made by a direct administrator write that leaves no
  audit and does not touch that flag, 11-12); outside the jobs ×2 (aggregate counts summed by eye,
  10-23; a "this is expected" claim drawn from a category name and refuted by a count, 11-10 — judgment,
  N2); plus one standing risk without an incident (homologation writes guarded only by rollback, N1). —
  basis: retrieved (case-study harness memory and iris#34 comments, read 2026-11-12).
- F3: The 11-12 J5 failure (F2) was not knowledge out of the session's reach. Earlier in that session the
  agent had read the case study's access note, which states that the audit-history database does not record
  direct writes. It then queried that database, found no matching operation, and wrote the caveat itself
  ("a direct administrator UPDATE does not show in this log") — and set the lesson aside TWICE. First, it had
  itself raised that a nulled link column might be the disabling done another way, and dropped that
  hypothesis on the audit absence ("the nulled link was changed by no one"). Second, in its message, a
  document status flag that still showed the documents active outweighed the caveat it had just written. The disabling had been done weeks earlier by a direct write that
  nulls that link and leaves the flag untouched. Before 11-12 that mechanism was recorded only in the
  change-ticket queue, in no note a session loads; it was recorded in the case-study repository's harness
  memory after the failure, the same day. So F3 does not show that keying a GENERAL lesson to the touched
  object changes a conclusion. The general lesson was in context, unkeyed, and it was overridden twice by an
  inference from the data. OBJECT-SPECIFIC knowledge (what this flag does not mean; how this system disables
  a record) existed in no note at the time. Whether that knowledge would have changed the conclusion is open:
  an override of knowledge in context may recur whatever its form or keying. n=1. — basis: retrieved (case-study session transcript, read
  2026-11-12 in the order: the access note's read, the agent's own null-link hypothesis, the audit query,
  the note dropping that hypothesis, the failing message, the correction via the ticket queue; access note last modified 2026-10-21; mechanism note created 2026-11-12, after the
  failure). The v1 statement of this fact (the lesson "sat only in the note's body, keyed to nothing the
  11-12 query touched") was drawn from the memory index and the journal, and is superseded.
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
- F12: At F3's own decision point, the recorded failure reproduced in 1 of 3 runs; its rate is undetermined. The original request
  that preceded the first override was rebuilt from the session's records (every message hash and the
  request digest reproduced; input tokens equal to the original's) and sent with one declared change: the
  reasoning-visibility setting, checked by a positive control and by thinking-token counts only. The
  unkeyed arm repeated the recorded wrong first conclusion in 1 of 3 fresh runs; the arm with the lesson
  keyed to the query result, in 0 of 3. n = 3 per arm says little about the failure rate (1 of 3 fits rates
  from about 1% to 91%); what it shows is that one run per arm is one draw, and that a gate requiring the
  unkeyed arm to fail in most of a few runs passes rarely unless the failure rate is high. — basis:
  retrieved (J5 test 1 run, 2026-11-13: one blind grading, and the author's arm-known grades agreeing on
  every label; iris#34 comments of 2026-11-13; design and raw responses in a private dossier).
- F13: J5's first test can run; the second cannot yet. A planning simulation (failure rate assumed ≈ 1/3 from F12; a noise model
  with correlated grader error assumed) put a rate comparison that can return either answer at about 80
  fresh runs per arm on F3's case, and 40 per arm failed its power floors under that model; a lower true
  rate needs more. The runs go through a direct-request vehicle billed per call. The operator first had no
  further budget for that vehicle and the dedicated key was retired after ≈ US$ 3 spent; later the same day
  the operator obtained a further US$ 20, which covers the first test at that size (≈ US$ 16, derived: run
  count × per-call cost); the second test's cost is not estimated, and it also needs a held-out case of the
  same class, which does not exist yet. The subscription-billed alternative, a
  fork of the session through the agent's own command-line client, was tried and voided: it hides the
  reasoning channel the grading reads and inserts turns at the decision point. — basis: retrieved for the
  budget and the voided fork (operator, 2026-11-13: "Não temos mais budget para api key", then "Consegui mais
  20 dólares"; iris#34 comment of 2026-11-13); derived for the run count and the cost (simulation of
  2026-11-13, private design dossier).

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
- Settled when, for the J1–J4 vehicle: S4's comparison against the best existing server is recorded
  (cheapest disconfirming test: configure that server in restricted mode against a read replica and replay
  the J2–J4 cases of F2) and completed against every feasible alternative, AND J5's first test (the
  general lesson, below) has returned a verdict from its rate design (fresh runs, bars fixed before the runs,
  its declared attempt number) — the 2026-11-13 three-run attempt (F12) does not set the branch; an attempt
  that ends without a verdict — or a test-1 design that ends without one (a calibration stop before any
  measured call, which is not itself an attempt, not cleared by its one declared re-grade; a spend or
  discard cap) — takes the "any other verdict" branch, unless the operator records a budget for a further
  test-1 attempt before the first build starts. That verdict sets only whether the layer is in the first
  build: SUPPORTED → J5 for the general-lesson class is built with it, and the layer carries J5 and J6;
  any other verdict → the first build stays entirely outside the layer, which enters for this source only
  once J5's value settles for a class. Among the alternatives, the choice rests on S4 merits in both
  branches (F13). On that second branch, J6's transport part (the layer's uniform surfaces) waits with J5;
  its reach from any session and its credential custody (C3) do not, and the outside-the-layer carrier
  serves them.
- Settled when, for J5's value: J5 testing has answered at least one of two questions with a supported
  reduction, or both with no reduction of at least the design's stated minimum. Each question has an arm
  that carries the same content unkeyed, so content and keying do not vary together:
  - Does keying a GENERAL lesson to the touched object REDUCE the rate of the recorded wrong first
    conclusion, compared with the same lesson in context? This is answerable on F3's own case without
    leaking the answer, because the general lesson does not contain it.
  - Does keying OBJECT-SPECIFIC knowledge REDUCE the rate of the wrong first conclusion, compared with the
    same knowledge unkeyed, on a case of the same class that the knowledge was not written from? A case it
    was written from would carry the answer (S1).
  Each question is a comparison of failure rates over repeated fresh runs, not a single run per arm: a
  recorded failure is one draw, and at its own decision point it can be the minority outcome (F12). Either
  test can return "no reduction of at least the stated minimum was observed". That outcome says J5's value
  for the class is not supported at that size, whatever the keying (F3); it does not show that keying has no
  effect. Each design is read under J3 before it runs. J5 is built for a class only once that class's test
  returns SUPPORTED; while J5 is not built, the layer has no surface for this source, since a surface that
  only re-exposes one source does not earn its cost (the domain model's BR05). A
  signal observed in use (a J5-class failure of F2's kind recorded again after this freeze) can prompt the
  tests; it cannot answer them, because it does not hold content fixed while keying varies.

## Open questions carried forward
- What may an agent read from the case-study databases at all (credentials only, or also personal data
  and secret proceedings), given that query results transit the model provider? — the custody owner's
  call; it sets the content of J2's policy.
- Does the parent Brief's transport value for a sensitive source (its C6, F6 here) still hold when an
  existing server already supplies a uniform interface (F4)? Decided for this effort by the domain model's
  BR05 (no layer surface without J5), against the parent's C6; reopened only if the domain model adopts C6
  as a standing earn for sensitive sources.
- Where does J5's knowledge live as a source — the knowledge store, a per-instance card in private
  configuration, or the repositories' notes — and how is a database object identified across them?
- Is the database-native alternative obtainable at all? On a standby replica, roles, grants and views
  are created on the primary, which only the organization's DBA reaches (F1), so it rests on a request the
  custody owner must accept.
- Does the layer's result model (nodes and excerpts) carry tabular results, or does a database source need
  a new result kind?
