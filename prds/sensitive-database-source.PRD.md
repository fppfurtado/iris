# PRD: Sensitive database sources — an access contract on the data path, with object-keyed knowledge

- Frozen at: 2026-11-12 (v1; v2 the same day)
- PRD version: v2
- Status: frozen after approval on 2026-11-12 (operator "Sim" to "Congelo `prds/sensitive-database-source.PRD.md` como v1, com o segundo repositório no escopo?"); v2 frozen after approval on 2026-11-12 (operator "Sim" to "Posso congelar `prds/sensitive-database-source.PRD.md` como v2?")
- Independent read: ran — throughline:blind-critic, lenses J1/J3/J5/J6 + conformance vs AGENTS.md and docs/domain.md BR01–BR07 (2026-11-12); 4 findings, all acted on (carrier table, J5 evidence, M4, R5, Open questions); conformance passed. The F3 replay design was read under J3 before it ran (5 findings, all acted on). v2 — ran — throughline:blind-critic, lenses J1/J3/J6 + conformance vs AGENTS.md and docs/domain.md BR01–BR07 (2026-11-12); 5 findings, all acted on in this draft: the part-(b) rule over-applied to a note that predates its failure → bound to "a case the note was not written from", checked per row (J1); "run" narrowed "answered" → "answered; INCONCLUSIVE does not answer" (J1); the invalidator over-claimed → scoped per test class, J5 falls only if both fail (J1); the precondition's rules contradicted test 2 → per-test rules, plus the missing "read under J3 before it runs" (J3); the amendment rationale contradicted test 1 → limited to the first replay's design. Conformance and C3 passed
- Source: Brief `briefs/sensitive-database-source.BRIEF.md` v2 (frozen 2026-11-12; v1 the same day). Vision skipped: a
  capability inside an existing product (iris; its direction is the `agent-context-layer` PRD and the parent
  Brief `costura-iris-fonte`), path Brief → PRD → Spec chosen by the operator 2026-11-12. Evidence for the
  carrier candidates: the S4 comment on iris#34 and the probes run for this PRD's blind read (2026-11-12).
- Product commitment confirmed: yes — 2026-11-12 (operator: the solution is software, a composite of an iris
  source adapter and a carrier outside iris for C4 and J7)
- Amendments: v1→v2 (2026-11-12, approved — operator "Sim"): follows Brief v1→v2. What changed: the J5-evidence
  paragraph, the M1 J5 rows' part (b), the F3 assumption, the deliberate-exclusions note and the Spec
  precondition are re-pointed from "a load-realistic replay of F3's case" to the Brief v2 "Settled when"
  pair of tests, and PR7(b) is bound to a case the note was not written from. Why: the Brief's F3 was
  restated from the 11-12 transcript. The general lesson was in context and was overridden twice. So the
  first replay's design could not test keying, because both its arms already held the lesson, and a note
  written from a failure carries its answer (Brief v2 S1(b))

## Context & users
For the operator's agents (any session, any repository) answering operational demands by querying an
organization's confidential PostgreSQL databases — today the institutional case-management system of the
Brief's case study. Today safety, confidentiality and correctness rest on rules the agent must remember, and
the recorded failures recur (`sensitive-database-source:F2`, `:F10`). This effort puts an access contract on
the data path and joins the recorded knowledge about the objects a query touches to its result. Users: the
agent as direct consumer, the operator as mediated consumer and as the person who answers for the custody
owner's rules. Not for: analysts running BI workloads (`:N3`), the organization's DBA, or anyone needing
writes through iris (`:C1`).

## Scope of THIS effort
- In this cut: serves `sensitive-database-source:J1`, `:J2`, `:J3`, `:J4`, `:J5`, `:J6`, `:J7`, and honors
  `:C1`–`:C4`. Which carrier serves each job is the Spec's decision, made among the candidates below.
  The PRD fixes only what follows from the constraints:
  - **iris** carries J5 and J6. Cross-source composition and the uniform surfaces are iris's by the domain
    seam rule BR01.
  - **J7 and the C4 bypass closure sit outside iris.** C1 forbids iris from carrying J7 (`:N1`). C4 puts the
    direct client outside any layer. Their home is named by the Spec, per the env-stack routing in the
    dotfiles repo.
  - **J1–J4 can sit in iris (an embedded guard) or in a local proxy on the data path,** which iris then
    queries through for J5. The Spec weighs both.
