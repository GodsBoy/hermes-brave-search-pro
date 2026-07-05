from __future__ import annotations

import httpx

from hermes_brave_search.client import (
    DEFAULT_CONTEXT_COUNT,
    BraveSearchClient,
    clamp_context_limit,
    clamp_context_snippets,
    clamp_context_tokens,
    clamp_context_tokens_per_url,
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
    assert clamp_context_snippets(0) == 1
    assert clamp_context_snippets(999) == 256
    assert clamp_context_tokens_per_url(1) == 512
    assert clamp_context_tokens_per_url(100_000) == 8192


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
            {
                "method": "GET",
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if url == BRAVE_SEARCH_ENDPOINT:
            return FakeResponse({"web": {"results": []}})
        raise AssertionError(f"unexpected url: {url}")

    def fake_post(url, json, headers, timeout):
        calls.append(
            {
                "method": "POST",
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
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
    monkeypatch.setattr(httpx, "post", fake_post)

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
    assert calls[0]["method"] == "GET"
    assert calls[0]["url"] == BRAVE_SEARCH_ENDPOINT
    assert calls[0]["params"] == {"q": "hermes", "count": 20}
    assert calls[1]["method"] == "POST"
    assert calls[1]["url"] == BRAVE_LLM_CONTEXT_ENDPOINT
    assert calls[1]["json"] == {
        "q": "hermes",
        "count": DEFAULT_CONTEXT_COUNT,
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
        "count": DEFAULT_CONTEXT_COUNT,
        "maximum_number_of_urls": DEFAULT_CONTEXT_COUNT,
    }


def test_search_passes_context_options_with_post(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout):
        seen.update({"url": url, "json": json, "headers": headers, "timeout": timeout})
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

    def fake_get(*args, **kwargs):
        raise AssertionError("advanced context request should use POST")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    result = BraveSearchClient(api_key="key").search(
        "hermes",
        mode="context",
        context_count=99,
        max_tokens=4096,
        max_urls=4,
        max_snippets=999,
        max_tokens_per_url=100_000,
        max_snippets_per_url=150,
        context_threshold_mode="lenient",
        freshness="pw",
        country="za",
        search_lang="en",
        goggles=["https://example.test/goggle"],
        spellcheck=False,
        enable_local=True,
        enable_source_metadata=True,
        loc_city="Cape Town",
        loc_country="ZA",
    )

    assert result["success"] is True
    assert seen["url"] == BRAVE_LLM_CONTEXT_ENDPOINT
    assert seen["json"] == {
        "q": "hermes",
        "count": 50,
        "maximum_number_of_urls": 4,
        "maximum_number_of_tokens": 4096,
        "maximum_number_of_snippets": 256,
        "maximum_number_of_tokens_per_url": 8192,
        "maximum_number_of_snippets_per_url": 100,
        "context_threshold_mode": "lenient",
        "freshness": "pw",
        "country": "ZA",
        "search_lang": "en",
        "goggles": ["https://example.test/goggle"],
        "spellcheck": False,
        "enable_local": True,
        "enable_source_metadata": True,
    }
    assert seen["headers"]["Content-Type"] == "application/json"
    assert seen["headers"]["X-Loc-City"] == "Cape Town"
    assert seen["headers"]["X-Loc-Country"] == "ZA"


def test_simple_context_request_still_uses_get(monkeypatch):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update({"url": url, "params": params, "headers": headers})
        return FakeResponse({"grounding": {"generic": []}, "sources": {}})

    def fake_post(*args, **kwargs):
        raise AssertionError("simple context request should use GET")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    result = BraveSearchClient(api_key="key").search("hermes", mode="context")

    assert result == {"success": True, "data": {"llm_context": []}}
    assert seen["url"] == BRAVE_LLM_CONTEXT_ENDPOINT
    assert seen["params"] == {
        "q": "hermes",
        "count": DEFAULT_CONTEXT_COUNT,
        "maximum_number_of_urls": DEFAULT_CONTEXT_COUNT,
    }


def test_context_numeric_zero_values_are_clamped(monkeypatch):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update({"url": url, "params": params, "headers": headers})
        return FakeResponse({"grounding": {"generic": []}, "sources": {}})

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search(
        "hermes",
        mode="context",
        context_count=0,
        max_urls=0,
    )

    assert result == {"success": True, "data": {"llm_context": []}}
    assert seen["params"] == {
        "q": "hermes",
        "count": 1,
        "maximum_number_of_urls": 1,
    }


def test_retry_transient_status_then_success(monkeypatch):
    calls = 0

    def fake_get(url, params, headers, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            return FakeResponse({"error": "slow down"}, status_code=429)
        return FakeResponse({"web": {"results": []}})

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key", backoff_seconds=0).search(
        "hermes", mode="web"
    )

    assert result == {"success": True, "data": {"web": []}}
    assert calls == 2


def test_does_not_retry_auth_failure(monkeypatch):
    calls = 0

    def fake_get(url, params, headers, timeout):
        nonlocal calls
        calls += 1
        return FakeResponse({"error": "unauthorized"}, status_code=401)

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key", backoff_seconds=0).search(
        "hermes", mode="web"
    )

    assert result["success"] is False
    assert calls == 1


def test_search_rejects_invalid_context_values(monkeypatch):
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

    result = BraveSearchClient(api_key="key").search(
        "hermes", mode="context", freshness="yesterday"
    )

    assert result == {
        "success": False,
        "error": "Unsupported freshness: yesterday",
    }
    assert called is False
