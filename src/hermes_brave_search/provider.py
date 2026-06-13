"""Hermes web-search provider for Brave Search Pro."""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised inside Hermes, shimmed in package tests.
    from agent.web_search_provider import WebSearchProvider
except ImportError:  # pragma: no cover

    class WebSearchProvider:  # type: ignore[no-redef]
        """Small compatibility shim for local package tests outside Hermes."""

        @property
        def display_name(self) -> str:
            return self.name

        def supports_search(self) -> bool:
            return True

        def supports_extract(self) -> bool:
            return False


from .constants import BRAVE_API_KEY_ENV


class BraveProSearchProvider(WebSearchProvider):
    """Search-only Brave Search Pro provider for Hermes `web_search`."""

    @property
    def name(self) -> str:
        return "brave-pro"

    @property
    def display_name(self) -> str:
        return "Brave Search Pro"

    def is_available(self) -> bool:
        from .client import BraveSearchClient

        return BraveSearchClient().resolved_api_key() is not None

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        from .client import BraveSearchClient

        result = BraveSearchClient().search(query=query, mode="web", limit=limit)
        if not result.get("success"):
            return result

        data = result.get("data", {})
        return {"success": True, "data": {"web": data.get("web", [])}}

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "pro",
            "tag": (
                "Brave-backed discovery for Hermes web_search. "
                "Pair with Tavily for web_extract."
            ),
            "env_vars": [
                {
                    "key": BRAVE_API_KEY_ENV,
                    "prompt": "Brave Search API key",
                    "url": "https://brave.com/search/api/",
                    "secret": True,
                }
            ],
        }
