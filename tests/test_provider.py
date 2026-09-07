from __future__ import annotations

import httpx
import pytest

import hermes_brave_search
from hermes_brave_search.provider import BraveProSearchProvider


class FakeContext:
    def __init__(self):
        self.web_providers = []
        self.tools = []
        self.events = []

    def register_web_search_provider(self, provider):
        self.events.append(("provider", provider.name))
        self.web_providers.append(provider)

    def register_tool(self, **kwargs):
        self.events.append(("tool", kwargs["name"]))
        self.tools.append(kwargs)


class CapabilityContext(FakeContext):
    def __init__(self, allowed: bool):
        super().__init__()
        self.allowed = allowed
        self.capability_checks = []

    def has_capability(self, capability):
        self.capability_checks.append(capability)
        return self.allowed


class RejectingContext(FakeContext):
    def register_tool(self, **kwargs):
        self.events.append(("tool", kwargs["name"]))
        raise PermissionError("tool override denied")


def test_register_adds_brave_provider_and_tool_after_successful_registration(
    monkeypatch,
):
    ctx = CapabilityContext(allowed=True)
    compat_observations = []
    monkeypatch.setattr(
        hermes_brave_search,
        "apply_runtime_compat",
        lambda: compat_observations.append(
            [provider.name for provider in ctx.web_providers]
        ),
    )

    hermes_brave_search.register(ctx)

    assert ctx.capability_checks == ["tools.override"]
    assert len(ctx.web_providers) == 1
    assert ctx.web_providers[0].name == "brave-pro"
    assert ctx.web_providers[0].supports_search() is True
    assert ctx.web_providers[0].supports_extract() is False
    assert len(ctx.tools) == 1
    assert ctx.tools[0]["name"] == "brave_search"
    assert ctx.tools[0]["toolset"] == "brave_search"
    assert ctx.tools[0]["requires_env"] == ["BRAVE_SEARCH_API_KEY"]
    assert ctx.tools[0]["emoji"] == "🦁"
    assert ctx.tools[0]["override"] is True
    assert callable(ctx.tools[0]["check_fn"])
    assert ctx.events == [
        ("tool", "brave_search"),
        ("provider", "brave-pro"),
    ]
    assert compat_observations == [["brave-pro"]]


def test_register_skips_only_tool_when_override_is_denied(monkeypatch):
    ctx = CapabilityContext(allowed=False)
    compat_calls = []
    monkeypatch.setattr(
        hermes_brave_search,
        "apply_runtime_compat",
        lambda: compat_calls.append([provider.name for provider in ctx.web_providers]),
    )

    hermes_brave_search.register(ctx)

    assert ctx.capability_checks == ["tools.override"]
    assert ctx.events == [("provider", "brave-pro")]
    assert ctx.tools == []
    assert [provider.name for provider in ctx.web_providers] == ["brave-pro"]
    assert compat_calls == [["brave-pro"]]


def test_register_preserves_legacy_context_registration_behavior(monkeypatch):
    ctx = RejectingContext()
    compat_calls = []
    monkeypatch.setattr(
        hermes_brave_search,
        "apply_runtime_compat",
        lambda: compat_calls.append(True),
    )

    with pytest.raises(PermissionError, match="tool override denied"):
        hermes_brave_search.register(ctx)

    assert ctx.events == [("tool", "brave_search")]
    assert ctx.web_providers == []
    assert compat_calls == []


def test_provider_availability_uses_brave_key(monkeypatch):
    monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    provider = BraveProSearchProvider()

    assert provider.is_available() is False

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "test-key")

    assert provider.is_available() is True


def test_provider_is_search_only():
    provider = BraveProSearchProvider()

    assert provider.supports_search() is True
    assert provider.supports_extract() is False


