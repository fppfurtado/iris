#!/usr/bin/env python3
"""glossary_altitude — the commit-time altitude check for a domain glossary (throughline; agent-kit #1756).

A glossary write that no review stage reads (a stand-alone edit) used to meet no altitude check at all: the at-source
judgment lives in `review`, and the at-rest pass runs on demand. This tool closes that gap at the commit, whatever
wrote it. It is SELF-CONTAINED and stdlib-only on purpose: a consumer vendors this one file at a pinned tag into
`.ci/` and runs it from a committed pre-commit hook and a CI step (`GLOSSARY_ALTITUDE.md`), the `land_gate.py`
precedent — a vendored file cannot import a sibling. `domain_glossary.py` imports from here — `delta` takes `TIER_A`
and `new_tokens`, the at-rest `altitude-seed` `TIER_A`, `tokens` and `spans` — so review, the at-rest audit and the
commit judge the same classes (#1756, #2567).

Two tiers:
- **tier A — findings, exit 1.** Mechanism that is never ubiquitous language: an env-var name, a ≥6-digit literal, a
  camelCase identifier in backticks, a code-file path in backticks, a route (a backticked `/a/b…` path of ≥2
  segments, or a token carrying a `?key=` query). Measured over 31 labelled stand-alone commits from six consumers:
  12/14 genuine leaks, 0/6 vocabulary; over all 307 glossary commits it fires on 62, all mechanism on a read.
- **tier B — nominations, never blocking.** A snake_case identifier in backticks that does not end in `_id`. The same
  shape names a function in one model and an enum value of the domain in another (4/6 vocabulary commits carry one),
  so only a reader who knows the model can tell; the tool lists them for the writer to judge.

Before matching, both tiers drop: `(carrier: …)`, `(anchor: …)` and `(world: …)` spans (tokens another throughline obligation
mandates in the same file), the domain-key convention (`word:<id>`, `` word:`…` ``), and a literal introduced as an
example of a format (`ex.` / `e.g.` / `example` / `for example` / `por exemplo`, any case, an optional colon, then a
backticked value with no letter in it — an identifier, route or path after "e.g." is still read). A token already present in the change's
removed lines is not reported: an in-place edit of a line that carried it adds nothing new.

    python3 glossary_altitude.py check (--staged | --base <rev> [--head <rev>]) [--glossary <path>] [--repo <path>]

Exit 1 iff tier A findings; 0 otherwise (including a change that does not touch the glossary); 2 with a JSON
`error` on a usage or revision error AND on any unexpected failure — a crash must never read as a finding. The
exit-2 errors name what failed (agent-kit #3149 SP-TE9): a `--repo` that is not the root of a git work tree, a
`--base`/`--head` that names no commit, a `--glossary` on neither side of the change (the index or HEAD for
`--staged`; base, or head — the working tree without `--head`), a `--glossary` that is a symlink on a side (git
diffs a link as its target's name; pass the file it points to) or behind a symlinked directory, and git failing. With `--staged` or `--head` the
glossary is read from git objects, so the working-tree file's bytes cannot change the answer; without `--head` the
working-tree file IS the head side.

A glossary renamed or moved in the change is diffed against its old path, so a content-free move reports nothing.
"""
import argparse
import json
import os
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
_SPAN_OPENERS = ("(carrier:", "(anchor:", "(world:")
_DOMAIN_KEY = re.compile(r"\b[a-z][a-z_]*:(?:<|`)")
_EXAMPLE = re.compile(r"\b(?:ex\.?|e\.g\.|por exemplo|for example|example)\s*:?\s*`[^`A-Za-z]*\d[^`A-Za-z]*`",
                      re.IGNORECASE)
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DEFAULT_GLOSSARY = "docs/domain.md"


