#!/usr/bin/env python3
"""glossary_altitude — the commit-time altitude check for a domain glossary (throughline; agent-kit #1756).

A glossary write that no review stage reads (a stand-alone edit) used to meet no altitude check at all: the at-source
judgment lives in `review`, and the at-rest pass runs on demand. This tool closes that gap at the commit, whatever
wrote it. It is SELF-CONTAINED and stdlib-only on purpose: a consumer vendors this one file at a pinned tag into
`.ci/` and runs it from a committed pre-commit hook and a CI step (`GLOSSARY_ALTITUDE.md`), the `land_gate.py`
precedent — a vendored file cannot import a sibling. `domain_glossary.py delta` imports `TIER_A` and `new_tokens`
from here, so the review path and the commit path judge the same classes.

Two tiers:
- **tier A — findings, exit 1.** Mechanism that is never ubiquitous language: an env-var name, a ≥6-digit literal, a
  camelCase identifier in backticks, a code-file path in backticks, a route (a backticked `/a/b…` path of ≥2
  segments, or a token carrying a `?key=` query). Measured over 31 labelled stand-alone commits from six consumers:
  12/14 genuine leaks, 0/6 vocabulary; over all 307 glossary commits it fires on 62, all mechanism on a read.
- **tier B — nominations, never blocking.** A snake_case identifier in backticks that does not end in `_id`. The same
  shape names a function in one model and an enum value of the domain in another (4/6 vocabulary commits carry one),
  so only a reader who knows the model can tell; the tool lists them for the writer to judge.

Before matching, both tiers drop: `(carrier: …)` and `(anchor: …)` spans (tokens another throughline obligation
mandates in the same file), the domain-key convention (`word:<id>`, `` word:`…` ``), and a literal introduced as an
example of a format (`ex.` / `e.g.` / `example` / `for example` / `por exemplo`, any case, an optional colon, then a
backticked value with no letter in it — an identifier, route or path after "e.g." is still read). A token already present in the change's
removed lines is not reported: an in-place edit of a line that carried it adds nothing new.

    python3 glossary_altitude.py check (--staged | --base <rev> [--head <rev>]) [--glossary <path>] [--repo <path>]

Exit 1 iff tier A findings; 0 otherwise (including a change that does not touch the glossary); 2 with a JSON
`error` on a usage or revision error AND on any unexpected failure — a crash must never read as a finding.

A glossary renamed or moved in the change is diffed against its old path, so a content-free move reports nothing.
"""
import json
import re
import subprocess
import sys

_CODE_EXT = r"(?:py|ts|tsx|js|jsx|mjs|cjs|sql|go|rs|java|kt|rb|php|cs|sh)"
TIER_A = (
    ("env_var", re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]{2,}\b")),
    ("magic_id", re.compile(r"(?<![\w.])[0-9]{6,}(?!\w|\.\d)")),     # a sentence-final period still ends it
    ("camel_identifier", re.compile(r"`[a-z]+[A-Z][A-Za-z0-9]*(?:\(\))?`")),
    ("code_file", re.compile(rf"`[\w./*-]*\.{_CODE_EXT}`")),
    ("route", re.compile(r"`/[\w*-]+(?:/[\w*<>:-]*)+(?:\?[\w-]+=[^`]*)?`"   # backticked path, ≥2 segments: `/form/x`
                         r"|`/?[\w/-]*\?[\w-]+=[^`]*`"                       # backticked query: `?codigo=`, `/vendas?c=`
                         r"|(?<![\w/])/[\w-]+\?[\w-]+=")),                   # a query in plain prose: /vendas?codigo=
)
TIER_B = (
    ("snake_identifier", re.compile(r"`(?![a-z0-9_]*_id`)[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?:\(\))?`")),
)
_SPAN_OPENERS = ("(carrier:", "(anchor:")
_DOMAIN_KEY = re.compile(r"\b[a-z][a-z_]*:(?:<|`)")
_EXAMPLE = re.compile(r"\b(?:ex\.?|e\.g\.|por exemplo|for example|example)\s*:?\s*`[^`A-Za-z]*\d[^`A-Za-z]*`",
                      re.IGNORECASE)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DEFAULT_GLOSSARY = "docs/domain.md"


def _drop_spans(line):
    """`line` without its `(carrier: …)` / `(anchor: …)` spans, each closed at its matching parenthesis (a span may
    nest parentheses, e.g. a carrier record's per-site note)."""
    for opener in _SPAN_OPENERS:
        start = line.find(opener)
        while start != -1:
            depth, end = 0, len(line)                 # an unclosed span runs to the end of the line
            for i in range(start, len(line)):
                depth += {"(": 1, ")": -1}.get(line[i], 0)
                if depth == 0:
                    end = i + 1
                    break
            line = line[:start] + " " + line[end:]
            start = line.find(opener, start)
    return line


def scrub(text):
    """Remove what neither tier may read: kit-mandated spans, the domain-key convention, example literals."""
    return _EXAMPLE.sub(" ", _DOMAIN_KEY.sub(" ", "\n".join(_drop_spans(ln) for ln in text.split("\n"))))


def tokens(text, tier):
    """{(class, token)} for every match of `tier` in `text`, after `scrub`."""
    clean = scrub(text)
    return {(cls, m.group(0)) for cls, rx in tier for m in rx.finditer(clean)}


