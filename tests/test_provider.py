from __future__ import annotations

import hermes_brave_search
from hermes_brave_search.provider import BraveProSearchProvider


class FakeContext:
    def __init__(self):
        self.web_providers = []
        self.tools = []

    def register_web_search_provider(self, provider):
        self.web_providers.append(provider)

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def test_register_adds_provider_and_tool():
    ctx = FakeContext()

    hermes_brave_search.register(ctx)

    assert len(ctx.web_providers) == 1
    assert ctx.web_providers[0].name == "brave-pro"
    assert len(ctx.tools) == 1
    assert ctx.tools[0]["name"] == "brave_search"
    assert ctx.tools[0]["toolset"] == "brave_search"
    assert ctx.tools[0]["requires_env"] == ["BRAVE_SEARCH_API_KEY"]
    assert callable(ctx.tools[0]["check_fn"])


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

    def fake_search(self, query, mode="both", limit=5):
        calls.update({"query": query, "mode": mode, "limit": limit})
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

    assert result == {
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
    assert calls == {"query": "hermes", "mode": "web", "limit": 3}


def test_setup_schema_prompts_for_brave_key():
    schema = BraveProSearchProvider().get_setup_schema()

    assert schema["name"] == "Brave Search Pro"
    assert schema["env_vars"][0]["key"] == "BRAVE_SEARCH_API_KEY"
