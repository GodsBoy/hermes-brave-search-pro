from __future__ import annotations

import httpx

from hermes_brave_search.client import (
    BraveSearchClient,
    clamp_context_limit,
    clamp_context_tokens,
    clamp_limit,
)
from hermes_brave_search.constants import (
    BRAVE_LLM_CONTEXT_ENDPOINT,
    BRAVE_SEARCH_ENDPOINT,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("GET", "https://example.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


def test_clamp_limit_bounds_values():
    assert clamp_limit(0) == 1
    assert clamp_limit(99) == 20
    assert clamp_limit("bad") == 5
    assert clamp_context_limit(0) == 1
    assert clamp_context_limit(99) == 50
    assert clamp_context_tokens(1) == 1024
    assert clamp_context_tokens(100_000) == 32768
    assert clamp_context_tokens("bad") == 8192


def test_normalises_web_and_llm_context():
    payload = {
        "web": {
            "results": [
                {
                    "title": "Hermes Agent",
                    "url": "https://hermes-agent.nousresearch.com/docs",
                    "description": "Docs",
                }
            ]
        },
        "summarizer": {
            "results": [
                {
                    "title": "Plugin docs",
                    "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins",
                    "snippets": ["Plugins add tools and backends."],
                }
            ]
        },
    }

    result = BraveSearchClient(api_key="key").normalise_payload(payload, mode="both")

    assert result == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "Hermes Agent",
                    "url": "https://hermes-agent.nousresearch.com/docs",
                    "description": "Docs",
                    "position": 1,
                }
            ],
            "llm_context": [
                {
                    "title": "Plugin docs",
                    "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/plugins",
                    "snippets": ["Plugins add tools and backends."],
                }
            ],
        },
    }


def test_normalises_dedicated_llm_context_payload():
    payload = {
        "grounding": {
            "generic": [
                {
                    "url": "https://example.com/page",
                    "title": "Page Title",
                    "snippets": ["Relevant extracted chunk"],
                }
            ],
            "poi": {
                "name": "Coffee Shop",
                "url": "https://coffee.example",
                "snippets": "Open now",
            },
            "map": [
                {
                    "name": "Map Place",
                    "url": "https://map.example",
                    "snippets": [{"text": "Structured chunk"}],
                }
            ],
        },
        "sources": {
            "https://coffee.example": {"title": "Coffee Shop Source"},
            "https://map.example": {"title": "Map Source"},
        },
    }

    result = BraveSearchClient(api_key="key").normalise_payload(payload, mode="context")

    assert result == {
        "success": True,
        "data": {
            "llm_context": [
                {
                    "title": "Page Title",
                    "url": "https://example.com/page",
                    "snippets": ["Relevant extracted chunk"],
                },
                {
                    "title": "Coffee Shop",
                    "url": "https://coffee.example",
                    "snippets": ["Open now"],
                },
                {
                    "title": "Map Place",
                    "url": "https://map.example",
                    "snippets": [{"text": "Structured chunk"}],
                },
            ]
        },
    }


def test_search_returns_structured_error_without_key(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)

    result = BraveSearchClient().search("hermes")

    assert result["success"] is False
    assert "BRAVE_SEARCH_API_KEY" in result["error"]


def test_search_handles_http_failures(monkeypatch):
    def fake_get(*args, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search("hermes", mode="web")

    assert result == {"success": False, "error": "timeout"}


def test_normalise_payload_tolerates_malformed_shapes():
    client = BraveSearchClient(api_key="key")

    assert client.normalise_payload([], mode="both") == {
        "success": True,
        "data": {"web": [], "llm_context": []},
    }
    assert client.normalise_payload({"web": None}, mode="web") == {
        "success": True,
        "data": {"web": []},
    }
    assert client.normalise_payload({"web": []}, mode="web") == {
        "success": True,
        "data": {"web": []},
    }
    assert client.normalise_payload({"summarizer": None}, mode="llm") == {
        "success": True,
        "data": {"llm_context": []},
    }
    assert client.normalise_payload({"grounding": None}, mode="context") == {
        "success": True,
        "data": {"llm_context": []},
    }
    assert client.normalise_payload({"news": None}, mode="news") == {
        "success": True,
        "data": {"news": []},
    }
    assert client.normalise_payload({"suggestions": {}}, mode="suggest") == {
        "success": True,
        "data": {"suggestions": []},
    }


def test_search_calls_web_and_dedicated_context_for_both_mode(monkeypatch):
    calls = []

    def fake_get(url, params, headers, timeout):
        calls.append(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        if url == BRAVE_SEARCH_ENDPOINT:
            return FakeResponse({"web": {"results": []}})
        if url == BRAVE_LLM_CONTEXT_ENDPOINT:
            return FakeResponse(
                {
                    "grounding": {
                        "generic": [
                            {
                                "title": "Context",
                                "url": "https://example.test",
                                "snippets": ["Extracted context"],
                            }
                        ]
                    },
                    "sources": {},
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search(
        "hermes",
        mode="both",
        limit=99,
        max_tokens=100_000,
        max_urls=99,
        context_threshold_mode="strict",
    )

    assert result == {
        "success": True,
        "data": {
            "web": [],
            "llm_context": [
                {
                    "title": "Context",
                    "url": "https://example.test",
                    "snippets": ["Extracted context"],
                }
            ],
        },
    }
    assert calls[0]["url"] == BRAVE_SEARCH_ENDPOINT
    assert calls[0]["params"] == {"q": "hermes", "count": 20}
    assert calls[1]["url"] == BRAVE_LLM_CONTEXT_ENDPOINT
    assert calls[1]["params"] == {
        "q": "hermes",
        "count": 50,
        "maximum_number_of_urls": 50,
        "maximum_number_of_tokens": 32768,
        "context_threshold_mode": "strict",
    }
    assert calls[0]["headers"]["X-Subscription-Token"] == "key"
    assert calls[1]["headers"]["X-Subscription-Token"] == "key"


def test_search_calls_dedicated_llm_context_for_llm_mode(monkeypatch):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update({"url": url, "params": params, "headers": headers})
        return FakeResponse(
            {
                "grounding": {
                    "generic": [
                        {
                            "title": "Context",
                            "url": "https://example.test",
                            "snippets": ["Extracted context"],
                        }
                    ]
                },
                "sources": {},
            }
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search("hermes", mode="llm", limit=3)

    assert result == {
        "success": True,
        "data": {
            "llm_context": [
                {
                    "title": "Context",
                    "url": "https://example.test",
                    "snippets": ["Extracted context"],
                }
            ]
        },
    }
    assert seen["url"] == BRAVE_LLM_CONTEXT_ENDPOINT
    assert seen["params"] == {
        "q": "hermes",
        "count": 3,
        "maximum_number_of_urls": 3,
    }


def test_search_rejects_invalid_context_threshold(monkeypatch):
    called = False

    def fake_get(*args, **kwargs):
        nonlocal called
        called = True
        return FakeResponse({})

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search(
        "hermes", mode="context", context_threshold_mode="wide-open"
    )

    assert result == {
        "success": False,
        "error": "Unsupported context_threshold_mode: wide-open",
    }
    assert called is False
