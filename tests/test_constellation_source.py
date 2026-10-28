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


def test_multi_document_catalog_info_is_parsed(tmp_path) -> None:
    # A catalog-info.yaml may hold several `---`-separated entities; the first
    # (mapping) document is the Component and must parse without error.
    repo = tmp_path / "multi"
    repo.mkdir()
    (repo / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [multi]\nspec:\n  type: library\n"
        "---\n"
        "kind: Location\nmetadata:\n  name: extra\n",
        encoding="utf-8",
    )
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{repo}]\ncheckout = x\n", encoding="utf-8")

    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())

    by_id = {n.id: n for n in result.nodes}
    assert "multi" in by_id["multi"].tags  # first document parsed, not a YAML crash


def _single_repo(tmp_path: Path, name: str, catalog: str) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    (repo / "catalog-info.yaml").write_text(catalog, encoding="utf-8")
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{repo}]\ncheckout = x\n", encoding="utf-8")
    return mrconfig


def test_resources_become_nodes_hosted_by_the_repo(tmp_path) -> None:
    mrconfig = _single_repo(
        tmp_path,
        "host-repo",
        "kind: Component\nmetadata:\n  name: host-repo\n"
        "---\n"
        "kind: Resource\nmetadata:\n  name: res-a\nspec:\n  type: database\n"
        "---\n"
        "kind: Resource\nmetadata:\n  name: res-b\n",
    )
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())

    repos = [n for n in result.nodes if n.kind == "repo"]
    resources = {n.id: n for n in result.nodes if n.kind == "resource"}
    assert [n.id for n in repos] == ["host-repo"]
    assert set(resources) == {"res-a", "res-b"}
    assert all(n.attrs["host"] == "host-repo" for n in resources.values())
    rels = {(r.from_, r.type, r.to) for r in result.relations}
    assert {("res-a", "hosted-by", "host-repo"), ("res-b", "hosted-by", "host-repo")} <= rels


def test_component_metadata_read_when_first_document_is_a_resource(tmp_path) -> None:
    mrconfig = _single_repo(
        tmp_path,
        "late-component",
        "kind: Resource\nmetadata:\n  name: res\n"
        "---\n"
        "kind: Component\nmetadata:\n  name: late-component\n  description: the repo\n  tags: [x]\n",
    )
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    repo = next(n for n in result.nodes if n.kind == "repo")
    assert repo.title == "the repo"
    assert repo.tags == ["x"]


def test_resource_dependency_of_is_read_as_entity_names(tmp_path) -> None:
    mrconfig = _single_repo(
        tmp_path,
        "host",
        "kind: Component\nmetadata:\n  name: host\n"
        "---\n"
        "kind: Resource\nmetadata:\n  name: res\nspec:\n  dependencyOf: [component:a, b]\n",
    )
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    res = next(n for n in result.nodes if n.kind == "resource")
    assert res.attrs["dependency_of"] == ["a", "b"]
