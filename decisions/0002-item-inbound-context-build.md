# 0002 — Build decisions for item inbound context

- Date: 2026-10-29
- Context: the build of `specs/item-inbound-context.spec.md` (v1, iris#38 part 3), SP-T1..T7. These are the
  choices the frozen Spec left open, resolved while building. They bind the code; a Spec amendment may
  supersede them.

## D1 — In the `tasks` source, `inbound` wins over `chain`

`read` routes a query that declares `inbound` to the inbound mode before checking `chain`. The surfaces never
send both kinds in one query (the Spec's two federation passes), so the order only makes a mixed query
deterministic instead of silently answering with one mode's records.

## D2 — `cli-json` declares `produces` per instance

The class keeps `produces = {hits}`; an instance whose options carry an `inbound` table sets its own
`produces = {hits, inbound}` in `__init__`. Federation reads `produces` from the instance, so an instance
without the table is skipped for an inbound query with no change to federation.

## D3 — A citation record without a locator is dropped

A record whose mapped locator is empty has no identity to show or de-duplicate by (the Node id is the
locator), so it is not emitted. A record with no link type is emitted with empty `roles`.

## D4 — SP-T8 fixtures are redacted recordings, pinned to one store snapshot

The repo is public and the knowledge store is private, so the recordings SP-T8 names cannot be committed
verbatim (operator decision, 2026-10-29). The fixtures keep only what the join reads: every task of both
lists with its text reduced to its ref tokens (so "no extras" is still tested over the whole list), each
locator as its file path plus a hash of its block slug, and the issue state the forge returns. The store
snapshot is pinned to the commit the Spec's expected sets were assembled from (it reproduces their counts
exactly); the live store has grown since. The oracle reads the private store, so it stays outside this repo,
and its result is recorded in the test. This changes where and in what form SP-T8's fixtures live, so it
lands with a Spec amendment (v1.1) in the SP-T8 cycle.

## D5 — SP-T8 waits for the store fix of a title-only citation

The SP-T8 oracle (positive control passed) found one miss on the pinned snapshot: a journal block that cites
`iris#29` only in its heading is not returned by the store, whose link index parses the block body only —
filed upstream as fppfurtado/mneme#344. By the Spec's own rule SP-T8 fails by design until the store is
fixed, and the expected set is not widened to cover it. SP-T1..T7 land first (operator decision, 2026-10-29);
SP-T8 is built after that fix, and iris#38 stays open until then.
