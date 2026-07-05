from __future__ import annotations

import importlib.util
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import tomllib


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


def test_directory_plugin_shim_exposes_register():
    shim_path = Path(__file__).resolve().parents[1] / "__init__.py"
    spec = importlib.util.spec_from_file_location("brave_directory_plugin", shim_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.register)


def test_package_and_plugin_versions_match():
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    package_version = pyproject["project"]["version"]

    assert f"version: {package_version}\n" in (root / "plugin.yaml").read_text()