def test_provider_delegates_to_client(monkeypatch):
    calls = {}

    def fake_search(self, query, mode="both", limit=5, **kwargs):
        calls.update({"query": query, "mode": mode, "limit": limit, **kwargs})
        return {
            "success": True,
            "data": {
                "web": [
                    {
                        "title": "A",
                        "url": "https://a.test",
                        "description": "",
                        "position": 1,
                    }
                ],
                "llm_context": [{"title": "Context", "url": "", "snippets": ["S"]}],
            },
        }

    monkeypatch.setattr(
        "hermes_brave_search.client.BraveSearchClient.search", fake_search
    )

    result = BraveProSearchProvider().search("hermes", limit=3)

    assert {"success": result["success"], "data": {"web": result["data"]["web"]}} == {
        "success": True,
        "data": {
            "web": [
                {
                    "title": "A",
                    "url": "https://a.test",
                    "description": "",
                    "position": 1,
                }
            ],
        },
    }
    assert result["data"]["llm_context"] == [
        {"title": "Context", "url": "", "snippets": ["S"]}
    ]
    assert calls == {
        "query": "hermes",
        "mode": "both",
        "limit": 3,
        "context_count": 5,
        "max_urls": 5,
        "max_tokens": 4096,
        "max_tokens_per_url": 1024,
    }


def test_setup_schema_prompts_for_brave_key():
    schema = BraveProSearchProvider().get_setup_schema()

    assert schema["name"] == "Brave Search Pro"
    assert schema["env_vars"][0]["key"] == "BRAVE_SEARCH_API_KEY"


@pytest.mark.parametrize("failed_endpoint", [None, "context", "web"])
def test_provider_both_requests_and_partial_failure(monkeypatch, failed_endpoint):
    from hermes_brave_search.constants import (
        BRAVE_LLM_CONTEXT_ENDPOINT,
        BRAVE_SEARCH_ENDPOINT,
    )

    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "synthetic-key")
    calls = []

    def respond(method, url, params):
        endpoint = "web" if url == BRAVE_SEARCH_ENDPOINT else "context"
        assert url in {BRAVE_SEARCH_ENDPOINT, BRAVE_LLM_CONTEXT_ENDPOINT}
        calls.append((endpoint, params))
        payload = (
            {
                "web": {
                    "results": [
                        {
                            "title": "A",
                            "url": "https://a.test",
                            "description": "Web result",
                        }
                    ]
                }
            }
            if endpoint == "web"
            else {
                "grounding": {
                    "generic": [
                        {
                            "title": "A",
                            "url": "https://a.test",
                            "snippets": ["Context result"],
                        }
                    ]
                }
            }
        )
        return httpx.Response(
            422 if endpoint == failed_endpoint else 200,
            json=payload,
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(
        httpx, "get", lambda url, params, **kw: respond("GET", url, params)
    )
    monkeypatch.setattr(
        httpx, "post", lambda url, json, **kw: respond("POST", url, json)
    )

    result = BraveProSearchProvider().search("hermes", limit=3)

    assert calls[0] == ("web", {"q": "hermes", "count": 3})
    if failed_endpoint == "web":
        assert result["success"] is False
        assert len(calls) == 1
        assert "422" in result["error"]
    else:
        assert len(calls) == 2
        assert calls[1] == (
            "context",
            {
                "q": "hermes",
                "count": 5,
                "maximum_number_of_urls": 5,
                "maximum_number_of_tokens": 4096,
                "maximum_number_of_tokens_per_url": 1024,
            },
        )
        assert result["success"] is True
        assert result["data"]["web"] == [
            {
                "title": "A",
                "url": "https://a.test",
                "description": "Web result",
                "position": 1,
            }
        ]
        if failed_endpoint == "context":
            assert result["data"]["llm_context"] == []
            assert "422" in result["data"]["llm_context_error"]
        else:
            assert result["data"]["llm_context"][0]["snippets"] == ["Context result"]
            assert "llm_context_error" not in result["data"]
    assert "synthetic-key" not in str(result)