- Deferred: none of the Brief's jobs. Release non-goals below bound engines and harnesses.
- Why J5 is in this cut and not deferred: under the domain rule BR05 (`docs/domain.md`), a surface that only
  re-exposes one source's read earns its cost only through composition across sources. J5 (the query ⋈ the
  knowledge source, keyed by object identity) is that composition. Without J5 the iris carrier would rest on
  the parent Brief's transport-only value alone, which `:F6` and BR05 leave in tension (see Assumptions).
- **J5's value is not yet evidenced.** A first F3 replay (2026-11-12) ran INCONCLUSIVE: all six answers, the
  unkeyed arm included, avoided the failure. A later read of the 11-12 transcript found that the replay could
  not have tested keying. The general lesson about the audit store was already in the agent's context there,
  read in-session, and the agent set it aside twice (Brief v2 F3). So F3 no longer supports J5's value.
  Brief v2's "Settled when" names what can settle it: two tests, each with a same-content unkeyed arm.
  - A general lesson keyed to the touched object vs the same lesson in context, on F3's own case.
  - Object-specific knowledge keyed vs unkeyed, on a held-out case of the same class.
  Design, answers and grades are in private dossiers.
  Consequence: no carrier decision may rest on J5's value until those tests have answered (an INCONCLUSIVE
  run does not answer). J5 stays in scope (a Brief
  job), and the tests are a precondition of the Spec's carrier decision (Open questions for Spec).

## Carrier candidates per job (the Spec decides; evidence as of 2026-11-12)
Each eliminated candidate is stated with its disqualifier, whether that disqualifier is intrinsic or swappable,
and how it was established. A candidate that is "kept" has no disqualifier on record, and the Spec weighs it.
Candidates:
- **A1:** the best existing read-only database server for agents.
- **A2:** database-native controls.
- **A3:** a harness hook on the direct client.
- **P:** a local database proxy on the data path. Open-source examples found 2026-11-12: AgentIAM
  (AST-parsing, table allowlists, row limits); veil (per-column masking, read-only); hoop (wire-protocol
  gateway with result masking). Sources are READMEs and vendor posts, unverified.
- **G:** a guard embedded in the iris carrier, reusing A1's guard approach.

| Job | Kept for the Spec | Eliminated — disqualifier — intrinsic? — how established |
|---|---|---|
| J1 refuse writes | G; P | A3 by injecting client settings (read-only transaction, timeout): undone by an in-SQL `SET` — intrinsic to a client-requested setting — probe on a local PostgreSQL 16, 2026-11-12. A1 as a server: does not compose with J5 (below). A2: infeasible (operator, 2026-11-12) |
| J1 report the guarantee / refuse a weaker one | G; P (if it reports) | A1: no per-connection class concept — code read at `15c8e33` |
| J2 keep sensitive objects out of results | G; P; A3 post-tool replacement | A1: no mask/deny/redact policy — code read with positive control. A2: infeasible. A3 is NOT eliminated: a post-tool hook replaced a Bash output before the model saw it, and the original never reached the local transcript (probe, headless session, 2026-11-12); harness telemetry is off on this machine. A3's costs for the Spec: on formatted text a value's source column is lost under an alias or an expression, so it would re-run the same query analysis; it covers one harness only (J6); where harness telemetry is enabled, that telemetry captures the original output before the hook (hooks reference, read verbatim). S4's reading "A3 cannot filter results" is withdrawn |
| J3 load bound | G; P | A3 by client settings: undone by `SET statement_timeout` — intrinsic — same probe |
| J4 preconditions | G; P; A3 by client settings (encoding and search path are correctness defaults, not a guarantee against the agent) | — |
| J5 object-keyed knowledge | iris (BR01) | A1 as a separate server: a layer cannot see its queries — intrinsic to a separate server, dissolved by embedding (G) — architecture read. P: a proxy cannot attach notes to the agent's result — intrinsic — but iris querying through P keeps J5 in iris. A3 could add notes as context, but the composition is iris's by BR01 |
| J6 uniform surfaces | iris | A3: one harness only |
| J7 rollback-only writes | outside iris: a runner that parses and wraps the statements, reached by A3 routing | iris: forbidden by C1 — intrinsic to the iris carrier, not the job. A1: two modes only — code read. A3 by wrapping text (`BEGIN … ROLLBACK` around a script): a `COMMIT` inside the script commits everything before it, and what follows runs in autocommit — intrinsic to wrapping without parsing — probe on a local PostgreSQL 16, 2026-11-12 (both rows of a two-insert script with a `COMMIT` between them survived the `ROLLBACK`) |
| C4 close the direct client | A3 routing or refusal; credential custody (the credential reachable only by the chosen carrier); P plus credential custody (covers every client, `psql` included) | iris: cannot close a client it does not run — intrinsic |

