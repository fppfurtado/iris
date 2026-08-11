"""SP-T2 gate: a source declared in sources.toml (with its type) is federated by the
type's factory; an undeclared one is absent — without touching other sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from iris.config import Config, SourceSpec, discover_config_path, load_config
from iris.core.registry import Registry
from iris.core.source import Query, SourceResult


@dataclass
class FakeSource:
    name: str

    def read(self, query: Query) -> SourceResult:  # pragma: no cover - not exercised here
        return SourceResult()


def _registry(*types: str) -> Registry:
    reg = Registry()
    for t in types:
        reg.register(t, lambda name, opts: FakeSource(name))
    return reg


def test_declared_source_is_federated_undeclared_is_absent() -> None:
    reg = _registry("alpha", "beta")
    config = Config(sources=[SourceSpec("alpha")])  # no type -> resolved by name
    resolved = [s.name for s in reg.resolve(config)]
    assert resolved == ["alpha"]
    assert "beta" not in resolved


def test_type_selects_implementation_name_is_the_instance() -> None:
    reg = _registry("cli-json")
    config = Config(sources=[SourceSpec("mneme", {"x": 1}, type="cli-json")])
    resolved = reg.resolve(config)
    assert [s.name for s in resolved] == ["mneme"]  # instance name, resolved via type


def test_unknown_type_skipped_without_touching_others() -> None:
    reg = _registry("alpha")
    config = Config(sources=[SourceSpec("alpha"), SourceSpec("ghost", type="nonesuch")])
    assert [s.name for s in reg.resolve(config)] == ["alpha"]


def test_load_config_parses_type_and_strips_it_from_options(tmp_path) -> None:
    toml = tmp_path / "sources.toml"
    toml.write_text(
        "[sources.constellation]\n\n"
        '[sources.mneme]\ntype = "cli-json"\ncommand = ["mneme", "ground", "{query}", "--json"]\n',
        encoding="utf-8",
    )
    config = load_config(toml)
    by_name = {s.name: s for s in config.sources}
    assert by_name["constellation"].type == ""  # no type -> name-fallback at resolve
    assert by_name["mneme"].type == "cli-json"
    assert "type" not in by_name["mneme"].options  # type is not left in options
    assert by_name["mneme"].options["command"][0] == "mneme"


def _isolate_discovery(monkeypatch, tmp_path) -> None:
    """Neutralize the ambient env + cwd so a test controls what discovery sees."""
    monkeypatch.delenv("IRIS_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    empty = tmp_path / "cwd-empty"
    empty.mkdir(exist_ok=True)
    monkeypatch.chdir(empty)


def test_env_override_wins_and_is_used_verbatim(monkeypatch, tmp_path) -> None:
    _isolate_discovery(monkeypatch, tmp_path)
    explicit = tmp_path / "custom" / "s.toml"
    monkeypatch.setenv("IRIS_CONFIG", str(explicit))
    # Used verbatim even before it exists — the override names the intended path.
    assert discover_config_path() == explicit


def test_cwd_config_preferred_over_xdg(monkeypatch, tmp_path) -> None:
    _isolate_discovery(monkeypatch, tmp_path)
    cwd = tmp_path / "proj"
    cwd.mkdir()
    (cwd / "sources.toml").write_text("", encoding="utf-8")
    xdg = tmp_path / "xdg" / "iris"
    xdg.mkdir(parents=True)
    (xdg / "sources.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(cwd)
    assert discover_config_path() == Path("sources.toml")


def test_falls_back_to_xdg_when_no_cwd_config(monkeypatch, tmp_path) -> None:
    _isolate_discovery(monkeypatch, tmp_path)
    xdg = tmp_path / "xdg" / "iris"
    xdg.mkdir(parents=True)
    user_config = xdg / "sources.toml"
    user_config.write_text("", encoding="utf-8")
    assert discover_config_path() == user_config


def test_no_config_anywhere_raises_listing_searched_paths(monkeypatch, tmp_path) -> None:
    _isolate_discovery(monkeypatch, tmp_path)
    with pytest.raises(FileNotFoundError) as excinfo:
        discover_config_path()
    msg = str(excinfo.value)
    assert "sources.toml" in msg
    assert "IRIS_CONFIG" in msg
