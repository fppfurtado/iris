# Problem Brief: item inbound context — what the other sources say about one work item

- Frozen at: 2026-10-29
- Mode: verifiable
- Distilled from dossier: `.throughline/dossiers/arm-3-single-item-deep-read.md` (re-entry 2026-10-29, sketch v4)
- Brief version: v1
- Status: frozen after approval on 2026-10-29 (operator "sim" to "Freeze the Brief as v1?")
- Independent read: ran — blind-critic, J3/J5/J6 (2026-10-29); 4 findings disposed in this draft: anchor key
  added (J1, F7, N4), the not-looking consequence recorded (N5), a lasting earn criterion (S2, old S2 → S2b),
  a parser-independent S1 check; F2 units corrected
- Amendments: none
- Parent frame: `working-state/programs/contexto-digital-integral/costura-iris-fonte.BRIEF.md — extends`
  (an instance of that Brief's cross-source composition job, at item granularity).
  `briefs/f6-minimo-cross-repo-dep-chain.BRIEF.md — adjacent` (that problem resolves the refs an item
  CITES, outbound; this one collects the records that cite the item, inbound — same item granularity,
  opposite direction). anchored: anchors f6-minimo-cross-repo-dep-chain.BRIEF.md; hits 4/4 disposed
- persona-input: n/a (no user-facing surface — an agent-facing CLI/MCP read; the operator consumes it
  through the agent by declared choice)

## Problem statement
An agent working one specific tracker item cannot get, in one call, the records in OTHER federated
sources that cite that item — the knowledge-store tasks, journal entries and notes that name it — joined
to the item's live state; so it assembles them by hand from at least two surfaces, and when it does not
think to look, a deciding fact recorded only in another source (a fired trigger, a decision, a verdict)
stays invisible to the work on the item.

The cost is not the two calls; it is that the deciding fact lives where the item's own tracker never
shows it. Observed: an item stayed classed as waiting for about seven weeks after its condition was met,
because the firing was recorded only in a knowledge-store note.

## Jobs in scope
- J1: Given an item key — a forge ref `<repo>#<n>` or a knowledge-store task anchor `^<anchor>` — fetch
  the item's live state (open/closed or open/done, title) from the source that owns it.
- J2: Collect every knowledge-store task that cites the key, resolved per TASK (its own anchor and
  status), not per file.
- J3: Collect every knowledge-store journal entry and note that cites the key, at the granularity the
  store resolves (entry/block).
- J4: Compose J1–J3 into one result keyed on the item, each citation carrying its source and a locator
  the agent can open; a source that fails to answer is reported as unknown, never as "no citations".
- J5: Serve it on the layer's production surfaces (CLI and MCP), so an agent working the item can reach it
  without knowing which sources hold citations.

## Non-goals (explicitly out of scope)
- N1: Re-exposing the item's own thread (body, comments, linked PRs) through the layer.
  Value-rejected: one direct, complete call already returns it (the forge CLI or the backlog tool's item read); the source is non-sensitive, so transport adds no value.
- N2: Interpreting what a citation means — declaring a trigger fired, a decision binding, an item done.
  Value-rejected: the layer composes and exposes data read-only; judgment stays with the consumer.
- N3 (filed upstream: fppfurtado/mneme#343): Making the knowledge store's own inbound-link read resolve tasks per task instead of per file — that
  is the store's within-source read (seam rule), filed upstream to the store, not built here.
- N4: Inbound citations from forge items (issues in any forge citing the key — cross-forge fan-in). Value
  plausible, evidence n=0 (the one recorded reverse-ref case, F7, is a task gated by another task, which J2
  covers) — deferred:
Trigger-source: #12 · session journal or this tracker — fires when (outside) a session finds an item's deciding gate only in a citation from a forge item
- N5: Making a specific skill or workflow (e.g. a backlog ranking or hygiene pass) call this read — that is
  the consuming tool's own decision, outside this layer. Consequence, stated plainly: this Brief makes the
  assembly ONE call (J4/J5); it does not by itself stop a deciding fact going unseen when no consumer makes
  that call — the seven-week case in the problem statement is prevented only once a consumer consults it.

## Constraints
- C1 (seam rule, ratified): cross-source composition is the layer's job; each source keeps its own
  within-source read and data. The composition must deliver what no single within-source call delivers.
- C2 (read-only, source-agnostic, per-source isolation): no write path; no adapter names a private
  instance; one source failing degrades only its own part of the result.
- C3 (identity by the key): a citation matches only by the parsed `<repo>#<n>` or `^<anchor>` identity the layer already
  derives from prose — never by substring coincidence (`iris#3` must not match `iris#34`).

## Success criteria
- S1 — verifiable (reproduces the hand-assembly): for each of 4 real items (F4), one call returns the
  item's live state and the SAME set of citing tasks, journal entries and notes that the hand-assembly
  finds (forge read + the store's inbound-link read + a per-task scan of the task store) — set equality,
  no extras, no misses. The expected set is also checked by a parser-independent raw text search of the
  store for each item's alternative forms (bare `#<n>` in that repo's context, the forge URL, the anchor):
  any citation found only by raw search is either a miss or a form recorded as out of identity (C3).
- S2 — verifiable (lasting earn — no single within-source call returns it): one result carries BOTH the
  item's live state from its owning source AND its citations from the other source; neither the forge read
  (no knowledge-store citations) nor the store's inbound-link read (no forge live state) returns both.
- S2b — verifiable (current granularity gain; expires when N3 lands upstream): for a key cited by a
  knowledge-store task, the result names that task by its own anchor and status, where the store's
  inbound-link read names only the task file.
- S3 — verifiable (graceful degradation): with one source made to fail, the result still carries the other
  sources' citations and marks the failed one as unknown.
- S4 — verifiable (identity, not coincidence): a ref that is a prefix of another (`#3` vs `#34`) matches
  only its own citations.

## Key facts and provenance
- F1: The store's inbound-link read for a `<repo>#<n>` ref returns journal entries and notes at
  entry/block level, but tasks only at FILE level (`knowledge/gtd.md`) — e.g. iris#34's citing task
  `^8g58ft` appears only as the file. — basis: retrieved (`mneme backlinks <ref> --json`, 2026-10-29).
- F2: Probe counts in the instrument's own units (journal entries and notes per block, tasks collapsed to
  one file entry) per ref: iris#34 → 4, iris#38 → 4, iris#12 → 5, agent-kit#1852 → 1,
  expedidor#310 → 0. — basis: retrieved (`mneme backlinks`, 2026-10-29, after `mneme index rebuild`).
- F3: The layer's existing task source already derives `<repo>#<n>` refs from each task's prose (per
  task), and its chain verb already parses refs and fetches specific issues' live state — both reusable.
  — basis: retrieved (`docs/domain.md`; `specs/f6-minimo-cross-repo-dep-chain.spec.md` Design, 2026-10-29).
- F4: In one session (2026-10-29), a backlog ranking and hygiene pass hand-assembled item ⋈ knowledge-store
  citations for 4 items (iris#5, #29, #38, #12); in all 4 the deciding fact (a met trigger, a resolved
  decision) was recorded only in the knowledge store. — basis: retrieved (this session's tracker reads and
  `iris-dogfood-publish-hold-decision-state` note, 2026-10-29).
- F5: The need was first logged on 2026-09-06 as a miss of an item's integral context (expedidor#310);
  the earlier frame (2026-09-08) parked it on "earns if the need recurs". — basis: retrieved (dossier,
  2026-09-08).
- F6: The layer's earn bar has already been met by two-source joins on a shared derived key with about two
  underlying calls (repo ⋈ open issues; GTD tasks ⋈ repo) — call count is not the disqualifier; what the
  join delivers beyond one within-source call is. — basis: retrieved (seam-rule record; iris#29 arm (a),
  PR #35; independent read 2026-10-29).
- F7: The earlier chain trial recorded that ref resolution is forward-only and that "the real gate
  sometimes lives in a reverse ref" (n=1): a task (`^fl1p26`) whose deciding gate was another task citing
  it (`^dogfd1`) — an anchor-keyed, knowledge-store case, not a forge one. — basis: retrieved (decision-state note §VEREDITO DO TRIAL,
  2026-09-09).

## Deliberate exclusions (from the dossier)
- Dossier candidate A/D (forge-thread re-expose) — carried as N1 (value-rejected), not as a job.
- Dossier residue R-a (reverse-ref arm of the chain verb) — narrowed: its knowledge-store half IS J2/J3
  (for both key types, J1); its forge fan-in half is N4 (armed).
- Dossier residue R-b (per-task inbound links in the store) — carried as N3 (upstream boundary).
- Dossier candidate B's "grounding/journal mentions" — narrowed to journal entries and notes that CITE the
  ref (J3): a relevance-ranked grounding hit does not cite the item by identity (C3), so it is not an
  inbound citation; the agent still has the grounding verb directly.

## Solution-space status (NOT a solution)
- Vehicle: committed (a read on the existing agent-context layer; the knowledge-store half alone would be
  the store's own read, N3).
- Settled when: S1's hand-assembly over the 4 items is written down as the expected result before design.

## Open questions carried forward
- Which existing surface carries it (a new verb, an item mode of the context verb, or an inbound arm of the
  chain verb) — a design decision; whichever touches the chain verb amends or extends its frozen Spec.
- Whether the item's live state should also list the forge's own same-forge cross-references (cheap, one
  call already in the forge read) or leave them to N1's direct call.
