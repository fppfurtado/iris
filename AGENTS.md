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