def spans(line, opener):
    """[(start, end)] of every `opener` span in `line`, each closed at its matching parenthesis (a span may nest
    parentheses, e.g. a carrier record's per-site note). `domain_glossary.altitude_seed` lists carrier records
    with it, so the at-rest seed and this check bound a span the same way."""
    out, start = [], line.find(opener)
    while start != -1:
        depth, end = 0, len(line)                     # an unclosed span runs to the end of the line
        for i in range(start, len(line)):
            depth += {"(": 1, ")": -1}.get(line[i], 0)
            if depth == 0:
                end = i + 1
                break
        out.append((start, end))
        start = line.find(opener, end)
    return out


def _drop_spans(line):
    """`line` without its `(carrier: …)` / `(anchor: …)` / `(world: …)` spans."""
    for opener in _SPAN_OPENERS:
        for start, end in reversed(spans(line, opener)):
            line = line[:start] + " " + line[end:]
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


# ---- git_run: copy of spec_surface.git_run (this file is vendored alone; tests pin the copy)
# A git child must read the repo it names with -C, not one the parent inherited: inside a git hook GIT_DIR
# and GIT_WORK_TREE point at the hook's own repo. GIT_INDEX_FILE is kept on purpose: a pre-commit hook points
# it at the index being committed, which is the staged set a hook-run tool must read.
_GIT_SCRUBBED_ENV = ("GIT_DIR", "GIT_WORK_TREE")


def git_run(repo, *args, timeout=None, text=True, encoding=None, errors=None):
    """`git -C <repo> <args>` -> CompletedProcess (stdout/stderr captured; never raises on a non-zero exit).
    `text=False` returns bytes (a blob read); `encoding`/`errors` pass through for text callers."""
    # LC_ALL=C: a caller tells "not a git repository" from a failure by git's message (`git_read`), and the
    # operator's locale would translate it (agent-kit #3337, the tracker's instance of the same read).
    env = {**{k: v for k, v in os.environ.items() if k not in _GIT_SCRUBBED_ENV}, "LC_ALL": "C"}
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text, encoding=encoding,
                          errors=errors, timeout=timeout, env=env)


def _git_proc(repo, *args):
    # errors="replace": a glossary line that is not valid UTF-8 must not crash the check (a crash is not a finding)
    return git_run(repo, *args, errors="replace")


def _git_ok(repo, *args):
    """stdout of a git read whose answer the check needs; CheckError naming git when it fails (SP-TE9: a failing
    read used to answer "no rename", or "unresolvable revision")."""
    p = _git_proc(repo, *args)
    if p.returncode:
        raise _git_failed(p, args)
    return p.stdout


def _git_failed(p, args):
    err = (p.stderr or "").strip()
    return CheckError("git %s failed (exit %d): %s" % (" ".join(args), p.returncode,
                                                       err.splitlines()[0] if err else "no message"))


def _require_root(repo):
    """CheckError unless `repo` is the root of a git work tree. A directory inside one passes `git -C` (git walks
    up), and the glossary path then resolves under the subdirectory, where it is not."""
    if not os.path.isdir(repo):
        raise CheckError(f"--repo {repo!r} is not a directory")
    p = _git_proc(repo, "rev-parse", "--show-toplevel")
    if p.returncode == 128 and "not a git repository" in (p.stderr or ""):
        raise CheckError(f"--repo {repo!r} is not a git repository")
    top = _git_ok(repo, "rev-parse", "--show-toplevel").strip()
    if os.path.realpath(top) != os.path.realpath(repo):
        raise CheckError(f"--repo {repo!r} is not the root of its git work tree ({top})")


