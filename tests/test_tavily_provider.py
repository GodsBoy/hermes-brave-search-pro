from __future__ import annotations

import sys
import types

import pytest

from hermes_brave_search import TavilyExtractProvider


def _install_bundled_provider(monkeypatch, rows):
    calls = []

    class FakeTavilyWebSearchProvider:
        def __init__(self):
            calls.append(("init",))

        def extract(self, urls, **kwargs):
            calls.append(("extract", urls, kwargs))
            return rows

    bundled = types.ModuleType("plugins.web.tavily.provider")
    bundled.TavilyWebSearchProvider = FakeTavilyWebSearchProvider
    monkeypatch.setitem(sys.modules, "plugins.web.tavily.provider", bundled)
    return calls


def test_provider_is_keyed_and_extract_only(monkeypatch):
    _install_bundled_provider(monkeypatch, [])
    state = {"value": None}
    monkeypatch.setattr(
        "hermes_brave_search.tavily._get_env_value",
        lambda key: state["value"],
    )
    provider = TavilyExtractProvider()

    assert provider.name == "tavily"
    assert provider.display_name == "Tavily Extract"
    assert provider.supports_search() is False
    assert provider.supports_extract() is True
    assert provider.is_available() is False

    state["value"] = "scoped-tavily-key"

    assert provider.is_available() is True


def test_extract_requires_scope_safe_key_before_constructing_bundled_provider(
    monkeypatch,
):
    calls = _install_bundled_provider(monkeypatch, [])
    monkeypatch.setattr(
        "hermes_brave_search.tavily._get_env_value", lambda key: None
    )
    provider = TavilyExtractProvider()
    urls = ["https://example.com/a", "https://example.com/b"]

    result = provider.extract(urls)

    assert [row["url"] for row in result] == urls
    assert {row["error"] for row in result} == {"TAVILY_API_KEY is required"}
    assert calls == []


def test_extract_fails_closed_when_scope_safe_key_lookup_raises(monkeypatch):
    calls = _install_bundled_provider(monkeypatch, [])

    def fail_closed(key):
        raise RuntimeError(f"unscoped secret: {key}")

    monkeypatch.setattr("hermes_brave_search.tavily._get_env_value", fail_closed)
    provider = TavilyExtractProvider()
    urls = ["https://example.com/a"]

    with pytest.raises(RuntimeError, match="unscoped secret: TAVILY_API_KEY"):
        provider.extract(urls)

    assert calls == []


def test_extract_delegates_kwargs_and_normalizes_mixed_duplicate_missing_rows(
    monkeypatch,
):
    urls = [
        "https://example.com/repeated",
        "https://example.com/failure",
        "https://example.com/repeated",
        "https://example.com/missing",
    ]
    rows = [
        {
            "url": "https://example.com/failure",
            "error": "Unable to extract",
        },
        {
            "url": "https://example.com/repeated",
            "raw_content": "First",
            "title": "First title",
        },
        {
            "url": "https://example.com/repeated",
            "content": "Second",
        },
        {"url": "https://example.com/unrequested", "raw_content": "Ignore"},
    ]
    calls = _install_bundled_provider(monkeypatch, rows)
    monkeypatch.setattr(
        "hermes_brave_search.tavily._get_env_value", lambda key: "scoped-key"
    )

    result = TavilyExtractProvider().extract(
        urls, format="markdown", max_chars=100, ignored_option=True
    )

    assert calls == [
        ("init",),
        (
            "extract",
            urls,
            {"format": "markdown", "max_chars": 100, "ignored_option": True},
        ),
    ]
    assert [row["url"] for row in result] == urls
    assert [row.get("content", "") for row in result] == [
        "First",
        "",
        "Second",
        "",
    ]
    assert result[0]["metadata"] == {}
    assert result[1]["error"] == "Tavily could not extract this URL"
    assert result[3]["error"] == "Tavily returned no result for this URL"


def test_extract_normalizes_invalid_delegated_response(monkeypatch):
    calls = _install_bundled_provider(monkeypatch, {"results": []})
    monkeypatch.setattr(
        "hermes_brave_search.tavily._get_env_value", lambda key: "scoped-key"
    )

    result = TavilyExtractProvider().extract(["https://example.com/a"])

    assert result[0]["error"] == "Tavily returned an invalid response"
    assert len(calls) == 2


def test_setup_schema_prompts_for_tavily_key(monkeypatch):
    _install_bundled_provider(monkeypatch, [])
    schema = TavilyExtractProvider().get_setup_schema()

    assert schema == {
        "name": "Tavily Extract",
        "badge": "pro",
        "tag": "Keyed Tavily extraction for Hermes web_extract.",
        "env_vars": [
            {
                "key": "TAVILY_API_KEY",
                "prompt": "Tavily API key",
                "url": "https://app.tavily.com/",
                "secret": True,
            }
        ],
    }


def test_provider_requires_bundled_tavily(monkeypatch):
    monkeypatch.setitem(sys.modules, "plugins.web.tavily.provider", None)

    with pytest.raises(
        RuntimeError,
        match="Hermes v0.21.0 or newer with bundled web-tavily is required",
    ):
        TavilyExtractProvider()
