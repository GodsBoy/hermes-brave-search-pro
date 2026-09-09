"""Run upstream install and migration guards against the distributable tree."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def distribution(tmp_path: Path) -> Path:
    tree = tmp_path / "distribution"
    # Include pending source additions locally, but never ignored private state.
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
    ).decode().split("\0")
    for name in filter(None, files):
        source = ROOT / name
        assert not source.is_symlink(), name
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tree


def test_source_archive_excludes_private_state(
    distribution: Path, tmp_path: Path
) -> None:
    for name in (".codegraph", ".verification", "plans", "docs/plans"):
        private = distribution / name / "private.txt"
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text("private build fixture", encoding="utf-8")
    subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(tmp_path / "dist")],
        cwd=distribution,
        check=True,
        capture_output=True,
        timeout=60,
    )
    archive = next((tmp_path / "dist").glob("*.tar.gz"))
    with tarfile.open(archive) as package:
        names = [Path(name).parts[1:] for name in package.getnames()]
    assert not any("private.txt" in name for name in names)
    assert ("tests", "test_tavily_provider.py") in names
    assert ("src", "hermes_brave_search", "__init__.py") in names
    assert ("plugin.yaml",) in names


def test_distribution_passes_real_hermes_guards(
    distribution: Path, tmp_path: Path
) -> None:
    python = os.environ.get("HERMES_TEST_PYTHON")
    if not python:
        if importlib.util.find_spec("hermes_cli") is None:
            pytest.skip("Hermes integration requires HERMES_TEST_PYTHON")
        python = sys.executable

    script = """
import json
import sys
from pathlib import Path
from hermes_cli.plugins_cmd import _check_manifest_version, _read_manifest
from hermes_cli.plugins_manifest import parse_manifest_file
from hermes_cli.plugin_compat import scan_plugin as scan_compat
from tools.plugin_guard import scan_plugin, should_allow_plugin_install

tree = Path(sys.argv[1])
_check_manifest_version(_read_manifest(tree), 'brave-search')
manifest = parse_manifest_file(tree / 'plugin.yaml', tree, 'user', '')
assert manifest is not None
assert manifest.capabilities == ['tools.override']
assert not scan_compat(tree)
result = scan_plugin(tree)
assert result.verdict == 'safe', [(f.pattern_id, f.file) for f in result.findings]
assert should_allow_plugin_install(result, force=False)[0] is True
print(json.dumps({'verdict': result.verdict, 'findings': len(result.findings)}))
"""
    env = os.environ.copy()
    env.update(
        HERMES_HOME=str(tmp_path / "hermes"),
        HERMES_ENABLE_PROJECT_PLUGINS="0",
    )
    result = subprocess.run(
        [python, "-c", script, str(distribution)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert json.loads(result.stdout)["verdict"] == "safe"