def _is_commit(repo, rev):
    """Whether `rev` names a commit. `--verify --quiet` exits 1 for "no such revision"; any other non-zero is git
    failing, and a failing git read as an unresolvable revision before (SP-TE9)."""
    args = ("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    p = _git_proc(repo, *args)
    if p.returncode in (0, 1):
        return p.returncode == 0
    raise _git_failed(p, args)


_LINK_MODE = "120000"   # git's mode for a symlink entry


def repo_relpath(repo, path):
    """`path` relative to the repo root, as text, or None when it is not under the root. The root is the deepest
    ancestor of `path` that IS the repo (same realpath), so a --repo or a --glossary spelled through a link to the
    repo is held either way (review R3, delta read 3 F3); below that ancestor nothing is resolved: a link there is
    the caller's to refuse (`linked_dir`). `domain_glossary` uses this one rule too."""
    top = os.path.realpath(repo)
    p = os.path.abspath(path)
    a = os.path.dirname(p)
    while True:
        if os.path.realpath(a) == top:
            return os.path.relpath(p, a)
        parent = os.path.dirname(a)
        if parent == a:
            return None
        a = parent


def linked_dir(repo, rel):
    """The first directory of `rel` that is a symlink in the working tree, else None. A working-tree read through it
    reads a file git does not hold at that path, possibly outside the repo (delta read 3, F1/F2)."""
    parts = rel.split(os.sep)[:-1]
    cur = repo
    for i, part in enumerate(parts):
        cur = os.path.join(cur, part)
        if os.path.islink(cur):
            return os.sep.join(parts[:i + 1])
    return None


def link_left_by_dotdot(path):
    """The first symlink in `path` (as given) that a later `..` steps back out of, else None. The system follows the
    link before the `..`, but `abspath` collapses the pair as text, so the path would name one file and the tools
    read another (delta read 4)."""
    root = os.sep if os.path.isabs(path) else ""
    stack = []   # (prefix, is_link) per component kept
    for part in path.split(os.sep):
        if part in ("", "."):
            continue
        if part == "..":
            if stack:
                prefix, is_link = stack.pop()
                if is_link:
                    return prefix
            continue
        prefix = os.path.join(stack[-1][0], part) if stack else root + part
        stack.append((prefix, os.path.islink(prefix)))
    return None


def _rel(repo, glossary):
    """The glossary's path relative to the repo root (a relative one is taken from the root); CheckError outside."""
    path = glossary if os.path.isabs(glossary) else os.path.join(repo, glossary)
    link = link_left_by_dotdot(path)
    if link:
        raise CheckError(f"--glossary {glossary!r} steps back out of the symlinked directory {link!r} with '..': "
                         "pass the path without it")
    rel = repo_relpath(repo, path)
    if rel is None:
        raise CheckError(f"--glossary {glossary!r} is outside --repo {repo!r}")
    return rel


def _sides(repo, rel, staged, base, head):
    """[(where, mode)] for each side of the change that holds `rel`: the index, else HEAD (`--staged`); base, and head
    or the working tree without --head. A literal pathspec: a path carrying `[` or `*` is a path, never a pattern."""
    spec = f":(literal){rel}"
    found = []
    if staged:
        for ln in _git_ok(repo, "ls-files", "--stage", "--", spec).splitlines():
            found.append(("the index", ln.split()[0]))
        revs = ["HEAD"] if not found and _is_commit(repo, "HEAD") else []
    else:
        revs = [base] + ([head] if head else [])
        path = os.path.join(repo, rel)
        if not head and os.path.lexists(path):
            found.append(("the working tree", _LINK_MODE if os.path.islink(path) else "file"))
    for rev in revs:
        for ln in _git_ok(repo, "ls-tree", "--full-tree", rev, "--", spec).splitlines():
            found.append((rev, ln.split()[0]))
    return found


def _require_held(repo, glossary, rel, staged, base, head):
    """CheckError when no side of the change holds the glossary (a wrong --glossary, not "the change does not touch
    the glossary", SP-TE9), or when a side holds it as a symlink: git diffs a link as its target's NAME, so the check
    would read one line of path instead of the glossary (delta read 2, P1). The fix rounds that followed links
    instead each broke a case the last one had right; the link is refused, never resolved. A working-tree side
    (no --head) behind a linked directory is refused too: git holds no file at that path (delta read 3, F1/F2)."""
    if not staged and not head:
        d = linked_dir(repo, rel)
        if d:
            raise CheckError(f"--glossary {glossary!r} is behind the symlinked directory {d!r} in the working tree: "
                             "pass the path the repo tracks")
    sides = _sides(repo, rel, staged, base, head)
    if not sides:
        raise CheckError(f"--glossary {glossary!r} is on neither side of the change")
    for where, mode in sides:
        if mode == _LINK_MODE:
            raise CheckError(f"--glossary {glossary!r} is a symlink in {where}: pass the file it points to")


_PLAIN = ("--no-ext-diff", "--no-textconv", "--no-color")   # a user's diff.external / textconv must not hide lines


def _rename_source(repo, rel, staged, base, head):
    """The glossary's path before the change when the change renamed or moved it, else None. `rel` is the path git
    prints (relative to the root); comparing the --glossary as given missed a rename of an absolute one."""
    args = ["diff", "--cached", "-M", "--name-status", *_PLAIN] if staged else \
        ["diff", "-M", "--name-status", *_PLAIN, base] + ([head] if head else [])
    for ln in _git_ok(repo, *args).splitlines():
        parts = ln.split("\t")
        if parts[0].startswith("R") and len(parts) == 3 and parts[2] == rel:
            return parts[1]
    return None


def _diff(repo, glossary, staged, base, head):
    _require_root(repo)
    if not staged:
        for flag, rev in (("--base", base), ("--head", head)):
            if rev is not None and not _is_commit(repo, rev):
                raise CheckError(f"{flag} {rev!r} is not a commit")
    # one path for every read, held, renamed and diffed alike: a held path that the diff did not read was a silent
    # pass behind a symlinked directory (delta read 2, P2)
    rel = _rel(repo, glossary)
    _require_held(repo, glossary, rel, staged, base, head)
    old = _rename_source(repo, rel, staged, base, head)
    paths = ["--"] + [f":(literal){p}" for p in ((old, rel) if old else (rel,))]
    if staged:
        args = ["diff", "--cached", "-U0", "-M", *_PLAIN, *paths]
    else:
        args = ["diff", "-U0", "-M", *_PLAIN, base] + ([head] if head else []) + paths
    out = _git_proc(repo, *args)
    if out.returncode:
        raise CheckError(f"git diff failed: {out.stderr.strip()[:200]}")
    return out.stdout


def _parse_diff(diff):
    """(added: [(new_line_no, text)], removed_text) from a -U0 unified diff of one file. `---`/`+++` are file headers
    only before a file's first hunk (as in interface_forms): an added `++…` line or a removed `--…` line is content."""
    added, removed, line_no, in_header = [], [], 0, False
    for ln in diff.splitlines():
        if ln.startswith("diff --git "):
            in_header = True
            continue
        m = _HUNK.match(ln)
        if m:
            line_no, in_header = int(m.group(1)), False
        elif in_header:
            continue
        elif ln.startswith("+"):
            added.append((line_no, ln[1:]))
            line_no += 1
        elif ln.startswith("-"):
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
                     "entry {line, class, token, text}; exit 1 iff findings, 0 otherwise, 2 naming what failed: "
                     "a usage error, a --repo that is not a work-tree root, a revision that names no commit, a "
                     "--glossary on neither side of the change, git failing",
        },
        "consumer_page": "GLOSSARY_ALTITUDE.md (vendoring, the pre-commit hook, the CI step)",
    }


