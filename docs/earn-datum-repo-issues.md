# Earn datum — `repo ⋈ open-issues` (iris#31, Brief S3)

The `costura-iris-fonte` Brief frames the publish/hold gate `^dogfd1` as **earn-or-retire**: iris earns
its place when a **second federated source** makes the composition beat the direct calls (the
single-source re-expose surface then becomes permanent and S6 finally validates). Candidate F4 — the
strongest earn-path — is `repo ⋈ open-issues`: constellation knows the repo, a `gh`/`glab` tracker knows
its issues, and **no single source does the join**.

This document records the **datum**, not the verdict. The publish/hold call is the operator's (Brief N2).

## The comparison

**The manual sequence a session runs today (N direct calls):**

```sh
iris repos                       # or: mr list          → the repo set (1 call)
gh issue list --repo <r1> ...    # per repo             → open issues of r1
gh issue list --repo <r2> ...    # per repo             → open issues of r2
# … one forge call per repo, then join issues to repos BY HAND
```

**The single composed iris call (1 call):**

```sh
iris context "<task>"            # repos ⋈ their open issues, already joined
```

With a `tracker` source declared (see `sources.example.toml`), `iris context` returns each repo followed
by its open issues in one pass — the join iris now owns (seam rule C6/R1). The manual `1 + N` calls plus a
hand-join collapse to **one** call.

## The equivalence is proven, deterministically

`tests/test_earn_datum.py` proves the buildable half of S3: over a fixture, the single composed call
(`compose_repo_issues ∘ federate`) returns **exactly** the union the manual `repos + per-repo issues`
sequence returns, hand-joined by identity. Composition equals the manual join — so the one call loses
nothing the N calls would surface.

## What is still the operator's call (not decided here)

- **Does 1 call beating N calls clear the publish/hold bar?** That is the `^dogfd1` earn-or-retire verdict
  (Brief N2) — this datum feeds it; it does not settle it.
- **Identity beyond the shared basename (Brief F6).** The join keys on the basename both sources derive
  from the same repo registry. An identity-miss (a tracker issue whose repo has no registry node) is
  surfaced under `## unmatched issues`, not swallowed — the signal that would escalate F6 to a declared
  cross-store identity protocol.
