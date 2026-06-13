"""Tool schema for the advanced Brave search tool."""

from __future__ import annotations

from .constants import BRAVE_SEARCH_MODES

BRAVE_SEARCH_SCHEMA = {
    "name": "brave_search",
    "description": (
        "Search Brave Search Pro. Use mode='both' for web results plus Brave "
        "answer context, or choose web, llm, images, news, videos, "
        "discussions, suggest, or raw."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to send to Brave Search Pro.",
            },
            "mode": {
                "type": "string",
                "enum": BRAVE_SEARCH_MODES,
                "default": "both",
                "description": "Brave search mode to use.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "Maximum result count where supported.",
            },
        },
        "required": ["query"],
    },
}