# ---- strict argv: BEGIN (agent-kit #1625) ------------------------------------------------------------
# Byte-identical in throughline land_gate.py, spec_surface.py, glossary_altitude.py and backlog tracker.py
# (agent-kit tests keep the copies equal). A copy per file, not an import: land_gate.py is vendored as a
# single file, and a suite may not import from another suite.
# argparse is the ONE parser: it refuses a malformed argv AND builds the dict the dispatch reads, so no
# second parser can disagree with it (a validator in front of the old parser blessed `--repo=/x`).
ARGV_VALUE, ARGV_SWITCH, ARGV_OPTIONAL = "value", "switch", "optional"


class _ArgvError(Exception):
    pass


class _StrictArgvParser(argparse.ArgumentParser):
    def error(self, message):  # raise instead of exiting, so main() keeps returning an int
        raise _ArgvError(message)


def parse_strict_argv(cmd, arity, args, positionals=0, json_errors=True):
    """Parse one subcommand's argv. Returns (flags, None) to dispatch on, or (None, exit_code).

    `arity` maps each accepted flag to ARGV_VALUE (`--f <v>`; a bare `--f` is refused), ARGV_SWITCH
    (a bare `--f` -> True; `--f <v>` is refused) or ARGV_OPTIONAL (absent, bare -> True, or `--f <v>`).
    `flags` holds only the flags given, plus "_positional" (a list) when `positionals` > 0.
    Refused with exit 2, before any side effect: an undeclared flag, an ARGV_VALUE flag with no value or an
    empty one (`--f ""`: read downstream as absent, it would end as a success; agent-kit #3149), a switch
    given a value, a positional beyond `positionals`. An ARGV_OPTIONAL flag's empty value is kept: the
    tool reads it as its bare form. `-h`/`--help` prints the flags and returns exit 0.
    """
    # The old parsers' token rule, kept: a value flag takes the next token unless it starts with `--`.
    # Joining it as `--f=<v>` first stops argparse refusing a value that starts with `-` (`--body "- item"`).
    joined, i = [], 0
    while i < len(args):
        name = args[i][2:] if args[i].startswith("--") else None
        if arity.get(name) in (ARGV_VALUE, ARGV_OPTIONAL) and i + 1 < len(args) \
                and not args[i + 1].startswith("--"):
            joined.append(f"{args[i]}={args[i + 1]}")
            i += 2
        else:
            joined.append(args[i])
            i += 1
    usage = sorted("--" + f for f in arity)
    if "-h" in joined or "--help" in joined:
        # `values`: the flags that take a value, so a caller can build a valid argv from this help alone
        values = sorted("--" + f for f, k in arity.items() if k in (ARGV_VALUE, ARGV_OPTIONAL))
        print(json.dumps({"command": cmd, "flags": usage, "values": values, "positionals": positionals}))
        return None, 0
    parser = _StrictArgvParser(prog=cmd, add_help=False, allow_abbrev=False)
    for name, kind in arity.items():
        kw = {"dest": name, "default": argparse.SUPPRESS}
        if kind == ARGV_SWITCH:
            kw.update(action="store_const", const=True)
        elif kind == ARGV_OPTIONAL:
            kw.update(nargs="?", const=True)
        parser.add_argument("--" + name, **kw)
    if positionals:
        parser.add_argument("_positional", nargs="*")
    try:
        flags = vars(parser.parse_args(joined))
        extra = flags.get("_positional", [])[positionals:]
        if extra:
            raise _ArgvError("unrecognized arguments: " + " ".join(extra))
        empty = sorted("--" + f for f, v in flags.items() if arity.get(f) == ARGV_VALUE and v == "")
        if empty:
            raise _ArgvError(f"argument {empty[0]}: expected a non-empty value")
    except _ArgvError as e:
        msg = f"{cmd}: {e}"
        print(json.dumps({"error": msg, "flags": usage}) if json_errors else f"{msg} (accepts: {' '.join(usage)})",
              file=sys.stderr)
        return None, 2
    return flags, None
# ---- strict argv: END --------------------------------------------------------------------------------


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd in ("", "-h", "--help", "help") or (cmd != "check" and ("--help" in argv[2:] or "-h" in argv[2:])):
        print(json.dumps(_usage(), indent=2))
        return 0
    # `check --help` falls through: the strict block prints the command's flags and the ones taking a value
    try:
        if cmd != "check":
            raise CheckError(f"unknown command: {cmd!r}")
        f, rc = parse_strict_argv(
            "check", {k[2:]: (ARGV_VALUE if takes else ARGV_SWITCH) for k, takes in _FLAGS.items()}, argv[2:])
        if f is None:
            return rc
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
