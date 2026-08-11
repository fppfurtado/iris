"""SP-T5 gate: constellation returns nodes with tags; pro-bono repo carries its tag;
repos without catalog-info are flagged as incomplete-coverage."""

from __future__ import annotations

from pathlib import Path

from iris.core.source import Query
from iris.sources.constellation import ConstellationSource


def _make_constellation(tmp_path: Path) -> Path:
    # repo WITH catalog-info (tagged pro-bono, a role, a dependency)
    tagged = tmp_path / "relatorios-h3"
    tagged.mkdir()
    (tagged / "catalog-info.yaml").write_text(
        "metadata:\n"
        "  description: H3 reports\n"
        "  tags: [pro-bono, finance]\n"
        "spec:\n"
        "  type: service\n"
        "  dependsOn:\n"
        "    - component:default/gnucash-workbench\n",
        encoding="utf-8",
    )
    # repo WITHOUT catalog-info
    bare = tmp_path / "superpowers"
    bare.mkdir()

    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(
        "[DEFAULT]\ngit_gc = git gc\n\n"
        f"[{tagged}]\ncheckout = git clone x relatorios-h3\n\n"
        f"[{bare}]\ncheckout = git clone y superpowers\n",
        encoding="utf-8",
    )
    return mrconfig


def test_returns_nodes_with_tags_and_flags_incomplete_coverage(tmp_path) -> None:
    mrconfig = _make_constellation(tmp_path)
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())

    by_id = {n.id: n for n in result.nodes}
    assert set(by_id) == {"relatorios-h3", "superpowers"}

    # a repo with tag pro-bono appears with its tag
    assert "pro-bono" in by_id["relatorios-h3"].tags
    assert by_id["relatorios-h3"].roles == ["service"]

    # a repo without catalog-info has no tags and coverage is flagged
    assert by_id["superpowers"].tags == []
    assert "incomplete-coverage" in result.note
    assert "1/2" in result.note


def test_edges_become_relations(tmp_path) -> None:
    mrconfig = _make_constellation(tmp_path)
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    rels = [(r.from_, r.type, r.to) for r in result.relations]
    assert ("relatorios-h3", "dependsOn", "component:default/gnucash-workbench") in rels
