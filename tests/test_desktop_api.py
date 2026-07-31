from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import hermes_brave_search.desktop as desktop
from hermes_brave_search.desktop import search_desktop_web


class FakeClient:
    def __init__(self, result, *, api_key: str | None = "configured"):
        self.result = result
        self.api_key = api_key
        self.calls: list[dict[str, object]] = []

    def resolved_api_key(self):
        return self.api_key

    def search(self, query, *, mode, limit):
        self.calls.append({"query": query, "mode": mode, "limit": limit})
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_desktop_search_trims_query_uses_web_mode_and_whitelists_results():
    client = FakeClient(
        {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "Hermes Agent",
                        "description": "Desktop plugin documentation",
                        "url": "https://hermes-agent.nousresearch.com/docs",
                        "position": 7,
                        "tracking": "not for the desktop response",
                    }
                ]
            },
        }
    )

    response = search_desktop_web("  Hermes Agent  ", client=client)

    assert client.calls == [{"query": "Hermes Agent", "mode": "web", "limit": 5}]
    assert response == {
        "outcome": "results",
        "results": [
            {
                "title": "Hermes Agent",
                "description": "Desktop plugin documentation",
                "url": "https://hermes-agent.nousresearch.com/docs",
                "position": 7,
            }
        ],
    }


@pytest.mark.parametrize(
    "query",
    [None, "", "   ", "x" * 401, " ".join(["word"] * 51)],
)
def test_desktop_search_rejects_out_of_bounds_queries_without_calling_client(query):
    client = FakeClient({"success": True, "data": {"web": []}})

    response = search_desktop_web(query, client=client)

    assert response["outcome"] == "validation_error"
    assert client.calls == []


def test_desktop_search_reports_missing_credential_without_calling_client():
    client = FakeClient({"success": True, "data": {"web": []}}, api_key=None)

    response = search_desktop_web("Hermes Agent", client=client)

    assert response == {
        "outcome": "missing_credential",
        "message": "BRAVE_SEARCH_API_KEY is required for Brave Search.",
    }
    assert client.calls == []


def test_desktop_search_constructs_client_with_bounded_desktop_budget(monkeypatch):
    constructed: list[FakeClient] = []

    class ConfiguredFakeClient(FakeClient):
        def __init__(self):
            super().__init__({"success": True, "data": {"web": []}})
            constructed.append(self)

    monkeypatch.setattr(desktop, "BraveSearchClient", ConfiguredFakeClient)

    assert search_desktop_web("Hermes Agent") == {
        "outcome": "empty",
        "results": [],
    }
    assert len(constructed) == 1
    assert constructed[0].timeout == 6.0
    assert constructed[0].max_retries == 2
    assert constructed[0].backoff_seconds == 0.5
    assert 6.0 * 3 + 0.5 * (1 + 2) == 19.5


@pytest.mark.parametrize(
    "result",
    [
        {"success": True, "data": {"web": []}},
        {"success": True, "data": {"web": "not a list"}},
        {"success": True, "data": None},
        {"success": True},
    ],
)
def test_desktop_search_treats_empty_or_malformed_web_data_as_successful_empty(result):
    client = FakeClient(result)

    assert search_desktop_web("Hermes Agent", client=client) == {
        "outcome": "empty",
        "results": [],
    }


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        (
            {"success": False, "error": "BRAVE_SEARCH_API_KEY is required"},
            {
                "outcome": "missing_credential",
                "message": "BRAVE_SEARCH_API_KEY is required for Brave Search.",
            },
        ),
        (
            {
                "success": False,
                "error": "timeout with X-Subscription-Token secret-value",
            },
            {
                "outcome": "api_error",
                "message": "Brave Search could not complete this request. Try again.",
            },
        ),
        (
            {"success": False, "error": "429 quota exceeded"},
            {
                "outcome": "rate_limited",
                "message": "Brave Search is temporarily unavailable. Try again later.",
            },
        ),
        (
            {"success": False, "error": "401 invalid key secret-value"},
            {
                "outcome": "invalid_credential",
                "message": "Brave Search credentials were not accepted.",
            },
        ),
        (
            RuntimeError("Traceback secret-value"),
            {
                "outcome": "api_error",
                "message": "Brave Search could not complete this request. Try again.",
            },
        ),
    ],
)
def test_desktop_search_maps_client_failures_to_exact_safe_outcomes(result, expected):
    client = FakeClient(result)

    response = search_desktop_web("Hermes Agent", client=client)

    assert response == expected
    assert "secret-value" not in json.dumps(response)
    assert "Traceback" not in json.dumps(response)
    assert "X-Subscription-Token" not in json.dumps(response)


def test_dashboard_manifest_is_hidden_and_references_existing_relative_assets():
    root = Path(__file__).resolve().parents[1]
    dashboard = root / "dashboard"
    manifest = json.loads((dashboard / "manifest.json").read_text())

    assert manifest["name"] == "brave-search"
    assert manifest["api"] == "plugin_api.py"
    assert not Path(manifest["api"]).is_absolute()
    assert manifest["tab"]["hidden"] is True
    assert (dashboard / manifest["entry"]).is_file()


def test_dashboard_api_bootstraps_source_layout_and_exposes_a_sync_router():
    root = Path(__file__).resolve().parents[1]
    script = f"""
import importlib.util
import sys
import types
from pathlib import Path

class FakeAPIRouter:
    def __init__(self):
        self.routes = []

    def post(self, path):
        def register(endpoint):
            self.routes.append(types.SimpleNamespace(path=path, endpoint=endpoint))
            return endpoint
        return register

sys.modules['fastapi'] = types.SimpleNamespace(APIRouter=FakeAPIRouter)
root = Path({str(root)!r})
api_file = root / 'dashboard' / 'plugin_api.py'
spec = importlib.util.spec_from_file_location('brave_dashboard_api_test', api_file)
assert 'hermes_brave_search' not in sys.modules
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
route = next(route for route in module.router.routes if route.path == '/search')
package = sys.modules['hermes_brave_search']
assert Path(package.__file__).resolve().parent == root / 'src' / 'hermes_brave_search'
assert not route.endpoint.__code__.co_flags & 0x80
"""

    subprocess.run([sys.executable, "-c", script], check=True)
