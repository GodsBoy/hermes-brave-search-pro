from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PLUGIN_ENTRY_POINT = """\
[hermes_agent.plugins]
brave-search = hermes_brave_search
"""
_PLUGIN_METADATA = """\
Metadata-Version: 2.1
Name: hermes-brave-search
Version: 0
"""

_SCENARIO = textwrap.dedent(
    """
    import json
    import socket
    import sys
    from pathlib import Path

    from agent.web_search_registry import (
        get_active_extract_provider,
        get_active_search_provider,
        get_provider,
    )
    from hermes_cli.config import load_config
    from hermes_cli.plugins import PluginManager
    from hermes_cli.tools_config import _plugin_web_search_providers
    from tools.registry import registry

    network_attempts = []

    socket_type = socket.socket

    class NetworkGuardSocket(socket_type):
        def connect(self, *args, **kwargs):
            network_attempts.append((args, kwargs))
            raise AssertionError("provider registration must not make network calls")

        def connect_ex(self, *args, **kwargs):
            network_attempts.append((args, kwargs))
            raise AssertionError("provider registration must not make network calls")

    socket.socket = NetworkGuardSocket

    hermes_home = Path(sys.argv[1])
    start_allowed = sys.argv[2] == "allowed"
    config_path = hermes_home / "config.yaml"

    def write_config(allowed):
        config = {
            "plugins": {
                "enabled": ["brave-search"],
                "entries": {
                    "brave-search": {"allow_tool_override": allowed},
                },
            },
        }
        config_path.write_text(json.dumps(config), encoding="utf-8")

    def plugin_info(manager):
        return next(
            plugin
            for plugin in manager.list_plugins()
            if plugin["key"] == "brave-search"
        )

    def builtin_brave_search(params, **kwargs):
        return json.dumps({"source": "builtin"})

    registry.register(
        name="brave_search",
        toolset="web",
        schema={"name": "brave_search", "description": "Built-in sentinel"},
        handler=builtin_brave_search,
    )

    write_config(start_allowed)
    manager = PluginManager()
    manager.discover_and_load()
    first = plugin_info(manager)
    first_entry = registry.get_entry("brave_search")

    result = {
        "first_enabled": first["enabled"],
        "first_error": first["error"],
        "first_handler": first_entry.handler.__module__,
        "first_toolset": first_entry.toolset,
        "first_provider_present": get_provider("brave-pro") is not None,
        "first_tavily_provider_present": get_provider("tavily") is not None,
        "first_config": load_config(),
    }

    if not start_allowed:
        write_config(True)
        manager.discover_and_load(force=True)

    loaded = plugin_info(manager)
    entry = registry.get_entry("brave_search")
    provider = get_provider("brave-pro")
    tavily_provider = get_provider("tavily")
    active_provider = get_active_search_provider()
    active_extract_provider = get_active_extract_provider()
    configured = load_config()
    rows = [
        row
        for row in _plugin_web_search_providers()
        if row.get("web_backend") in {"brave-pro", "tavily"}
    ]

    result.update(
        {
            "enabled": loaded["enabled"],
            "error": loaded["error"],
            "tool_count": loaded["tools"],
            "handler": entry.handler.__module__,
            "toolset": entry.toolset,
            "provider_name": provider.name if provider else None,
            "tavily_provider_name": tavily_provider.name if tavily_provider else None,
            "provider_capabilities": {
                "brave-pro": {
                    "search": provider.supports_search() if provider else None,
                    "extract": provider.supports_extract() if provider else None,
                },
                "tavily": {
                    "search": (
                        tavily_provider.supports_search()
                        if tavily_provider
                        else None
                    ),
                    "extract": (
                        tavily_provider.supports_extract()
                        if tavily_provider
                        else None
                    ),
                },
            },
            "provider_rows": rows,
            "active_provider": active_provider.name if active_provider else None,
            "active_extract_provider": (
                active_extract_provider.name if active_extract_provider else None
            ),
            "configured_web": configured.get("web"),
            "network_attempts": network_attempts,
        }
    )
    print(json.dumps(result))
    """
)


