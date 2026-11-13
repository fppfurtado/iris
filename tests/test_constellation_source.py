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


# --- SP-T8 (Spec v1.2, iris#61): a repo's tags = descriptor tags + system name + registry tag words ---


def _system_source(tmp_path: Path, repos: dict[str, str | None], registry_extra: str = "", **opts):
    """A registry of ``repos`` (name -> descriptor text, or None for no descriptor)."""
    body = ""
    for name, descriptor in repos.items():
        repo = tmp_path / name
        repo.mkdir()
        if descriptor is not None:
            (repo / "catalog-info.yaml").write_text(descriptor, encoding="utf-8")
        body += f"[{repo}]\ncheckout = x\n{registry_extra}\n"
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(body, encoding="utf-8")
    return ConstellationSource("constellation", {"mrconfig": str(mrconfig), **opts})


def _repo_tags(result) -> dict[str, list[str]]:
    return {n.id: n.tags for n in result.nodes if n.kind == "repo"}


def test_spec_system_alone_becomes_the_tag(tmp_path) -> None:
    source = _system_source(tmp_path, {"alpha": "spec:\n  system: s\n"})
    assert _repo_tags(source.read(Query())) == {"alpha": ["s"]}


def test_declared_tags_come_first_and_the_system_is_not_duplicated(tmp_path) -> None:
    source = _system_source(tmp_path, {"alpha": "metadata:\n  tags: [b, s, b]\nspec:\n  system: s\n"})
    assert _repo_tags(source.read(Query())) == {"alpha": ["b", "s"]}


def test_without_spec_system_the_tags_are_the_declared_ones_deduplicated(tmp_path) -> None:
    source = _system_source(tmp_path, {"alpha": "metadata:\n  tags: [b, a, b]\nspec:\n  type: cli\n"})
    assert _repo_tags(source.read(Query())) == {"alpha": ["b", "a"]}


def test_registry_tag_words_follow_the_descriptor_tags_without_duplicates(tmp_path) -> None:
    descriptor = "metadata:\n  tags: [b]\nspec:\n  system: s\n"
    source = _system_source(tmp_path, {"alpha": descriptor}, registry_extra="tags = s x")
    assert _repo_tags(source.read(Query())) == {"alpha": ["b", "s", "x"]}


def test_a_repo_without_descriptor_carries_its_registry_tag_words(tmp_path) -> None:
    source = _system_source(tmp_path, {"alpha": None}, registry_extra="tags = x y")
    assert _repo_tags(source.read(Query())) == {"alpha": ["x", "y"]}


def test_registry_tags_are_read_literally_from_the_sections_own_line(tmp_path) -> None:
    plain, commented, indented = tmp_path / "plain", tmp_path / "commented", tmp_path / "indented"
    for repo in (plain, commented, indented):
        repo.mkdir()
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(
        "[DEFAULT]\ntags = d\n\n"
        f"[{plain}]\ncheckout = x\n\n"
        f"[{commented}]\n# tags = c\n\n"
        f"[{indented}]\ncheckout = x\n  tags = i\n",
        encoding="utf-8",
    )
    result = ConstellationSource("constellation", {"mrconfig": str(mrconfig)}).read(Query())
    # no [DEFAULT] inheritance, no commented line, no indented (continuation) line
    assert _repo_tags(result) == {"plain": [], "commented": [], "indented": []}


def test_spec_system_written_as_an_entity_ref_contributes_its_name(tmp_path) -> None:
    source = _system_source(tmp_path, {"alpha": "spec:\n  system: system:default/s\n"})
    assert _repo_tags(source.read(Query())) == {"alpha": ["s"]}


def test_non_scalar_descriptor_values_contribute_no_tag(tmp_path) -> None:
    source = _system_source(
        tmp_path,
        {
            "listed": "spec:\n  system: [a, b]\n",
            "mapped": "metadata:\n  tags: [ok, null, [x]]\nspec:\n  system: {name: a}\n",
            "one-string": "metadata:\n  tags: finance\n",
            "numbered": "metadata:\n  tags: [yes, 7]\nspec:\n  system: 42\n",
        },
    )
    assert _repo_tags(source.read(Query())) == {
        "listed": [],
        "mapped": ["ok"],
        "one-string": ["finance"],
        "numbered": ["7", "42"],  # a number is a tag; a boolean (`yes`) is not
    }


def test_universe_query_carries_each_repos_own_system(tmp_path) -> None:
    from iris.core.source import KIND_UNIVERSE

    root = tmp_path / "src"
    disk = root / "beta"
    (disk / ".git").mkdir(parents=True)
    (disk / "catalog-info.yaml").write_text("spec:\n  system: t\n", encoding="utf-8")
    source = _system_source(
        tmp_path, {"alpha": "spec:\n  system: s\n"}, registry_extra="tags = x", roots=[str(root)]
    )
    result = source.read(Query(kinds=frozenset({KIND_UNIVERSE})))
    # the registry repo carries its section's word; the disk-only repo has no section
    assert _repo_tags(result) == {"alpha": ["s", "x"], "beta": ["t"]}
