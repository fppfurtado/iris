"""SP-T2 gate: a source declared in sources.toml is federated; an undeclared one is absent."""

from __future__ import annotations

from dataclasses import dataclass

from iris.config import Config, SourceSpec, load_config
from iris.core.registry import Registry
from iris.core.source import Query, SourceResult


@dataclass
class FakeSource:
    name: str

    def read(self, query: Query) -> SourceResult:  # pragma: no cover - not exercised here
        return SourceResult()


def _registry_with(*names: str) -> Registry:
    reg = Registry()
    for n in names:
        reg.register(n, lambda opts, _n=n: FakeSource(_n))
    return reg


def test_declared_source_is_federated_undeclared_is_absent() -> None:
    reg = _registry_with("alpha", "beta")
    config = Config(sources=[SourceSpec("alpha", {})])
    resolved = [s.name for s in reg.resolve(config)]
    assert resolved == ["alpha"]  # declared alpha is federated
    assert "beta" not in resolved  # registered-but-undeclared beta is absent


def test_undeclared_name_never_touches_other_sources() -> None:
    # Declaring an unknown source must not drop the known ones (isolation, PR5).
    reg = _registry_with("alpha")
    config = Config(sources=[SourceSpec("alpha", {}), SourceSpec("ghost", {})])
    resolved = [s.name for s in reg.resolve(config)]
    assert resolved == ["alpha"]


def test_load_config_parses_declared_sources(tmp_path) -> None:
    toml = tmp_path / "sources.toml"
    toml.write_text("[sources.mneme]\n\n[sources.constellation]\nroot = \"~/x\"\n", encoding="utf-8")
    config = load_config(toml)
    assert [s.name for s in config.sources] == ["mneme", "constellation"]
    assert config.sources[1].options == {"root": "~/x"}
