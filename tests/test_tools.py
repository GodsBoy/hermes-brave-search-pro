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
        "context",
        "images",
        "news",
        "videos",
        "discussions",
        "suggest",
        "place",
        "local",
        "pois",
        "descriptions",
        "raw",
    }


def test_tool_rejects_unsupported_mode():
    payload = json.loads(brave_search_tool({"query": "hermes", "mode": "bad"}))

    assert payload["success"] is False
    assert "Unsupported" in payload["error"]


def test_tool_routes_to_client(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5, **kwargs):
        calls.update({"query": query, "mode": mode, "limit": limit, "kwargs": kwargs})
        return {"success": True, "data": {"web": []}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(
        brave_search_tool({"query": "Hermes Agent", "mode": "news", "limit": 7})
    )

    assert payload == {"success": True, "data": {"web": []}}
    assert calls == {
        "query": "Hermes Agent",
        "mode": "news",
        "limit": 7,
        "kwargs": {
            "context_count": None,
            "max_tokens": None,
            "max_urls": None,
            "max_snippets": None,
            "max_tokens_per_url": None,
            "max_snippets_per_url": None,
            "context_threshold_mode": None,
            "freshness": None,
            "country": None,
            "search_lang": None,
            "goggles": None,
            "spellcheck": None,
            "enable_local": None,
            "enable_source_metadata": None,
            "loc_lat": None,
            "loc_long": None,
            "loc_timezone": None,
            "loc_city": None,
            "loc_state": None,
            "loc_state_name": None,
            "loc_country": None,
            "loc_postal_code": None,
            "latitude": None,
            "longitude": None,
            "location": None,
            "radius": None,
            "count": None,
            "ui_lang": None,
            "units": None,
            "safesearch": None,
            "geoloc": None,
            "ids": None,
        },
    }


def test_tool_defaults_to_both_mode(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5, **kwargs):
        calls.update({"query": query, "mode": mode, "limit": limit, "kwargs": kwargs})
        return {"success": True, "data": {"web": [], "llm_context": []}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(brave_search_tool({"query": "Hermes Agent"}))

    assert payload["success"] is True
    assert calls == {
        "query": "Hermes Agent",
        "mode": "both",
        "limit": None,
        "kwargs": {
            "context_count": None,
            "max_tokens": None,
            "max_urls": None,
            "max_snippets": None,
            "max_tokens_per_url": None,
            "max_snippets_per_url": None,
            "context_threshold_mode": None,
            "freshness": None,
            "country": None,
            "search_lang": None,
            "goggles": None,
            "spellcheck": None,
            "enable_local": None,
            "enable_source_metadata": None,
            "loc_lat": None,
            "loc_long": None,
            "loc_timezone": None,
            "loc_city": None,
            "loc_state": None,
            "loc_state_name": None,
            "loc_country": None,
            "loc_postal_code": None,
            "latitude": None,
            "longitude": None,
            "location": None,
            "radius": None,
            "count": None,
            "ui_lang": None,
            "units": None,
            "safesearch": None,
            "geoloc": None,
            "ids": None,
        },
    }


def test_tool_passes_context_options_to_client(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5, **kwargs):
        calls.update({"query": query, "mode": mode, "limit": limit, "kwargs": kwargs})
        return {"success": True, "data": {"llm_context": []}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(
        brave_search_tool(
            {
                "query": "Hermes Agent",
                "mode": "context",
                "limit": 4,
                "context_count": 20,
                "max_tokens": 4096,
                "max_urls": 8,
                "max_snippets": 12,
                "max_tokens_per_url": 2048,
                "max_snippets_per_url": 6,
                "context_threshold_mode": "strict",
                "freshness": "pw",
                "country": "ZA",
                "search_lang": "en",
                "goggles": ["https://example.test/goggle"],
                "spellcheck": False,
                "enable_local": True,
                "enable_source_metadata": True,
                "loc_city": "Cape Town",
                "loc_country": "ZA",
            }
        )
    )

    assert payload == {"success": True, "data": {"llm_context": []}}
    assert calls == {
        "query": "Hermes Agent",
        "mode": "context",
        "limit": 4,
        "kwargs": {
            "context_count": 20,
            "max_tokens": 4096,
            "max_urls": 8,
            "max_snippets": 12,
            "max_tokens_per_url": 2048,
            "max_snippets_per_url": 6,
            "context_threshold_mode": "strict",
            "freshness": "pw",
            "country": "ZA",
            "search_lang": "en",
            "goggles": ["https://example.test/goggle"],
            "spellcheck": False,
            "enable_local": True,
            "enable_source_metadata": True,
            "loc_lat": None,
            "loc_long": None,
            "loc_timezone": None,
            "loc_city": "Cape Town",
            "loc_state": None,
            "loc_state_name": None,
            "loc_country": "ZA",
            "loc_postal_code": None,
            "latitude": None,
            "longitude": None,
            "location": None,
            "radius": None,
            "count": None,
            "ui_lang": None,
            "units": None,
            "safesearch": None,
            "geoloc": None,
            "ids": None,
        },
    }


def test_schema_lists_context_controls():
    props = BRAVE_SEARCH_SCHEMA["parameters"]["properties"]

    for key in {
        "context_count",
        "max_tokens",
        "max_urls",
        "max_snippets",
        "max_tokens_per_url",
        "max_snippets_per_url",
        "context_threshold_mode",
        "freshness",
        "country",
        "search_lang",
        "goggles",
        "spellcheck",
        "enable_local",
        "enable_source_metadata",
        "loc_city",
        "loc_country",
        "latitude",
        "longitude",
        "location",
        "radius",
        "count",
        "ui_lang",
        "units",
        "safesearch",
        "geoloc",
        "ids",
    }:
        assert key in props
    assert "context_count" in props["max_urls"]["description"]
    assert props["count"]["maximum"] == 100


def test_tool_passes_place_options_to_client(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5, **kwargs):
        calls.update({"query": query, "mode": mode, "limit": limit, "kwargs": kwargs})
        return {"success": True, "data": {"places": {"results": []}}}

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    payload = json.loads(
        brave_search_tool(
            {
                "query": "coffee shops",
                "mode": "place",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "location": "san francisco ca united states",
                "radius": 1000,
                "count": 50,
                "country": "US",
                "search_lang": "en",
                "ui_lang": "en-US",
                "units": "metric",
                "safesearch": "moderate",
                "geoloc": "37.7749,-122.4194",
                "ids": ["loc123"],
            }
        )
    )

    assert payload == {"success": True, "data": {"places": {"results": []}}}
    assert calls["query"] == "coffee shops"
    assert calls["mode"] == "place"
    assert calls["kwargs"]["latitude"] == 37.7749
    assert calls["kwargs"]["longitude"] == -122.4194
    assert calls["kwargs"]["location"] == "san francisco ca united states"
    assert calls["kwargs"]["radius"] == 1000
    assert calls["kwargs"]["count"] == 50
    assert calls["kwargs"]["ui_lang"] == "en-US"
    assert calls["kwargs"]["units"] == "metric"
    assert calls["kwargs"]["safesearch"] == "moderate"
    assert calls["kwargs"]["geoloc"] == "37.7749,-122.4194"
    assert calls["kwargs"]["ids"] == ["loc123"]
