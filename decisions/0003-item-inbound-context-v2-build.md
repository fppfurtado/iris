# 0003 — Build decisions for item inbound context v2

- Date: 2026-11-11
- Context: the build of `specs/item-inbound-context.spec.md` v2 (SP-T8..SP-T12; iris#38, iris#62 part 2).
  These are the choices the frozen Spec left open, resolved while building. They bind the code; a Spec
  amendment may supersede them. 0002 D4 (redacted fixtures) and D5 (SP-T8 waits for mneme#344) are now
  discharged: the fixtures are in `tests/fixtures/inbound/`, and mneme#344 landed in 0.26.1.

## D1 — The three passes live in one helper the surfaces share

`iris._present.inbound_context(config, key, federate)` runs the three passes and composes. The CLI and the
MCP adapter both call it, so their parity holds by construction. Each surface passes its own `federate`,
which keeps the seam its tests already fake. `inbound_sources(config)` beside it derives `searched`.

## D2 — A citing task keeps the store as its source

The task node the store's inbound read names keeps `source` = that store, and takes only `title` and `roles`
from the task-state pass. The store is the source that decided the task cites the key (BR01); the task
list only supplied its state.

## D3 — With no inbound source, the CLI says nothing was searched

The Spec forbids claiming "no records cite" when `searched` is empty. The CLI prints
`# no configured source reads inbound — nothing was searched` on stderr instead of staying silent. That way
a missing `inbound` table in the config shows.

## D4 — The task fixtures keep only `iris#<n>` tokens

The Spec says to reduce each task's text to its ref tokens. Since v2, iris does not parse task text for
`inbound`, so the tokens test nothing beyond the title shown for a resolved task. The fixtures keep only the
`iris#<n>` tokens; the refs to other repos, some of them institutional, are dropped from the public repo.
Every task of both lists is still present, by id.

## D5 — The per-file split of the expected sets is the recording's

The Spec lists each item's citing files and totals. The split per file comes from the recording, which the
oracle confirmed record by record: 0 MISS, 0 records returned without a citing line. The test asserts the
files, the split and the totals.

## D6 — The v2 oracle stays in the private dossier

`oracle_v2.py`, its output and the raw recordings are in the gitignored
`.throughline/dossiers/item-inbound-oracle/` of the main tree, because they read the private store. The
test's docstring records the result.
