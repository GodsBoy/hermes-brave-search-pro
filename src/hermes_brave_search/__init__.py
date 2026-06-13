"""Hermes Brave Search plugin."""

from __future__ import annotations

from .provider import BraveProSearchProvider
from .schemas import BRAVE_SEARCH_SCHEMA
from .tools import brave_search_tool

__all__ = ["BraveProSearchProvider", "register"]


def register(ctx) -> None:
    """Register the Brave provider and the advanced Brave tool with Hermes."""

    provider = BraveProSearchProvider()
    ctx.register_web_search_provider(provider)
    ctx.register_tool(
        name="brave_search",
        toolset="brave_search",
        schema=BRAVE_SEARCH_SCHEMA,
        handler=brave_search_tool,
        check_fn=provider.is_available,
        requires_env=["BRAVE_SEARCH_API_KEY"],
        description=(
            "Search Brave Search Pro across web, answer context, media, news, "
            "discussions, suggestions, and raw modes."
        ),
    )