def new_tokens(added_lines, removed_text, tier):
    """[(line_index, class, token)] for tokens on `added_lines` that `removed_text` does not already carry."""
    old = {tok for _cls, tok in tokens(removed_text, tier)}
    out, seen = [], set()
    for i, ln in enumerate(added_lines):
        for cls, tok in sorted(tokens(ln, tier)):
            if tok not in old and (cls, tok) not in seen:
                seen.add((cls, tok))
                out.append((i, cls, tok))
    return out


class CheckError(Exception):
    """A usage/revision error the CLI reports as exit 2 + JSON `error`."""


def _git(repo, *args):
    # errors="replace": a glossary line that is not valid UTF-8 must not crash the check (a crash is not a finding)
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, errors="replace")


_PLAIN = ("--no-ext-diff", "--no-textconv", "--no-color")   # a user's diff.external / textconv must not hide lines


def _rename_source(repo, glossary, staged, base, head):
    """The glossary's path before the change when the change renamed or moved it, else None."""
    args = ["diff", "--cached", "-M", "--name-status", *_PLAIN] if staged else \
        ["diff", "-M", "--name-status", *_PLAIN, base] + ([head] if head else [])
    for ln in _git(repo, *args).stdout.splitlines():
        parts = ln.split("\t")
        if parts[0].startswith("R") and len(parts) == 3 and parts[2] == glossary:
            return parts[1]
    return None


def _diff(repo, glossary, staged, base, head):
    if not staged:
        for rev in (base, head):
            if rev is not None and _git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}").returncode:
                raise CheckError(f"unresolvable revision: {rev!r}")
    old = _rename_source(repo, glossary, staged, base, head)
    paths = ["--", old, glossary] if old else ["--", glossary]
    if staged:
        args = ["diff", "--cached", "-U0", "-M", *_PLAIN, *paths]
    else:
        args = ["diff", "-U0", "-M", *_PLAIN, base] + ([head] if head else []) + paths
    out = _git(repo, *args)
    if out.returncode:
        raise CheckError(f"git diff failed: {out.stderr.strip()[:200]}")
    return out.stdout


def _parse_diff(diff):
    """(added: [(new_line_no, text)], removed_text) from a -U0 unified diff of one file."""
    added, removed, line_no = [], [], 0
    for ln in diff.splitlines():
        m = _HUNK.match(ln)
        if m:
            line_no = int(m.group(1))
        elif ln.startswith("+") and not ln.startswith("+++"):
            added.append((line_no, ln[1:]))
            line_no += 1
        elif ln.startswith("-") and not ln.startswith("---"):
            removed.append(ln[1:])
    return added, "\n".join(removed)


def check(repo=".", glossary=DEFAULT_GLOSSARY, staged=False, base=None, head=None):
    """Run both tiers over the glossary's change. Returns {glossary, findings, candidates}; each entry is
    {line, class, token, text}."""
    if staged == (base is not None):
        raise CheckError("give exactly one of --staged or --base <rev>")
    added, removed_text = _parse_diff(_diff(repo, glossary, staged, base, head))
    texts = [t for _n, t in added]
    result = {"glossary": glossary, "findings": [], "candidates": []}
    for key, tier in (("findings", TIER_A), ("candidates", TIER_B)):
        for i, cls, tok in new_tokens(texts, removed_text, tier):
            result[key].append({"line": added[i][0], "class": cls, "token": tok, "text": added[i][1].strip()})
    return result


_FLAGS = {"--staged": False, "--base": True, "--head": True, "--glossary": True, "--repo": True}


def _usage():
    """Machine-readable usage, like every other output of this tool (the domain_glossary #1366 precedent)."""
    return {
        "tool": "glossary_altitude.py",
        "purpose": "commit-time altitude check for a domain glossary: tier A mechanism blocks, tier B snake_case "
                   "identifiers are nominated for the writer's judgment (agent-kit #1756)",
        "commands": {
            "check": "check (--staged | --base <rev> [--head <rev>]) [--glossary <path>] [--repo <path>] — "
                     f"--glossary defaults to {DEFAULT_GLOSSARY}; returns {{glossary, findings, candidates}}, each "
                     "entry {line, class, token, text}; exit 1 iff findings, 0 otherwise, 2 on a usage/revision error",
        },
        "consumer_page": "GLOSSARY_ALTITUDE.md (vendoring, the pre-commit hook, the CI step)",
    }


def _parse(argv):
    flags, i = {}, 0
    while i < len(argv):
        flag = argv[i]
        if flag not in _FLAGS:
            raise CheckError(f"unknown argument: {flag!r}")
        if _FLAGS[flag]:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                raise CheckError(f"{flag} requires a value")
            flags[flag[2:]] = argv[i + 1]
            i += 2
        else:
            flags[flag[2:]] = True
            i += 1
    return flags


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd in ("", "-h", "--help", "help") or "--help" in argv[2:]:
        print(json.dumps(_usage(), indent=2))
        return 0
    try:
        if cmd != "check":
            raise CheckError(f"unknown command: {cmd!r}")
        f = _parse(argv[2:])
        result = check(f.get("repo", "."), f.get("glossary", DEFAULT_GLOSSARY), bool(f.get("staged")),
                       f.get("base"), f.get("head"))
    except CheckError as exc:
        print(json.dumps({"error": str(exc), "usage": _usage()}), file=sys.stderr)
        return 2
    except Exception as exc:          # noqa: BLE001 — any other failure is a tool error (2), never a finding (1)
        print(json.dumps({"error": f"unexpected failure: {type(exc).__name__}: {exc}"}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    if result["findings"]:
        print(f"glossary_altitude: {len(result['findings'])} mechanism token(s) in {result['glossary']} — "
              "state the rule in domain terms; the mechanism belongs in code or ops docs", file=sys.stderr)
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
