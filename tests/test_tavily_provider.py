from __future__ import annotations

import httpx

from hermes_brave_search.tavily import TavilyExtractProvider


class FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_provider_is_keyed_and_extract_only(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    provider = TavilyExtractProvider()

    assert provider.name == "tavily"
    assert provider.supports_search() is False
    assert provider.supports_extract() is True
    assert provider.is_available() is False

    monkeypatch.setenv("TAVILY_API_KEY", "   ")

    assert provider.is_available() is False

    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")

    assert provider.is_available() is True


def test_extract_uses_fixed_endpoint_and_bearer_header(monkeypatch):
    calls = []
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(
            {
                "results": [
                    {
                        "url": "https://example.com/a",
                        "raw_content": "Alpha",
                    }
                ],
                "failed_results": [],
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    results = TavilyExtractProvider().extract(
        ["https://example.com/a"],
        format="markdown",
        ignored_option=True,
    )

    assert results == [
        {
            "url": "https://example.com/a",
            "title": "",
            "content": "Alpha",
            "raw_content": "Alpha",
            "metadata": {},
        }
    ]
    assert calls[0][0] == "https://api.tavily.com/extract"
    assert calls[0][1]["headers"] == {
        "Authorization": "Bearer tavily-test-key",
        "Content-Type": "application/json",
    }
    assert calls[0][1]["json"] == {
        "urls": ["https://example.com/a"],
        "include_images": False,
        "format": "markdown",
    }
    assert "tavily-test-key" not in repr(calls[0][1]["json"])


def test_extract_preserves_mixed_results_and_duplicate_positions(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    urls = [
        "https://example.com/repeated",
        "https://example.com/failure",
        "https://example.com/repeated",
    ]

    monkeypatch.setattr(
        httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse(
            {
                "results": [
                    {
                        "url": "https://example.com/repeated",
                        "raw_content": "First",
                    },
                    {
                        "url": "https://example.com/repeated",
                        "raw_content": "Second",
                    },
                ],
                "failed_results": [
                    {
                        "url": "https://example.com/failure",
                        "error": "Unable to extract",
                    }
                ],
            }
        ),
    )

    results = TavilyExtractProvider().extract(urls)

    assert [result["url"] for result in results] == urls
    assert [result.get("content", "") for result in results] == [
        "First",
        "",
        "Second",
    ]
    assert results[1]["error"] == "Tavily could not extract this URL"


def test_extract_returns_one_safe_error_per_url_without_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    results = TavilyExtractProvider().extract(
        ["https://example.com/a", "https://example.com/b"]
    )

    assert [result["url"] for result in results] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert {result["error"] for result in results} == {
        "TAVILY_API_KEY is required"
    }


def test_extract_normalizes_http_timeout_transport_and_json_failures(
    monkeypatch,
):
    secret = "tavily-secret-sentinel"
    monkeypatch.setenv("TAVILY_API_KEY", secret)
    provider = TavilyExtractProvider()
    url = "https://example.com/a"

    cases = [
        (FakeResponse({}, status_code=401), "Tavily authentication failed (HTTP 401)"),
        (FakeResponse({}, status_code=429), "Tavily rate limit reached (HTTP 429)"),
        (FakeResponse({}, status_code=432), "Tavily quota is unavailable (HTTP 432)"),
        (FakeResponse({}, status_code=500), "Tavily service failed (HTTP 500)"),
        (FakeResponse(ValueError(secret)), "Tavily returned an invalid response"),
        (httpx.TimeoutException(secret), "Tavily extract request timed out"),
        (httpx.TransportError(secret), "Tavily extract request failed"),
    ]

    for outcome, expected_error in cases:
        def fake_post(*_args, _outcome=outcome, **_kwargs):
            if isinstance(_outcome, Exception):
                raise _outcome
            return _outcome

        monkeypatch.setattr(httpx, "post", fake_post)

        result = provider.extract([url])

        assert result[0]["error"] == expected_error
        assert secret not in repr(result)


def test_extract_fills_missing_response_rows(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *_args, **_kwargs: FakeResponse(
            {"results": [], "failed_results": []}
        ),
    )

    result = TavilyExtractProvider().extract(["https://example.com/missing"])

    assert result == [
        {
            "url": "https://example.com/missing",
            "title": "",
            "content": "",
            "raw_content": "",
            "error": "Tavily returned no result for this URL",
        }
    ]
