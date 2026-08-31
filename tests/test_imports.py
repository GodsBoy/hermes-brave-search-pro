from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tomllib
from importlib.metadata import entry_points
from pathlib import Path


def test_plugin_import_does_not_import_httpx():
    script = "import hermes_brave_search, sys; print('httpx' in sys.modules)"

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "False"


def test_entry_point_loads_module_with_register():
    matches = [
        ep
        for ep in entry_points(group="hermes_agent.plugins")
        if ep.name == "brave-search"
    ]

    assert matches
    loaded = matches[0].load()

    assert hasattr(loaded, "register")
    assert callable(loaded.register)
    assert hasattr(loaded, "TavilyExtractProvider")


def test_directory_plugin_shim_exposes_register():
    shim_path = Path(__file__).resolve().parents[1] / "__init__.py"
    spec = importlib.util.spec_from_file_location("brave_directory_plugin", shim_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.register)


def test_release_metadata_is_aligned():
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    lockfile = tomllib.loads((root / "uv.lock").read_text())
    project = pyproject["project"]
    package_version = project["version"]
    classifiers = set(project["classifiers"])
    locked_package = next(
        package
        for package in lockfile["package"]
        if package["name"] == project["name"]
    )

    assert package_version == "0.1.9"
    assert f"version: {package_version}\n" in (root / "plugin.yaml").read_text()
    dashboard_manifest = json.loads(
        (root / "dashboard" / "manifest.json").read_text()
    )
    assert dashboard_manifest["version"] == package_version
    assert locked_package["version"] == package_version
    assert project["requires-python"] == ">=3.11,<3.14"
    assert lockfile["requires-python"] == ">=3.11, <3.14"
    assert pyproject["tool"]["ruff"]["target-version"] == "py311"
    assert "Programming Language :: Python :: 3.10" not in classifiers
    assert {
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    } <= classifiers


def test_plugin_manifest_only_requires_brave_key():
    plugin_manifest = (Path(__file__).resolve().parents[1] / "plugin.yaml").read_text()

    assert "BRAVE_SEARCH_API_KEY" in plugin_manifest
    assert "TAVILY_API_KEY" not in plugin_manifest
    assert "provides_web_providers:" in plugin_manifest
    assert "  - brave-pro" in plugin_manifest
    assert "  - tavily" in plugin_manifest


def test_ci_installs_current_hermes_editably():
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text()

    assert "git clone --depth 1" in workflow
    assert 'uv pip install -e "$RUNNER_TEMP/hermes-agent"' in workflow
    wheel_install = (
        "uv pip install 'git+https://github.com/NousResearch/hermes-agent.git'"
    )
    assert wheel_install not in workflow
