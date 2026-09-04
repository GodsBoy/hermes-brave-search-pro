"""Hermes Brave Search plugin."""

from __future__ import annotations

from .compat import apply_runtime_compat
from .constants import BRAVE_API_KEY_ENV as _BRAVE_API_KEY_ENV
from .provider import BraveProSearchProvider
from .schemas import BRAVE_SEARCH_SCHEMA
from .tavily import TavilyExtractProvider
from .tools import brave_search_tool

__all__ = ["BraveProSearchProvider", "TavilyExtractProvider", "register"]


def register(ctx) -> None:
    """Register Brave search and the optional advanced Brave tool."""

    brave_provider = BraveProSearchProvider()
    has_capability = getattr(ctx, "has_capability", None)
    if not callable(has_capability) or has_capability("tools.override"):
        ctx.register_tool(
            name="brave_search",
            toolset="brave_search",
            schema=BRAVE_SEARCH_SCHEMA,
            handler=brave_search_tool,
            check_fn=brave_provider.is_available,
            requires_env=[_BRAVE_API_KEY_ENV],
            emoji="🦁",
            override=True,
            description=(
                "Search Brave Search Pro across web, answer context, media, news, "
                "discussions, suggestions, and raw modes."
            ),
        )
    ctx.register_web_search_provider(brave_provider)
    apply_runtime_compat()