S4's comparison is incomplete for A3 and P. The rows above extend it, and the Spec completes it (M4).

## Requirements
- PR1: Each database connection is declared in iris's private configuration with its instance identity and
  a declared write-guarantee class — `server-enforced` (the server refuses writes whatever the role does) or
  `client-requested` (only a read-only transaction requested by the client). A connection whose role can
  write and whose job includes writes is declared `writable` and is served only by the J7 carrier, never by
  iris. — acceptance: (a) a declared connection is queryable through iris; (b) the adapter code, tests,
  fixtures and docs name no instance (PR11); (c) WHEN a declared connection's credential would be read from
  a path inside a git working tree, the system SHALL refuse the connection and name the path class (not the
  path) in the error. — serves `sensitive-database-source:J6`, `:C2`, `:C3` — priority: must
- PR2: Every query result states the write guarantee that actually held on its connection, established by the
  system against the server, never taken from the declaration alone. — acceptance: (a) every result carries
  a guarantee field whose value is one of the declared classes and was established for that connection;
  (b) WHEN a connection declared `server-enforced` is found by the system to offer only a client-requested
  guarantee, the system SHALL refuse the query and run no statement on it; (c) replay on the case-study
  configuration: each production read replica reports `server-enforced`; the homologation database, if
  declared for reads, reports `client-requested`. — serves `:J1` — satisfies `:S2` — priority: must
