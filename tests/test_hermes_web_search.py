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
_PLUGIN_CAPABILITY_ENTRY_POINT = """\
[hermes_agent.plugin_capabilities]
brave-search.tools.override = hermes_brave_search
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

    import httpx

    from hermes_brave_search.constants import (
        BRAVE_LLM_CONTEXT_ENDPOINT,
        BRAVE_SEARCH_ENDPOINT,
    )
    from hermes_cli.config import load_config
    from hermes_cli.plugins import get_plugin_manager

    network_attempts = []
    socket_type = socket.socket

    class NetworkGuardSocket(socket_type):
        def connect(self, *args, **kwargs):
            network_attempts.append((args, kwargs))
            raise AssertionError("unexpected network request")

        def connect_ex(self, *args, **kwargs):
            network_attempts.append((args, kwargs))
            raise AssertionError("unexpected network request")

    socket.socket = NetworkGuardSocket

    hermes_home = Path(sys.argv[1])
    config_path = hermes_home / "config.yaml"
    config_path.write_text(
        json.dumps(
            {
                "plugins": {
                    "enabled": ["brave-search"],
                    "entries": {
                        "brave-search": {
                            "granted_capabilities": ["tools.override"],
                        }
                    },
                },
                "web": {
                    "backend": "brave-pro",
                    "search_backend": "brave-pro",
                    "keyless_fallback": False,
                    "keyless_rescue": False,
                    "cache_enabled": True,
                },
            }
        ),
        encoding="utf-8",
    )

    calls = []

    def web_payload(query):
        return {
            "web": {
                "results": [
                    {
                        "title": f"{query} result {index}",
                        "url": f"https://source{index}.example.test/page",
                        "description": f"Description {index}",
                    }
                    for index in range(1, 11)
                ]
            }
        }

    def context_payload(query):
        return {
            "grounding": {
                "generic": [
                    {
                        "title": f"{query} context",
                        "url": "https://context.example.test/page",
                        "snippets": ["Context snippet"],
                    }
                ]
            }
        }

    def fake_get(url, params=None, **kwargs):
        if url != BRAVE_SEARCH_ENDPOINT:
            raise AssertionError(f"unexpected GET URL: {url}")
        params = dict(params or {})
        calls.append({"endpoint": "web", "params": params})
        query = params.get("q")
        status = 422 if query == "web failure" else 200
        payload = (
            {"error": "synthetic web failure"}
            if status != 200
            else web_payload(query)
        )
        return httpx.Response(
            status,
            json=payload,
            request=httpx.Request("GET", url),
        )

    def fake_post(url, json=None, **kwargs):
        if url != BRAVE_LLM_CONTEXT_ENDPOINT:
            raise AssertionError(f"unexpected POST URL: {url}")
        params = dict(json or {})
        calls.append({"endpoint": "context", "params": params})
        query = params.get("q")
        status = 422 if query == "context failure" else 200
        payload = (
            {"error": "synthetic context failure"}
            if status != 200
            else context_payload(query)
        )
        return httpx.Response(
            status,
            json=payload,
            request=httpx.Request("POST", url),
        )

    httpx.get = fake_get
    httpx.post = fake_post

    manager = get_plugin_manager()
    manager.discover_and_load()
    plugin = next(
        plugin
        for plugin in manager.list_plugins()
        if plugin["key"] == "brave-search"
    )

    from model_tools import handle_function_call

    def dispatch(query):
        return json.loads(
            handle_function_call("web_search", {"query": query, "limit": 2})
        )

    success_first = dispatch("combined success")
    success_second = dispatch("combined success")
    success_calls = [
        call for call in calls if call["params"].get("q") == "combined success"
    ]

    context_failure_first = dispatch("context failure")
    context_failure_second = dispatch("context failure")
    context_failure_calls = [
        call for call in calls if call["params"].get("q") == "context failure"
    ]

    web_failure = dispatch("web failure")
    web_failure_calls = [
        call for call in calls if call["params"].get("q") == "web failure"
    ]

    print(
        json.dumps(
            {
                "plugin_enabled": plugin["enabled"],
                "plugin_error": plugin["error"],
                "configured_web": load_config()["web"],
                "success_first": success_first,
                "success_second": success_second,
                "success_calls": success_calls,
                "context_failure_first": context_failure_first,
                "context_failure_second": context_failure_second,
                "context_failure_calls": context_failure_calls,
                "web_failure": web_failure,
                "web_failure_calls": web_failure_calls,
                "network_attempts": network_attempts,
            }
        )
    )
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


def _run_scenario(tmp_path: Path) -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir()

    metadata_dir = tmp_path / "site" / "hermes_brave_search-0.dist-info"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "METADATA").write_text(_PLUGIN_METADATA, encoding="utf-8")
    (metadata_dir / "entry_points.txt").write_text(
        _PLUGIN_ENTRY_POINT + _PLUGIN_CAPABILITY_ENTRY_POINT,
        encoding="utf-8",
    )

    python_path = [str(metadata_dir.parent), str(repo_root / "src")]
    existing_python_path = os.environ.get("PYTHONPATH")
    if existing_python_path:
        python_path.append(existing_python_path)

    env = os.environ.copy()
    env.update(
        {
            "BRAVE_SEARCH_API_KEY": "synthetic-key",
            "HOME": str(tmp_path / "home"),
            "HERMES_HOME": str(hermes_home),
            "HERMES_ENABLE_PROJECT_PLUGINS": "0",
            "PYTHONPATH": os.pathsep.join(python_path),
        }
    )
    for name in ("BRAVE_API_KEY", "HERMES_SAFE_MODE"):
        env.pop(name, None)

    result = subprocess.run(
        [
            _hermes_python(),
            "-c",
            _SCENARIO,
            str(hermes_home),
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


def test_hermes_web_search_dispatches_combined_results_and_caches_envelope(tmp_path):
    result = _run_scenario(tmp_path)

    assert result["plugin_enabled"] is True
    assert result["plugin_error"] is None
    assert result["configured_web"]["backend"] == "brave-pro"
    assert result["configured_web"]["search_backend"] == "brave-pro"
    assert result["network_attempts"] == []

    success = result["success_first"]
    assert success == result["success_second"]
    assert success["success"] is True
    assert set(success) == {"success", "data"}
    assert set(success["data"]) == {"web", "llm_context"}
    assert success["data"]["web"] == [
        {
            "title": "combined success result 1",
            "url": "https://source1.example.test/page",
            "description": "Description 1",
            "position": 1,
        },
        {
            "title": "combined success result 2",
            "url": "https://source2.example.test/page",
            "description": "Description 2",
            "position": 2,
        },
    ]
    assert success["data"]["llm_context"] == [
        {
            "title": "combined success context",
            "url": "https://context.example.test/page",
            "snippets": ["Context snippet"],
        }
    ]
    assert result["success_calls"] == [
        {"endpoint": "web", "params": {"q": "combined success", "count": 10}},
        {
            "endpoint": "context",
            "params": {
                "q": "combined success",
                "count": 5,
                "maximum_number_of_urls": 5,
                "maximum_number_of_tokens": 4096,
                "maximum_number_of_tokens_per_url": 1024,
            },
        },
    ]

    context_failure = result["context_failure_first"]
    assert context_failure == result["context_failure_second"]
    assert context_failure["success"] is True
    assert context_failure["data"]["web"][0]["title"] == "context failure result 1"
    assert context_failure["data"]["llm_context"] == []
    assert "422" in context_failure["data"]["llm_context_error"]
    assert result["context_failure_calls"] == [
        {"endpoint": "web", "params": {"q": "context failure", "count": 10}},
        {
            "endpoint": "context",
            "params": {
                "q": "context failure",
                "count": 5,
                "maximum_number_of_urls": 5,
                "maximum_number_of_tokens": 4096,
                "maximum_number_of_tokens_per_url": 1024,
            },
        },
    ]

    web_failure = result["web_failure"]
    assert web_failure["success"] is False
    assert "422" in web_failure["error"]
    assert result["web_failure_calls"] == [
        {"endpoint": "web", "params": {"q": "web failure", "count": 10}}
    ]
