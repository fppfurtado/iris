"""Shared test fixtures.

``constellation_config`` builds the two-repo constellation config the federation,
MCP-adapter, and S2-proof tests all need — a ``relatorios-h3`` repo tagged
``pro-bono`` and a ``meta-system`` repo tagged ``meta`` — and returns the
``sources.toml`` path. The builder was triplicated across three test modules
(iris#8); this is the single home.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def constellation_config(tmp_path: Path) -> Path:
    """Write a two-repo constellation under ``tmp_path`` and return its config path."""
    tagged = tmp_path / "relatorios-h3"
    tagged.mkdir()
    (tagged / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [pro-bono]\nspec:\n  type: service\n", encoding="utf-8"
    )
    other = tmp_path / "meta-system"
    other.mkdir()
    (other / "catalog-info.yaml").write_text(
        "metadata:\n  tags: [meta]\nspec:\n  type: library\n", encoding="utf-8"
    )
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{tagged}]\ncheckout = x\n\n[{other}]\ncheckout = y\n", encoding="utf-8")
    config = tmp_path / "sources.toml"
    config.write_text(f'[sources.constellation]\nmrconfig = "{mrconfig}"\n', encoding="utf-8")
    return config
