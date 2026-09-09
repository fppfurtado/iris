"""F6-T1 — the ref parser: cross-repo ``<repo>#<n>`` issues + within-store ``^<id>`` anchors."""

from iris.sources._repos import Ref, parse_refs, repo_refs


def test_parses_issue_and_anchor_refs_typed_and_in_order():
    # F6-T1 acceptance: text with iris#5, agent-kit#1464 and ^dogfd1 -> three typed Refs, correct
    # (slug, number) / (anchor), first-seen order.
    text = "resolve iris#5 then agent-kit#1464 gated on ^dogfd1"
    assert parse_refs(text) == [
        Ref(kind="issue", slug="iris", number=5),
        Ref(kind="issue", slug="agent-kit", number=1464),
        Ref(kind="anchor", anchor="dogfd1"),
    ]


def test_heading_and_spaced_pr_are_not_refs():
    # F6-T1 acceptance: a `## x` heading or a spaced `PR #32` must NOT yield a Ref.
    assert parse_refs("## x section and PR #32 in review") == []


def test_dedups_preserving_first_seen_order():
    text = "iris#5 blocks ^dogfd1, and iris#5 again, plus ^dogfd1"
    assert parse_refs(text) == [
        Ref(kind="issue", slug="iris", number=5),
        Ref(kind="anchor", anchor="dogfd1"),
    ]


def test_uppercase_acronym_refs_are_dropped_like_repo_refs():
    # Same lowercase-led discipline as repo_refs: PR#25 / GLPI#7 are prose, not repos.
    assert parse_refs("see PR#25 and GLPI#7") == []


def test_anchor_inside_a_word_is_not_a_ref():
    assert parse_refs("a^b is not an anchor") == []


def test_repo_refs_unaffected_by_number_capture():
    # The shared _REPO_REF now captures the number (group 2); repo_refs still keys on the slug alone.
    assert repo_refs("iris#5 and iris#31 and agent-kit#1464") == ["iris", "agent-kit"]
