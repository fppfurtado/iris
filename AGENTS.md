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

<!-- agent-kit operational-floor v13 — single source: agent-kit/onboarding/operational-floor.md
     Copy this whole block into your repo's own AGENTS.md / CLAUDE.md, below your own content.
     Extend BELOW the closing marker; never edit INSIDE the block. Re-copy when the version bumps.
     This block is a SHIPPED ASSET: it stays English-as-shipped regardless of your repo's `## Language`
     `project` setting — re-copy verbatim, never translate it (localizing a shipped asset is separate
     product-i18n, not authored content). Your own below-marker sections follow your `project` normally.
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
     mention are not durable), so an odd-class follow-up cannot slip through bulk reasoning (#708). v8
     (2026-08-16) adds the governing-Spec scan sub-step to the Declare-the-route rung: before a skip-Spec
     lightweight route commits, scan for an existing frozen Spec governing the touched files (#781). v9
     (2026-08-16) gives the Cycle-close capture sweep its during-flow FEED — the session findings ledger,
     appended at detection so process-class findings survive to close (#863) — and aligns the spec-file
     pattern list to the tools' full set (adds `spec_*.md`). v10 (2026-08-17) extends the
     Verify-before-destructive rung with the repo-archive case — verify `HEAD == @{u}` + a clean tree
     before archiving a repo that serves as a delete-backstop (#852; evidence mneme#194). v11
     (2026-08-17) adds the teardown half to the Session isolation rung: sweep gitignored working state
     out of a session worktree BEFORE removal — a bare `git worktree remove` silently deletes it (#840;
     evidence #798, n=3). v12 (2026-08-18) adds the Stage-by-explicit-paths rung: stage changed paths by
     name, never a broad `git add -A`/`add .`, so a stale worktree copy cannot silently revert a sibling
     session's landed work (#888). v13 (2026-09-01) adds the liveness half to the Concurrency-check rung: a
     foreign `.worktrees/<slug>` is presumed live until a positive death signal, and a positive liveness
     probe (`lsof +D` / `/proc/*/cwd`) precedes any destructive action on it — landing-absence (unpushed/no
     PR) is in-progress work, not death (#1210).
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

- **Session isolation.** <!-- rung:session-isolation --> Work in a dedicated git worktree — created **under `.worktrees/<slug>` inside the
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
  **Teardown is sweep-then-remove:** before removing a session worktree, sweep its gitignored working
  state OUT to the main tree — `git worktree remove` refuses on tracked modifications but **silently
  deletes gitignored files** (the in-worktree `.throughline/dossiers/`, plus any path a tracked
  `.worktreesweep` manifest at the repo root lists). A throughline install ships the sweep
  (`python3 sub-tools/worktree_sweep.py --repo <main-root> --worktree <worktree-path>`); without it,
  copy those paths out by hand before `git worktree remove`.
  **Carve-out — canonical-path-bound tooling:** for a repo whose tooling reads a *configured canonical
  absolute path* rather than the working tree (e.g. a chezmoi source dir), a `.worktrees/<slug>` worktree
  relocates edits where the tool never looks (no isolation, actively misleading) — **branch in-place** in
  the canonical dir instead; PR-per-cycle + the concurrency check still bind (guard the concurrency check —
  a bare pull/checkout on the shared dir can collide).
- **Stage by explicit paths.** <!-- rung:stage-by-explicit-paths --> Stage what you changed by naming the paths (`git add <path> …`) — never a
  broad `git add -A` / `git add .`. A broad add re-stages whatever the worktree's index happens to hold, so
  in a parallel-session repo a stale copy of a file a *sibling* session already landed gets silently
  re-committed at its old contents — reverting that sibling's work, with no merge conflict to warn you.
  Review `git status` / `git diff --cached` before committing; stage additions and deletions explicitly.
- **Concurrency check at pickup.** <!-- rung:concurrency-check-at-pickup --> Before working an existing tracker item, check whether a live session
  already owns it (a sibling worktree/branch for it, or a frozen design / open PR on the item). If one
  exists, stand down — do not produce competing artifacts; defer or coordinate. A foreign `.worktrees/<slug>`
  is **presumed live until a positive death signal** (operator confirmation · the branch already
  merged/closed · an explicit end marker) — landing-absence (unpushed · no PR · no comment) is in-progress
  work, not death. Before any destructive action on it (worktree remove · teardown-sweep · rebase-onto), run
  a positive liveness probe (`lsof +D <worktree>`, or scan `/proc/*/cwd` for a process cwd'd inside — a
  parallel session's command line carries no slug, so a slug grep of `ps` misses it) and read git mtimes
  against the real wall clock, rather than reading landing-absence as death.
- **Issue-first.** <!-- rung:issue-first --> A significant effort — one worth framing, or expected to outlive a session — opens its
  tracker item BEFORE work begins, so the effort is visible from the start and survives a dead session.
- **Declare the route before solution mechanics.** <!-- rung:declare-the-route-before-solution-mechanics --> For each item you pick up, name the route on two axes —
  problem space (frame the problem, vs work from an already-frozen problem brief) and solution space
  (a lightweight build, vs a full design pipeline) — each with a one-line reason, *before* touching the
  solution. A trivial fix names its door too; "worked ad-hoc, through no door" is never a valid route.
  Before committing a "lightweight build, skip Spec" route, check whether an existing frozen Spec already
  governs the code the change touches — a throughline install ships the deterministic scan
  (`spec_surface.py match --repo . --paths <touched files>`); without it, scan the repo's spec files
  (`spec-*.md` / `spec_*.md` / `*.spec.md`) by hand. One found → the route defaults to *amend that Spec*, not skip it.
- **PR-per-cycle; the agent never merges.** <!-- rung:pr-per-cycle-the-agent-never-merges --> Every cycle lands via a pull/merge request off the feature
  branch — never a direct push to the default branch. The agent stops at a merge-ready PR (checks green,
  review attested) and hands off; the **human performs the merge** (the terminal, least-reversible step).
- **Review before land (the land-gate).** <!-- rung:review-before-land-the-land-gate --> Built code lands on the default branch only after the judgment
  review pass ran — attested — or a reasoned waiver is on record. The bar is *ran-or-waived*, not
  findings-resolved: acting on findings stays human judgment; the gate only ensures review was not silently
  skipped.
- **Cycle-close capture sweep.** <!-- rung:cycle-close-capture-sweep --> An error, gap, drift, or optimization candidate detected MID-flow
  appends ONE line, at detection, to the session findings ledger — `.throughline/dossiers/session-findings-<slug>.md`
  in the working worktree (a worktree-less or in-place session → the same path at the repo root):
  create the directory if absent and keep it gitignored (a
  `.throughline/.gitignore` carrying `/dossiers/`); it is a CONVENTION, not a tool dependency — with no
  throughline install, any gitignored session-notes file serves the same role. A line is owed when the
  finding is not already tracked, outlives the session or names a class, and was not fixed in-flow with
  zero class-residue — so the close sweep reads a FILE, never working memory. Before removing the
  session worktree, sweep the ledger's lines to their dispositions (or copy the file out) — a bare
  worktree removal deletes it. At the close of ANY session — a landing cycle OR a
  landing-free analysis/review/hygiene pass that lands nothing — sweep the ledger PLUS any follow-ups, drifts, and gaps recalled at close (the ledger augments the
  sweep's feed, it never bars a late entry) and
  dispose each **per item, to a durable surface**: enumerate each surfaced follow-up (an odd-class one — a
  one-off "run `X`" mechanical step — counts too) and name where it durably lands (a filed tracker item, or a
  recorded reason it needs none), never swallowed — whether or not the session lands. An **aggregate** "all
  handled" and a mention in **chat, an ephemeral close summary, or un-attested prose** are NOT durable
  dispositions: reasoning over the class lets an odd-class item slip and land nowhere. A landing cycle records
  each where the change lands; a landing-free pass records each in the pass's own output.
- **Verify before any destructive action.** <!-- rung:verify-before-any-destructive-action --> Before `rm` / overwrite / `clean`, verify the target against
  the real tree (tracked-files / status / an explicit path check) — never a bare directory listing, which
  goes stale across branch churn. Before `git stash pop`/`apply`/`drop`, check `git stash list` and target
  an explicit `stash@{n}` (the stash stack is shared across all worktrees, so a bare pop may apply an alien
  stash onto the wrong tree); prefer read-only inspection when you only need to look. Same class —
  archiving a repo that serves as a delete-backstop (`gh repo archive` / forge Settings → Archive):
  archiving freezes the remote history read-only — verify `HEAD == @{u}` and a clean tree (nothing
  load-bearing untracked or uncommitted) BEFORE archiving, else the backstop freezes incomplete history
  and "delete-because-backed-up" stops being true.

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

<!-- /agent-kit operational-floor v13 -->

<!-- agent-kit session-boundary ritual v13 — single source: agent-kit/onboarding/session-boundary-ritual.md
     OPERATOR-PERSONAL extension (it names my own ecosystem tools — mneme, backlog, and the
     agent-kit substrate itself — and is agent-kit-local, never published to strangers). Copy this whole
     block into your repo's own AGENTS.md / CLAUDE.md, BELOW the operational-floor block's closing marker
     (this is the "extend below the marker" seam — it is deliberately NOT part of the minimal shared floor).
     Extend BELOW this block's own closing marker; never edit INSIDE the block. Re-copy when the version
     bumps.

     v13 (agent-kit #856 — mneme#194 Logseq-triad cutover): dropped the retired `meta-bridge` from the
     named ecosystem tools above; it is no longer a live surface. No operative change — the stub body
     enumerates no ritual axes (it points to the manifest); the correction is to this provenance header only.

     v12 (Spec session-ritual-delivery v2 — the #770 instance-1 reprocess of #771/#768): this block is now
     a STUB, not the enumeration. The authoritative, machine-readable enumeration of every ritual axis —
     both bounded contexts, with per-axis presence conditions, actions, write-twins, guidance depth, and
     the close checkpoint's deterministic signals — is the RITUAL MANIFEST:
       deployed:  ~/.claude/hooks/ritual-manifest.md   (read this one at runtime)
       canonical: agent-kit/onboarding/ritual-manifest.md
     Do NOT restate axes here or anywhere else — one home per context, by construction. -->

## Session-boundary ritual (open + close)

At the START and the END of a work session, execute the session-boundary ritual from its
**manifest** — `~/.claude/hooks/ritual-manifest.md` (fallback when a machine has no deploy: the
canonical `agent-kit/onboarding/ritual-manifest.md`). The ritual is **assisted, not automatic**:
entries surface and enumerate; judgment stays in the loop (`awaiting-confirmation` is a valid
disposition). **Graceful skip** is per-entry, via each entry's `presence:` condition — an absent
surface is an explicit `no-op`, never an error and never a silent omission.

- **OPEN:** the `phase: open` entries normally arrive ALREADY INJECTED in context by the
  `ritual_open_surface.py` SessionStart hook (mechanical delivery — session-start momentum cannot
  skip it). Execute the injected checklist before any front-door skill or first work act, reporting
  each entry inline. If no checklist was injected (hook unwired / manifest absent on this machine),
  read the manifest's open entries directly and do the same.
- **CLOSE:** on the operator's wrap-up cue, compose BOTH contexts from the manifest:
  1. the `repo-close` entries — the loose-end sweep entrypoint (`backlog:session-close` or this
     repo's equivalent) plus the pointer entries the repo's own floor/CI already enforce;
  2. the `operator-boundary` `phase: close` entries — executed per their manifest guidance.
  Emit ONE disposition line per axis (both contexts) in a fenced `ritual-close-dispositions` block:
  `<axis-id>: ran|skipped-with-reason|no-op|awaiting-confirmation [— reason]`. An omitted axis is a
  violation; an aggregate "all clear" is non-conforming.
- **Backstop:** the deterministic close checkpoint (SessionEnd → next SessionStart) reads the SAME
  manifest's embedded signals — a missed write-back axis surfaces at the next open; dispose it then.

<!-- /agent-kit session-boundary ritual v13 -->
