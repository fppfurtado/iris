"""SP-T6 gate: `iris check` end-to-end — constellation (mrconfig + roots) and forge-repos (a fake forge
CLI) through federate → compose_membership → the Typer command, with its exit codes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from iris.cli import app

runner = CliRunner()
HOST = "forge.example"

FAKE_FORGE = """\
import json, os, sys
if os.environ.get("FAKE_FORGE_FAIL"):
    sys.exit(3)
repos = os.environ.get("FAKE_FORGE_REPOS", "").split(",")
print(json.dumps([{"nameWithOwner": f"{sys.argv[1]}/{r}", "isArchived": False} for r in repos if r]))
"""


def _checkout(path: Path, name: str, descriptor: bool) -> Path:
    (path / ".git").mkdir(parents=True)
    (path / ".git" / "config").write_text(
        f'[remote "origin"]\n\turl = git@{HOST}:org/{name}.git\n', encoding="utf-8"
    )
    if descriptor:
        (path / "catalog-info.yaml").write_text(f"metadata:\n  name: {name}\n", encoding="utf-8")
    return path


def _world(tmp_path: Path, with_bare: bool, forge_and_roots: bool = True) -> Path:
    root = tmp_path / "src"
    app_repo = _checkout(root / "app", "app", descriptor=True)
    if with_bare:
        _checkout(root / "bare", "bare", descriptor=False)
    mrconfig = tmp_path / ".mrconfig"
    mrconfig.write_text(f"[{app_repo}]\ncheckout = git clone 'git@{HOST}:org/app.git' 'app'\n", encoding="utf-8")
    script = tmp_path / "fake_forge.py"
    script.write_text(FAKE_FORGE, encoding="utf-8")
    config = tmp_path / ("sources.toml" if forge_and_roots else "plain.toml")
    body = f'[sources.constellation]\ntype = "constellation"\nmrconfig = "{mrconfig}"\n'
    if forge_and_roots:
        body += (
            f'roots = ["{root}"]\n\n'
            f'[sources.forge]\ntype = "forge-repos"\nhost = "{HOST}"\norgs = ["org"]\n'
            f'command = ["{sys.executable}", "{script}", "{{org}}"]\n'
            '[sources.forge.map]\npath = "nameWithOwner"\narchived = "isArchived"\n'
        )
    config.write_text(body, encoding="utf-8")
    return config


def _invoke(config: Path, *args: str, repos: str = "app,bare", fail: bool = False):
    env = {"IRIS_CONFIG": str(config), "FAKE_FORGE_REPOS": repos, "FAKE_FORGE_FAIL": "1" if fail else ""}
    return runner.invoke(app, list(args), env=env)


def test_drift_exits_1_with_a_section_per_kind(tmp_path) -> None:
    result = _invoke(_world(tmp_path, with_bare=True), "check")
    assert result.exit_code == 1, result.output
    assert "## undeclared-member" in result.output
    assert f"{HOST}/org/bare" in result.output


def test_json_output_shape(tmp_path) -> None:
    result = _invoke(_world(tmp_path, with_bare=True), "check", "--json")
    payload = json.loads(result.stdout)
    assert set(payload) == {"drift", "skipped", "counts"}
    assert payload["drift"]
    assert all(set(item) == {"kind", "subject", "detail"} for item in payload["drift"])


def test_no_drift_and_nothing_skipped_exits_0(tmp_path) -> None:
    result = _invoke(_world(tmp_path, with_bare=False), "check", repos="app")
    assert result.exit_code == 0, result.output
    assert "clean" in result.output


def test_failing_forge_without_drift_exits_2_and_is_not_clean(tmp_path) -> None:
    result = _invoke(_world(tmp_path, with_bare=False), "check", repos="app", fail=True)
    assert result.exit_code == 2, result.output
    assert "clean" not in result.stdout
    assert "incomplete" in result.stdout


def test_repos_output_unaffected_by_forge_and_roots(tmp_path) -> None:
    full = _invoke(_world(tmp_path, with_bare=True), "repos")
    plain = _invoke(_world(tmp_path / "p", with_bare=True, forge_and_roots=False), "repos")
    assert full.exit_code == 0 and plain.exit_code == 0
    assert full.stdout == plain.stdout


def test_unreadable_registry_exits_2_without_false_drift(tmp_path) -> None:
    config = _world(tmp_path, with_bare=False)
    (tmp_path / ".mrconfig").unlink()
    mirror = tmp_path / "members.md"
    mirror.write_text("`app`\n", encoding="utf-8")
    config.write_text(
        config.read_text(encoding="utf-8")
        + f'\n[[check.mirrors]]\npath = "{mirror}"\npattern = "`([a-z]+)`"\n',
        encoding="utf-8",
    )
    result = _invoke(config, "check", repos="app")
    assert result.exit_code == 2, result.output
    assert "## " not in result.stdout
    assert "registry" in result.stderr
