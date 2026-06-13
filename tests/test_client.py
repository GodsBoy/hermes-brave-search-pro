from __future__ import annotations

import httpx

from hermes_brave_search.client import BraveSearchClient, clamp_limit


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

    result = BraveSearchClient(api_key="key").search("hermes")

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
    assert client.normalise_payload({"news": None}, mode="news") == {
        "success": True,
        "data": {"news": []},
    }
    assert client.normalise_payload({"suggestions": {}}, mode="suggest") == {
        "success": True,
        "data": {"suggestions": []},
    }


def test_search_calls_brave_with_summary_for_both_mode(monkeypatch):
    seen = {}

    def fake_get(url, params, headers, timeout):
        seen.update(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        return FakeResponse({"web": {"results": []}, "summarizer": {"results": []}})

    monkeypatch.setattr(httpx, "get", fake_get)

    result = BraveSearchClient(api_key="key").search("hermes", mode="both", limit=99)

    assert result["success"] is True
    assert seen["params"] == {"q": "hermes", "count": 20, "summary": "1"}
    assert seen["headers"]["X-Subscription-Token"] == "key"