- PR3: Every write attempt on a declared read-only-class connection fails, whatever carries J1, including multi-statement inputs
  and statements a parser allowlist would admit by statement type. — acceptance: the S4 cases W1 (temporary
  table create), W2 (`SELECT 1; COMMIT; <write>`) and W5 (`ANALYZE` on a scratch table, checked by the
  table's last-analyze time before and after) are refused on every declared connection, with a direct-client
  control showing each would have succeeded. — serves `:J1` — satisfies `:S2` — priority: must
- PR4: Declared-sensitive objects (whole tables, or columns of a table) never appear in a query result,
  whatever the query asks for. — acceptance: for a flagged column, each of these forms returns no value of
  it — the query is refused with the policy named, or the result omits it: `SELECT *`, an explicit column, an
  alias, an expression over the column, a whole-row reference (`t`, a row-to-JSON or row-to-text function),
  a subquery, a CTE, a view over the table, and a function that runs SQL given as text. A query that
  touches no flagged object returns unchanged. The case-study replay of the 11-10 failure (`:F2` J2 case)
  returns no stored credential. — serves `:J2` — priority: must
- PR5: Every query is bounded in duration by default, the bound configurable per connection, and a query
  that hits the bound is cancelled on the server, parallel workers included. — acceptance: WHEN a query runs
  past its connection's bound, the system SHALL stop it and, within 5 s of the bound, no backend of that
  query (including parallel workers) SHALL remain on the server; the replay of the 10-23 runaway scan
  (`:F2` J3 case) stops at the bound. The agent sets nothing for this to hold. — serves `:J3` — priority:
  must
- PR6: Each connection's declared correctness preconditions — client encoding, and how unqualified object
  names resolve across schemas — apply to every query without the agent setting them. — acceptance: (a) the
  accented-literal case of `:F2` (the 11-10 false zero) returns the correct count on the case-study replica
  with no encoding set by the agent; (b) a table that lives in different schemas on two declared instances
  resolves on both when queried unqualified, or the result names the schema each name resolved to. —
  serves `:J4` — priority: must
- PR7: When a query touches database objects, its result carries the recorded knowledge about those objects
  and their instance (what a column means, where a table's audit trail lives, which writes bypass the audit),
  joined to the query by the object's identity — never by text similarity. — acceptance: the J5 replay of
  `:S1` passes for each of the three `:F2` J5 cases: (a) a note keyed to the touched object is returned
  (positive control: a query on that object returns it; a query on an unrelated object does not); and (b)
  with the note in hand, the replayed first conclusion changes on a held-out case of the same class, not on
  a case the note was written from (M1). Surfacing a note alone does not pass. —
  serves `:J5` — satisfies `:S1` — priority: must
- PR8: The capability is served on iris's CLI and MCP surfaces with the same results, reachable from any
  session and any working directory. — acceptance: one query run through the CLI and through the MCP tool,
  each from a working directory outside the iris repository, returns the same rows, guarantee field and
  notes. — serves `:J6` — priority: must
- PR9: For every declared connection, the direct-client bypass is closed in the harness the operator's
  sessions query these databases from (today: Claude Code), so the PR2–PR6 guarantees hold on the data path.
  — acceptance: in a session of that harness, an attempt to reach a declared connection with a direct client
  (the incumbent command-line client, or a script using a client library) is refused with a pointer to
  iris (read-only classes) or to the J7 carrier (`writable` class); connections that are not declared are
  unaffected. The carrier lives outside iris; the Spec names it and its home. — serves `:C4` — priority:
  must
- PR10: On a `writable` connection, statements run only inside a transaction that is rolled back, unless the
  operator explicitly authorizes a commit for that one invocation; the statements' own output (for example a
  vendor script's embedded verification query) is returned before the rollback. — acceptance: (a) a
  vendor-style UPDATE script run through the J7 carrier on the homologation database returns its output and
  leaves no committed change, checked by a read before and after; (b) a commit happens only with a
  per-invocation authorization by the operator, recorded with the invocation; a standing authorization does
  not exist. The carrier lives outside iris (`:C1`, `:N1`). — serves `:J7` — priority: must
- PR11: Nothing that identifies an instance enters the public repository. — acceptance: a grep over the
  public repository (code, tests, fixtures, docs, commit messages of this effort) for the case-study
  identifiers kept in a private list returns zero hits; tests run against a synthetic database. — serves
  `:C3` — satisfies `:S3` — priority: must

## Non-goals (this release)
- NR1: Database engines other than PostgreSQL. The case study and every recorded failure are PostgreSQL;
  the guarantee probes and the guard are engine-specific. Value affirmed, deferred by grow-by-need.
  Trigger-source: #11 · session journal — fires when (outside) a session needs a sensitive non-PostgreSQL database as a source
- NR2: Writing or curating the J5 knowledge through iris. iris reads the notes from their home; capturing
  them stays in that home (`:C1`). Boundary, not a deferral.
- NR3: Carried from the Brief as boundaries: interpretation of results (`:N2`), analytics/BI (`:N3`),
  non-sensitive databases as the driver (`:N5`), deciding what the custody owner permits (`:N6`), other
  institutional sources (`:N7`). Composition across two databases of one system (`:N4`) stays deferred with
  the Brief's own arm (carrier #12, open).

## Success metrics
- M1 (from `:S1`): the replay set below passes on the case-study configuration. It is the expected result,
  written before the Spec's design. Case identifiers stay private (`:C3`); the private instantiation
  (instance, objects, exact statements) is written to a gitignored file before the Spec's design starts.

  | Case | Recorded failure (`:F2`) | Expected result |
  |---|---|---|
  | RP-J2 | `SELECT *` on an integration-config table put stored credentials into the transcript (11-10) | no credential value in the result, in every PR4 form |
  | RP-J3 | unbounded text filter became a parallel full scan on a shared replica (10-23) | stopped at the bound; no backend or parallel worker left within 5 s |
  | RP-J4a | server-encoding mismatch made an accented regex return a false zero (11-10) | correct count, no encoding set by the agent |
  | RP-J4b | the same table lives in different schemas across instances (11-11) | resolves on both instances, or the result names the resolved schema |
  | RP-J5a | accents stored as HTML entities in a document-content column; a text search missed half the hits (11-04) | the column's note surfaces; the replayed conclusion no longer reports the partial count as complete |
  | RP-J5b | a column's meaning read from its name gave a wrong conclusion, nearly published (11-11) | the column's note surfaces; the replayed conclusion reads the column correctly |
  | RP-J5c | an absence in the application audit, plus a status flag still set, read as "not executed", while a direct administrator write had made the change without audit and without touching the flag (11-12) | the notes keyed to the touched objects surface: the audit store's (direct writes leave no audit) and the status flag's (a record is disabled through a link, not this flag); "not executed" is not concluded from the absence or the flag |
  | RP-J1 | standing risk (S4 W1/W2/W5) | refused on every connection; guarantee stated; a weaker-than-declared connection refused |
  | RP-J7 | standing risk (homologation writes guarded only by rollback) | script output returned, nothing committed |

  Positive control for every J5 case: the same query shape on an unrelated object surfaces no note.
  Part (b) of every RP-J5 row ("the replayed conclusion …") is judged on a case the note was NOT written
  from (Brief v2 S1(b)). A note written after its failure, from that failure's answer, is judged on a
  held-out case of the same class: replaying its own failure with it would carry the answer. A note that
  predates the failure (in RP-J5c, the audit-store note, last modified before 11-12) may be judged on the
  row's own case. Which notes predate their failure is checked per row (by the note's dates) when the
  private instantiation is written. The row's own case always tests part (a): the note surfaces, keyed.
- M2 (from `:S2`): 100% of write attempts in the replay fail on every declared connection, each result
  stating which guarantee held; a connection mis-declared `server-enforced` is refused.
- M3 (from `:S3`): zero hits for the private identifier list over the public repository at the effort's
  landing.
- M4 (from `:S4`): the comparison covers every candidate in the carrier table for each of J1–J4 and J7,
  with its feasibility and verdict recorded. S4 (iris#34, 2026-11-12) recorded A1 and A2. This PRD extends
  it to A3 and P, and the Spec completes it. The layer builds a job only where it beats every feasible
  candidate, or where no candidate composes with J5.
- M5 (from `:S5`): before the first use on real data, the operator, acting under the custody owner's rules,
  accepts the read-surface policy declared for the case-study instance (a recorded yes on the declared list).

## Risks & dependencies
- R1: PR4 has no server-side backstop: database-native controls are infeasible (S4, operator 2026-11-12),
  and a SQL parser alone is not a security boundary (`:F4`, vendor guidance, unverified). Residual risk: an
  unlisted construction that reaches a flagged column. Mitigation: deny by default on flagged tables (only
  listed columns pass), an allowlist of functions, and the adversarial forms of PR4 in the test set; the
  residual is stated to the operator at M5.
- R2: If the Spec picks G, reusing A1's guard as a library inherits its parser dependency: A1 at `15c8e33` pins a `pglast`
  release no longer on PyPI; the probe ran with `pglast==7.20`. Last A1 PyPI release 2025-05. — retrieved
  (S4 probe, 2026-11-12). Mitigation: pin the parser; the Spec decides between vendoring the guard and
  writing one on the same approach.
- R3: The J5 knowledge home is undecided (Brief open question). Today the notes live in per-repository
  harness-memory stores, unversioned and outside any repository (`:F5`); the notes carry instance data, so
  their home must be private. Dependency: the Spec picks the home and the object-identity scheme.
- R4: A PR9 carrier that matches command text can be bypassed by another client (a script with a client
  library). Credential custody (the credential reachable only by the chosen carriers) is a stronger
  candidate than command matching, and with a proxy (P) it covers every client; a pre-tool hook can also rewrite a command's input (`updatedInput`, same
  reference), which opens routing the direct client through a carrier instead of refusing it. The Spec
  weighs these. Dependency: env-stack routing in the dotfiles repo
  for where a hook or a secret lives.
- R5: Query results transit the model provider. What may be read at all is the custody owner's call
  (`:N6`); PR4 enforces a declared policy, it does not decide one. Where harness telemetry is enabled, it
  records a tool's original output before any post-tool hook runs (hooks reference). It is off on this
  machine (probe, 2026-11-12). A placement upstream of the harness (G or P) keeps a flagged value out of that
  telemetry whatever its setting; a post-tool hook does so only while telemetry stays off.
- R6: Verifying against the case study needs the institutional VPN and the operator's credentials; CI runs
  only against a synthetic database. The M1 replay is an operator-present run.
- R7: The outside-iris carrier adds a second repository to the effort (scope declared to the operator at
  this PRD's freeze).

## Assumptions & invalidators
- The agent is careless, not adversarial: every recorded failure was an accident (`:F2`). — invalidated if a
  recorded failure shows a deliberate or injected evasion of a declared policy; then R1's residual is no
  longer acceptable without a server-side control.
- The job stays keyed, bounded operational lookups (`:F7`). — invalidated if sessions start running
  aggregate or analytics workloads against these connections.
- The sessions that query these databases run in Claude Code. — invalidated if a session list shows a
  case-study query from another harness; PR9 then needs that harness too.
- Notes keyed by object identity change the first conclusion. This is not supported by F3 as restated (Brief
  v2 `:F3`): the general lesson was in context, unkeyed, and was overridden twice. Each Brief v2 J5 test
  scopes to its own class of knowledge. If test 1 returns "the keyed arm is still overridden" (no better
  than the same lesson in context), keying general lessons earns nothing. If test 2 returns it (no better
  than the same object-specific knowledge unkeyed), keying object-specific knowledge earns nothing. If both
  return it, J5's value falls, and with it BR05's earn for the iris carrier. iris's role then reduces to J6
  transport, and the carrier choice reopens. If only one returns it, J5 stays in scope for the other class.
- The iris carrier earns under BR05 only through J5. — invalidated (in the other direction) if the domain
  model adopts the parent Brief's C6 transport-only value for sensitive sources; then J5 could be cut
  without re-justifying the carrier. Neither is decided here.

## Deliberate exclusions (from the Brief)
- None narrowed. The Brief's "Settled when" has two halves. S4 ran, and this PRD extends it. The J5 half (two
  tests, Brief v2) has not run; a first F3 replay ran INCONCLUSIVE and is superseded. So the vehicle for J1–J4
  stays open into the Spec. That is not a narrowing: this PRD
  commits requirements, not carriers.
- Brief open questions: Q2 (does the parent's transport value hold against an existing server) is answered
  in part. A1 as a server does not compose with J5 and fails J2/J7. P (a proxy) was not in S4, and the Spec
  weighs it;
  Q4 (is the database-native alternative obtainable) — answered: no (operator, 2026-11-12). Q1 (what may be
  read) carries as M5 and R5; Q3 (J5 home) and Q5 (result model) carry to the Spec below.

## Open questions for Spec
- **Precondition of the carrier decision:** the two J5 tests that Brief v2's "Settled when" names have
  answered (an INCONCLUSIVE run does not answer) before the Spec commits the carrier for J1–J4. Each design is
  read under J3 before it runs. Rules for both tests, from the J3 read of a superseded replay design
  (2026-11-12, 6 defects):
  - Each test has a same-content unkeyed arm, so content and keying do not vary together.
  - The labels cover a message that leans one way and also proposes a check.
  - The verdict bars are mutually exclusive.
  - Blinding removes every arm cue, including details only the note carries.
  Test 1 (a general lesson keyed vs the same lesson in context, on F3's own case):
  - The context matches the original session's at that point, including what it had already READ, not only
    what its index listed.
  - The cut and the instruction do not force a conclusion where the original session kept working.
  - The unkeyed arm reproduces the recorded failure first (≥2 of 3), else the result is INCONCLUSIVE.
  Test 2 (object-specific knowledge keyed vs unkeyed, on a held-out case of the same class):
  - The case is one the knowledge was not written from.
  - The unkeyed arm reaches the wrong first conclusion in ≥2 of 3 runs, else the case is too easy to
    discriminate, and the result is INCONCLUSIVE.
  Until both tests have answered, no carrier choice may rest on J5's value.
- The carrier for J1–J4: a guard embedded in iris (G), or a local proxy on the data path (P) that iris
  queries through; with credential custody for C4 in either case.
- J5's knowledge home and object identity: the knowledge store, a per-instance card in private
  configuration, or a data-catalog convention (column descriptions keyed by object, as data catalogs and
  schema-doc files do); how one object is identified across instances (instance, schema, table, column).
- The result model: a tabular result kind, or iris's nodes and excerpts.
- PR4's mechanism: deny by parse-tree reference, filter by result-column origin, or both.
- PR3/PR5: vendor A1's guard as a library or write one on the same approach; how the bound is configured.
- PR9's carrier: a harness hook (refusing or routing via `updatedInput`), credential custody, a proxy with credential custody, or a mix; and its home.
- PR10's carrier and home, and the per-invocation authorization mechanism.
- How the RP-J5 "conclusion changes" is judged (for example a blind replay graded against the expected
  result).
- One Spec, or one per carrier (iris; outside iris).
