from __future__ import annotations

import json

from hermes_brave_search.schemas import BRAVE_SEARCH_MODES, BRAVE_SEARCH_SCHEMA
from hermes_brave_search.tools import brave_search_tool


def test_schema_lists_all_supported_modes():
    mode_schema = BRAVE_SEARCH_SCHEMA["parameters"]["properties"]["mode"]

    assert mode_schema["enum"] == BRAVE_SEARCH_MODES
    assert set(mode_schema["enum"]) == {
        "both",
        "web",
        "llm",
        "images",
        "news",
        "videos",
        "discussions",
        "suggest",
        "raw",
    }


def test_tool_rejects_unsupported_mode():
    payload = json.loads(brave_search_tool({"query": "hermes", "mode": "bad"}))

    assert payload["success"] is False
    assert "Unsupported" in payload["error"]


def test_tool_routes_to_client(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5):
        calls.update({"query": query, "mode": mode, "limit": limit})
        return {"success": True, "data": {"web": []}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(
        brave_search_tool({"query": "Hermes Agent", "mode": "news", "limit": 7})
    )

    assert payload == {"success": True, "data": {"web": []}}
    assert calls == {"query": "Hermes Agent", "mode": "news", "limit": 7}


def test_tool_defaults_to_both_mode(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5):
        calls.update({"query": query, "mode": mode, "limit": limit})
        return {"success": True, "data": {"web": [], "llm_context": []}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(brave_search_tool({"query": "Hermes Agent"}))

    assert payload["success"] is True
    assert calls == {"query": "Hermes Agent", "mode": "both", "limit": 5}
