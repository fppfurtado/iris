# AGENTS.md — iris

## What iris is

**iris** is a sovereign, read-only **agent-context layer**: a small core that **federates** the context
sources you already trust — a knowledge base, a repository/asset registry, and more — and **serves** a
unified view of them to AI agents through a CLI and an MCP adapter.

Thesis: **federation of sovereign canonicals + bridges by resolved identity** — integral by federation, not
by a totalizing store. iris **owns no data**: it reads each source through that source's own interface and
composes the results. No write path exists anywhere (read-only by construction).

Named for Iris — the messenger goddess and the rainbow that bridges realms: federation-by-bridges and
context delivery in one symbol.

## Language

Project language is **English** by default — code, comments, CLI help, docs, and commit messages.

## Working norm (operational floor)

<!-- floor block vendored below; never edit inside it, extend below the closing marker -->

<!-- agent-kit operational-floor v7 — single source: agent-kit/onboarding/operational-floor.md
     Copy this whole block into your repo's own AGENTS.md / CLAUDE.md, below your own content.
     Extend BELOW the closing marker; never edit INSIDE the block. Re-copy when the version bumps.
     Distillation baseline — last verified faithful against the maintainer's root operational-floor
     section on 2026-07-17. v2 (2026-07-20) adds the `.worktrees/<slug>` worktree-location convention to
     the Session isolation rung, aligning it with the maintainer root floor (#338). v3 (2026-07-24)
     adds apply-`.worktreeinclude` (copy, not symlink) after every worktree create (#431). v4 (2026-07-28)
     adds `git submodule update --init` after worktree create for repos with a `.gitmodules` (#492).
     v5 (2026-08-03) adds the canonical-path-bound-tooling carve-out to the Session isolation rung (branch
     in-place where the tool reads a configured canonical path, e.g. a chezmoi source dir; #606). v6
     (2026-08-05) generalizes the Cycle-close capture sweep from "before landing" to the close of ANY
     session — a landing-free analysis/hygiene pass owes a disposition for each gap it surfaces too (#635).
     v7 (2026-08-10) sharpens the Cycle-close capture sweep from spirit to a checkable step: disposition is
     per-item to a durable surface (an aggregate "all handled" and a chat/close-summary/un-attested-prose
     mention are not durable), so an odd-class follow-up cannot slip through bulk reasoning (#708).
     This generic block intentionally omits the maintainer-internal
     release/attestation rungs (a per-PR method self-check, issue-close-evidence, the PR attestation
     lines, and release-due surfacing for published units) — they depend on maintainer-specific tooling
     a norm-blind repo does not have. Re-verify when that floor section changes; the version bumps only
     when a *copied rung* changes (so an unchanged re-copy is never forced). -->

## Working norm (operational floor)

This repo follows the **throughline** working discipline. The rungs below are the always-on floor: they
bind every session that mutates git — from a one-line fix to a large build — and are **not** scaled down by
effort size (a smaller effort takes fewer steps, never a thinner floor). They run as **self-checks**; where
a deterministic guard is installed (see the last rung) it enforces the same rung, but the behavior binds
with or without it.

- **Session isolation.** Work in a dedicated git worktree — created **under `.worktrees/<slug>` inside the
  repo** (a gitignored directory), on a feature branch — from session start, solo included. The
  main/default worktree stays a neutral base: no session does feature work on it. Never run two
  git-mutating sessions against one working tree. If you start and find the base on another session's
  branch (or dirty with foreign work), spawn your own worktree — do not work there. After
  `git worktree add`, if the repo root has a `.worktreeinclude`, **copy** each listed path from the main
  worktree into the new one (copy, not symlink; halt if a listed path is missing in main) — gitignored
  agent context (`AGENTS.md`, `CLAUDE.md`, …) does not travel with the worktree otherwise. If the repo has
  a `.gitmodules`, also run `git submodule update --init --recursive` in the new worktree — submodules are
  **versioned** (a gitlink to a pinned commit) that `git worktree add` does **not** init, so a build that
  depends on them fails otherwise; **init, don't copy** (they are not `.worktreeinclude` entries).
  **Carve-out — canonical-path-bound tooling:** for a repo whose tooling reads a *configured canonical
  absolute path* rather than the working tree (e.g. a chezmoi source dir), a `.worktrees/<slug>` worktree
  relocates edits where the tool never looks (no isolation, actively misleading) — **branch in-place** in
  the canonical dir instead; PR-per-cycle + the concurrency check still bind (guard the concurrency check —
  a bare pull/checkout on the shared dir can collide).
- **Concurrency check at pickup.** Before working an existing tracker item, check whether a live session
  already owns it (a sibling worktree/branch for it, or a frozen design / open PR on the item). If one
  exists, stand down — do not produce competing artifacts; defer or coordinate.
- **Issue-first.** A significant effort — one worth framing, or expected to outlive a session — opens its
  tracker item BEFORE work begins, so the effort is visible from the start and survives a dead session.
- **Declare the route before solution mechanics.** For each item you pick up, name the route on two axes —
  problem space (frame the problem, vs work from an already-frozen problem brief) and solution space
  (a lightweight build, vs a full design pipeline) — each with a one-line reason, *before* touching the
  solution. A trivial fix names its door too; "worked ad-hoc, through no door" is never a valid route.
- **PR-per-cycle; the agent never merges.** Every cycle lands via a pull/merge request off the feature
  branch — never a direct push to the default branch. The agent stops at a merge-ready PR (checks green,
  review attested) and hands off; the **human performs the merge** (the terminal, least-reversible step).
- **Review before land (the land-gate).** Built code lands on the default branch only after the judgment
  review pass ran — attested — or a reasoned waiver is on record. The bar is *ran-or-waived*, not
  findings-resolved: acting on findings stays human judgment; the gate only ensures review was not silently
  skipped.
- **Cycle-close capture sweep.** At the close of ANY session — a landing cycle OR a landing-free
  analysis/review/hygiene pass that lands nothing — sweep for surfaced follow-ups, drifts, and gaps and
  dispose each **per item, to a durable surface**: enumerate each surfaced follow-up (an odd-class one — a
  one-off "run `X`" mechanical step — counts too) and name where it durably lands (a filed tracker item, or a
  recorded reason it needs none), never swallowed — whether or not the session lands. An **aggregate** "all
  handled" and a mention in **chat, an ephemeral close summary, or un-attested prose** are NOT durable
  dispositions: reasoning over the class lets an odd-class item slip and land nowhere. A landing cycle records
  each where the change lands; a landing-free pass records each in the pass's own output.
- **Verify before any destructive action.** Before `rm` / overwrite / `clean`, verify the target against
  the real tree (tracked-files / status / an explicit path check) — never a bare directory listing, which
  goes stale across branch churn. Before `git stash pop`/`apply`/`drop`, check `git stash list` and target
  an explicit `stash@{n}` (the stash stack is shared across all worktrees, so a bare pop may apply an alien
  stash onto the wrong tree). Prefer read-only inspection when you only need to look.

**The methodology.** The full working cycle is **throughline** — one guided front door (**frame** the
problem) → solution design → **build** → **review** — available as installed agent skills. Bring a problem
to `frame`; it routes the rest. Diagnosis has its own depth branch (`debug`). Do not reach for a solution
before the problem is framed.

**Deterministic enforcement (optional; the floor degrades gracefully).** The rungs above are self-checks and
bind everywhere. Where you want a *hard* floor, add the deterministic layers separately: a pre-commit guard
that refuses commits on the default branch, a pre-push / CI land-gate that blocks unreviewed
throughline-built code (use the land-gate CI recipe your throughline install ships), and your forge's branch
protection. These are per-harness / per-platform add-ons, not a dependency of the norm — where they are
absent, the self-checks still bind.

<!-- /agent-kit operational-floor v7 -->

<!-- agent-kit session-boundary ritual v9 — single source: agent-kit/onboarding/session-boundary-ritual.md
     OPERATOR-PERSONAL extension (it names my own ecosystem tools — mneme, meta-bridge, backlog, and the
     agent-kit substrate itself — and is agent-kit-local, never published to strangers). Copy this whole
     block into your repo's own AGENTS.md / CLAUDE.md, BELOW the operational-floor block's closing marker
     (this is the "extend below the marker" seam — it is deliberately NOT part of the minimal shared floor).
     Extend BELOW this block's own closing marker; never edit INSIDE the block. Re-copy when the version
     bumps. -->

## Session-boundary ritual (open + close)

At the START and the END of a work session, run the ritual below. It is **assisted, not automatic**:
surface the checklist and act only on my confirmation — never self-execute a step silently, and respect
each step's preconditions (e.g. the journal target being logged in). **Graceful skip:** a step whose
target surface is absent on this repo/machine is skipped, not failed — the ritual degrades to whatever
surfaces are present. The trigger is **presence + this block being read natively** at the session
boundary: any "opening"/"wrapping up" cue fires it, no special phrase required.

**On session OPEN — ground the state:**
- **Ground the sovereign KB** (the mneme *instance* at `~/mneme` — the KB data, reached by the `mneme`
  CLI): `mneme index rebuild >/dev/null && mneme ground --query "<session theme>"` — pull the relevant
  prior context before orienting.
- **Reconcile the PKM bridge** where used (meta-bridge `reconcile`): verify-state + dedup cross-store
  before work begins.
- **Name the executing model-tier** (`opus | sonnet`) as a session covariate — NOT a gate (throughline is
  model-agnostic and cannot enforce tier). Recording which tier drives the session lets a finding filed at
  close carry an honest `tier:` marker (the close-side agent-kit feedback-path rung below), keeping tier an
  auditable covariate rather than an invisible one (agent-kit #357).
- **Surface the open GTD next-actions** (the agent-consumed next-action axis — a *sibling* read to
  `ground`, NOT folded into it): `mneme task list --status open --instance ~/mneme` — surface the open
  next-actions the agent tracks in the sovereign `~/mneme/knowledge/gtd.md`. No aggregator consumes this
  axis, so cross-cutting (often repo-less) next-actions stay invisible unless read HERE. Distinct from
  `ground` (learnings) and initiative-state below — the three axes stay separate. **Agent-consumed class
  only** (per the mneme J7 verdict, 2026-08-04 — operator-executed real-world tasks are a different axis).
- **Surface coordination-program state** where a program seed is present: resolve
  `working-state/programs/<program>/coordination.SEED.md` — `working-state` is a git repo **sibling of this
  repo**, NOT a `$HOME` subdir (derive it from the repo root, climbing out of an in-repo `.worktrees/<slug>`
  first, and verify it resolves before use). Surface its roll-up + next-actionable, honoring the seed's two
  axes — **trust** (operator-ratified vs agent-derived) and **execution** (executed / rider-open /
  cutover-pending). Take each initiative's **disposition + progress from the newest mneme journal block
  naming it** (newest-wins — the seed's hand-authored roll-up goes stale), reading the seed only for its
  edges + next-actionable. **Read-only** (it surfaces state; it is never the execution mechanism).
  **Graceful skip** when the sibling `working-state` doesn't resolve.

**On session CLOSE — deposit the why:**
- **Sweep loose ends** (`backlog:session-close`, or this repo's session-close equivalent): file surfaced
  follow-ups / record decisions — leave no loose end.
- **Capture agent-consumed next-actions into GTD** (the write-twin of the OPEN GTD read). For repo-less
  next-actions that emerged from THIS session's agentic work AND that the **agent** acts on in sessions
  (the agent-consumed class): append `- [ ] <task>` under the existing structure in
  `~/mneme/knowledge/gtd.md`, then `mneme block stamp knowledge/gtd.md --instance ~/mneme` to assign `^id`s.
  **Angle-bracket hygiene:** never a raw `<tag>` in the drafted line — an unclosed `<…>` opens an HTML block
  that swallows every FOLLOWING checkbox; use `{braces}`, backticks, or prose.
  **Class discriminator** (this rung is the agent-consumed class only): repo-less + agent-acts-in-session →
  `gtd.md`; repo-less + operator-acts-in-the-world (reminders, life-admin) → the class-2 residence, NOT
  `gtd.md` (gated on a manual-ergonomic UI, mneme#158). Do **not** absorb cross-repo work that already routes
  to a forge tracker (issues/labels/trailers). Ledger-relevant ops keep `--actor agent`; `block stamp` is
  mechanical (no `--actor`). **Archive-done:** if `gtd.md` carries ≥1 `- [x]` line, move those blocks to
  `knowledge/gtd-arquivadas.md` preserving the `^id`.
- **Check the agent-kit feedback path** — ONLY when THIS repo consumes agent-kit/throughline (skip
  otherwise). For each gap/drift the session surfaced HERE, ask whether its cause roots — partly or wholly —
  in the shared **agent-kit substrate** (a skill / posture / doctrine gap), not merely in this repo's local
  code. Attribute it honestly, collapsing *"is this agent-kit's fault?"* into *"would a checkable GATE (not
  spirit) have caught it at the weakest supported tier?"* — and **guard over-attribution** (the
  confirmation-bias hole: *asked → it agrees* is not evidence):
  - **substrate** — a skill/posture/doctrine gap → agent-kit's; **file upstream**.
  - **spirit-not-gate** — a correct norm with no checkable gate surviving the weakest tier's momentum →
    agent-kit's; **file upstream**.
  - **model** — a weak-tier execution miss no gate could catch at the weakest supported tier → NOT the
    substrate; it stays local (the execution-tier-policy residual, agent-kit #357).

  When it IS substrate / spirit-not-gate, file it into agent-kit's OWN tracker WITH its provenance, so the
  receiving-side audit (`build/audit_cross_repo_origin.py`, agent-kit #355) sees it from the tracker alone —
  this stamps the RECEIVING-side marker (agent-kit defines the schema; the filing act stamps it); the finding
  becomes an agent-kit-local item carrying its origin, NOT a cross-repo portfolio:

  ```sh
  gh label create "src:<this-repo>" -R fppfurtado/agent-kit 2>/dev/null || true   # once per new source repo
  gh issue create -R fppfurtado/agent-kit \
    --title "<terse finding>" \
    --body  "<context + Origin block: source-repo / executing model-tier / attribution>" \
    --label "origin:cross-repo,src:<this-repo>,tier:<opus|sonnet>,attr:<substrate|spirit-not-gate|model>"
  ```
- **Refine the operator profile from this session's evidence** (agent-mediated, surface-first). If this
  session surfaced real evidence about how the operator works, thinks, or decides — a preference stated, a
  pattern *contradicted*, a pattern's evidence base strengthened by a genuinely new independent datum (not a
  restatement), a new working/interaction/operating tendency — PROPOSE a refinement to the sovereign profile
  artifact on the approve→act seam: draft the specific edit (an `Observed:`-backed, dated line — or the
  retirement of a contradicted pattern), surface it, and apply ONLY on the operator's approval — never
  self-edit the profile silently. The act is **resolve → land → materialize-and-verify**, because this step
  *writes to one layer and is read from another* — writing the edit somewhere is not finishing:
  1. **Resolve the SOURCE, not the read surface.** **Probe, don't restate the path** (the drift class that
     stranded this step once, agent-kit #593): the global `~/.claude/CLAUDE.md`'s own operator-profile
     section is the single source of truth for where the artifact lives — resolve the path THERE at use
     time, never a value hardcoded in this block. Then test whether that path is a **generated** surface (a
     template / `do not edit` header, or the renderer's own query — e.g. `chezmoi source-path <file>`); if
     so the edit target is the **source**, and the resolved path is only the read surface a later render
     must reach.
  2. **Edit + land the source under the operational floor.** If the source lives in a git repo the floor
     binds — including the **canonical-path-bound carve-out** (operational-floor v5 / agent-kit #606) when
     the renderer reads a configured absolute source dir: branch-in-place + PR *there*, never a
     `.worktrees/<slug>` the renderer never looks at (the render would be a silent no-op while branch + PR +
     merge all appear to succeed). Persist to the **committed** source — never a bare edit-the-live-file +
     render that strands the refinement uncommitted (lost on a fresh renderer init).
  3. **Materialize, targeted — then VERIFY at the read path.** Render only the **affected paths** (a bare
     whole-tree render also executes pending `run_` scripts — unrelated system side effects), then confirm
     the new text actually reached **the read surface the next session consumes** — the *same* surface
     resolved in sub-step 1, never a path re-hardcoded here (that would re-open the #593 drift the resolve
     step exists to close): the always-on `~/.claude/CLAUDE.md` section for a lean-region refinement, or the
     fuller artifact's own resolved path for one that lands only there —
     `grep -q "<distinctive phrase from the new line>" "<read surface resolved in sub-step 1>" || echo "refinement did NOT reach the read path"`.
     This one cheap check is the gate — it catches BOTH silent failures (edited the generated surface → next
     render overwrites it; edited the source but never rendered → invisible to every session). **On a failed
     grep the render did not land — the refinement is NOT applied:** re-resolve the source (sub-step 1) and
     re-render; if a re-render still doesn't reach the read path, surface the failure to the operator rather
     than closing the step. **Renderer-agnostic:** where the profile is a plain file (write == read, no
     render) sub-steps 1/3 collapse to the edit itself — no problem to solve.

  Discipline: propose from **evidence this session actually produced**, never to re-derive mature content
  (usability/evolution, not a content rework) and never merely to *restate* an existing line — a bare
  re-confirmation adds no evidence and risks self-confirming bias (its own epistemic-status warning), so only
  a genuinely new datum warrants a proposed edit; a genuine contradiction UPDATES or RETIRES the pattern
  rather than explaining the behavior away. Most sessions surface nothing to propose → skip.
  **Graceful skip:** if the global CLAUDE.md names no such artifact, or the artifact it names is absent, skip.
- **Enumerate durable artifacts born this session — outcome-independent** (agent-kit #719). BEFORE the
  mneme registration below, list the durable artifacts this session **created or discovered** — files,
  credentials, hosts, service endpoints, configs — **regardless of whether the session's nominal result was
  substantive or null.** A null/inconclusive finding suppresses the perceived salience of any *incidental*
  artifact left behind (the null becomes the frame of the whole session, and the collateral artifact is
  never nominated) — the exact #719 miss: a credentials file (`~/.pgpass`, 5 hosts) born during a
  null-result triage stayed invisible to `mneme ground` for 6 days. Ask this **separately** from *"did the
  session have a substantive finding?"* — one question must not absorb the other. Each durable artifact is a
  **candidate on two distinct axes** (surface as a candidate, never mint — respect the spine's curation gate):
  - **findability** → propose it as an entity in the `entity propose` step below, so a later `ground`
    retrieves it (the axis #719 names);
  - **reproducibility** → a **secret / config / unit born outside the managed declarative tree** ALSO owes
    the env-stack **birth-capture** (surface it for a chezmoi / Bitwarden / mise disposition — that reflex
    is env-stack-specific and lives in the operator's global doctrine, not vendored here). The axes do not
    substitute: a chezmoi-captured secret is *reproducible* yet still not *findable* via `ground`, and an
    entity-proposed fact is *findable* yet not *reproducible* on a machine rebuild. **Graceful degrade** to
    the findability axis alone where no env-stack reflex is present.
- **Register the session in the mneme _instance_** (`~/mneme`, via the `mneme` CLI — this deposits KB
  *data*; it is NOT the mneme *system* repo, whose tooling issues live in its own tracker — keep the two
  distinct):
  - `mneme journal add` — deposit the session's journal block(s) (body via stdin). The close can
    happen in **two moments**: a deliberate 2nd deposit of the SAME session takes `--complement`
    (appends a sibling block); without the flag, re-invoking with the same session-id is a silent
    no-op — the 2nd body is discarded (mneme#41).
  - `mneme entity propose` — **propose the session's entities, CONCEPTS INCLUDED** (not only proper
    names). This step is decoupled from `journal add` and is silently skipped when not named, so name it
    at every close.
  - `mneme index rebuild` — refresh the read-side index.
- **Synthesize the human journal** where Logseq is present (meta-bridge `journal-close`): a
  human-friendly session synthesis in the Logseq journal.

<!-- /agent-kit session-boundary ritual v9 -->
