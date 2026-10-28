"""SP-T1 gate: the shared descriptor parser — entity refs, Component selection, Resource documents."""

from __future__ import annotations

from pathlib import Path

from iris.sources._catalog import parse_descriptor, parse_entity_ref


def test_parse_entity_ref_kinds_namespaces_and_bare_names() -> None:
    assert parse_entity_ref("resource:erp-account") == ("resource", None, "erp-account")
    assert parse_entity_ref("component:default/x") == ("component", "default", "x")
    assert parse_entity_ref("y") == (None, None, "y")


def test_component_found_after_a_leading_resource_document(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog-info.yaml"
    catalog.write_text(
        "kind: Resource\nmetadata:\n  name: shared-db\n"
        "---\n"
        "kind: Component\nmetadata:\n  name: app\n  tags: [t]\nspec:\n  dependsOn: [resource:other]\n",
        encoding="utf-8",
    )
    descriptor = parse_descriptor(catalog)
    assert descriptor.component["metadata"]["name"] == "app"
    assert [r["metadata"]["name"] for r in descriptor.resources] == ["shared-db"]
    assert descriptor.depends_on == ["resource:other"]
