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
- **Federation runs every source per command (review finding #1).** `repos` (needs only
  nodes) still invokes grounding sources — e.g. a cli-json source runs with an empty
  query on every `repos`; `ground` triggers the full constellation scan it discards.
  Works (results are filtered) but wasteful + semantically loose. Make federation
  kind-aware: a command declares which sources/result-kinds it needs, or skip a source
  whose output the command discards. Next-phase refinement (skeleton S2 proof holds).
- **Test hygiene**: the constellation fixture builder is duplicated across
  `test_federation.py`, `test_mcp_adapter.py`, `test_s2_proof.py` — extract a shared
  `conftest.py` fixture.
- **mneme `relation`/`inventory` reads lack `--json`** (spike SP-T3). If a later phase needs
  them, request the flag upstream in mneme or add a text-parse fallback.
- **Repro-env: pin Python 3.12.** No `.python-version`, so a fresh `uv sync` resolves to
  the system's newest interpreter (3.14 observed), where `fastmcp>=2,<3` is not installable —
  the suite then fails to collect. The existing `.venv` is 3.12; a new worktree/machine has
  no such luck. Add a `.python-version` (or a lower `requires-python` ceiling / CI matrix) so
  the toolchain is reproducible without an ad-hoc `--python 3.12`. Surfaced 2026-08-11 building
  config-discovery.

## Deferred by the Spec/PRD (future phases)
- Facets: finances/gnucash, env-stack, tjpa work-corpus (grow-by-validated-need).
- Curated cross-facet bridges (J6), agent-mediated actuation (J5), knowledge curation (J3).
- MCP HTTP/remote transport (Phase 1 is stdio-only).
