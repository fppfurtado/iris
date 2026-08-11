# Backlog

Tracker-agnostic backlog for iris (no forge remote yet). Migrate to issues once a
remote is established.

## Before public flip (operator intends to open-source)
- **Establish a remote** and decide private-now / public-when. PR-per-cycle landing needs it.
- **Add a LICENSE** (operator's choice) — required before public.
- **Add README.md** at the repo root — the public entry doc (distinct from AGENTS.md).
- **Public packaging metadata** in `pyproject.toml`: `readme`, `license`, classifiers,
  `project.urls`, author — before any publish.
- **Trace trailers reference the private brief** (`Serves: arranjo:J*`) — abstract tokens,
  no facet content, but they name the private brief. Scrub the slug before the public flip
  if that reference is unwanted; full J-trace stays recoverable via the private contracts.

## Product / engineering follow-ups
- **Config discovery is cwd-relative** (`IRIS_CONFIG` env, else `./sources.toml`). Add a
  packaged default / XDG lookup so `iris` works from any directory.
- **Test hygiene**: the constellation fixture builder is duplicated across
  `test_federation.py`, `test_mcp_adapter.py`, `test_s2_proof.py` — extract a shared
  `conftest.py` fixture.
- **mneme `relation`/`inventory` reads lack `--json`** (spike SP-T3). If a later phase needs
  them, request the flag upstream in mneme or add a text-parse fallback.

## Deferred by the Spec/PRD (future phases)
- Facets: finances/gnucash, env-stack, tjpa work-corpus (grow-by-validated-need).
- Curated cross-facet bridges (J6), agent-mediated actuation (J5), knowledge curation (J3).
- MCP HTTP/remote transport (Phase 1 is stdio-only).