def _hermes_python() -> str:
    configured = os.environ.get("HERMES_TEST_PYTHON")
    if configured:
        return configured
    if importlib.util.find_spec("hermes_cli") is not None:
        return sys.executable
    pytest.skip(
        "Hermes is not installed in this environment; set HERMES_TEST_PYTHON "
        "to a current Hermes interpreter"
    )


def _run_scenario(tmp_path: Path, *, override_allowed: bool) -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    metadata_dir = tmp_path / "site" / "hermes_brave_search-0.dist-info"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "METADATA").write_text(_PLUGIN_METADATA, encoding="utf-8")
    (metadata_dir / "entry_points.txt").write_text(
        _PLUGIN_ENTRY_POINT,
        encoding="utf-8",
    )

    python_path = [str(metadata_dir.parent), str(repo_root / "src")]
    existing_python_path = os.environ.get("PYTHONPATH")
    if existing_python_path:
        python_path.append(existing_python_path)

    env = os.environ.copy()
    env.update(
        {
            "BRAVE_SEARCH_API_KEY": "not-a-real-key",
            "TAVILY_API_KEY": "not-a-real-tavily-key",
            "HOME": str(tmp_path / "home"),
            "HERMES_HOME": str(hermes_home),
            "HERMES_ENABLE_PROJECT_PLUGINS": "0",
            "PYTHONPATH": os.pathsep.join(python_path),
        }
    )
    for name in (
        "BRAVE_API_KEY",
        "HERMES_SAFE_MODE",
    ):
        env.pop(name, None)

    result = subprocess.run(
        [
            _hermes_python(),
            "-c",
            _SCENARIO,
            str(hermes_home),
            "allowed" if override_allowed else "denied",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_root,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


def _assert_successful_load(result: dict) -> None:
    assert result["enabled"] is True
    assert result["error"] is None
    assert result["tool_count"] == 1
    assert result["handler"] == "hermes_brave_search.tools"
    assert result["toolset"] == "brave_search"
    assert result["provider_name"] == "brave-pro"
    assert result["tavily_provider_name"] == "tavily"
    assert result["provider_capabilities"] == {
        "brave-pro": {"search": True, "extract": False},
        "tavily": {"search": False, "extract": True},
    }
    assert result["active_provider"] == "brave-pro"
    assert result["active_extract_provider"] == "tavily"
    assert result["configured_web"]["backend"] == "brave-pro"
    assert result["configured_web"]["search_backend"] == "brave-pro"
    assert result["configured_web"]["extract_backend"] == "tavily"
    assert {
        row["web_search_plugin_name"] for row in result["provider_rows"]
    } == {"brave-pro", "tavily"}
    assert result["network_attempts"] == []


def test_plugin_manager_denies_override_without_leaking_then_retries(tmp_path):
    result = _run_scenario(tmp_path, override_allowed=False)

    assert result["first_enabled"] is False
    assert "allow_tool_override" in result["first_error"]
    assert result["first_handler"] == "__main__"
    assert result["first_toolset"] == "web"
    assert result["first_provider_present"] is False
    assert result["first_tavily_provider_present"] is False
    assert result["first_config"]["web"]["backend"] != "brave-pro"
    assert result["first_config"]["web"]["search_backend"] != "brave-pro"
    assert result["first_config"]["web"].get("extract_backend") != "tavily"
    _assert_successful_load(result)


def test_plugin_manager_loads_with_override_permission(tmp_path):
    result = _run_scenario(tmp_path, override_allowed=True)

    assert result["first_enabled"] is True
    assert result["first_error"] is None
    assert result["first_handler"] == "hermes_brave_search.tools"
    assert result["first_toolset"] == "brave_search"
    assert result["first_provider_present"] is True
    _assert_successful_load(result)
