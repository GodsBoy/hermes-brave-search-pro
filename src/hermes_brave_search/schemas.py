"""Tool schema for the advanced Brave search tool."""

from __future__ import annotations

from .constants import BRAVE_SEARCH_MODES

BRAVE_SEARCH_SCHEMA = {
    "name": "brave_search",
    "description": (
        "Search Brave Search Pro. Use mode='both' for web results plus Brave "
        "LLM Context API chunks, or choose web, llm/context, images, news, "
        "videos, discussions, suggest, or raw."
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
            "max_tokens": {
                "type": "integer",
                "minimum": 1024,
                "maximum": 32768,
                "description": (
                    "Optional Brave LLM Context API token budget for "
                    "mode='both', 'llm', or 'context'."
                ),
            },
            "max_urls": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "description": (
                    "Optional maximum number of URLs returned by Brave LLM "
                    "Context API. Defaults to the requested limit."
                ),
            },
            "context_threshold_mode": {
                "type": "string",
                "enum": ["strict", "balanced", "lenient", "disabled"],
                "description": (
                    "Optional relevance threshold for Brave LLM Context API."
                ),
            },
        },
        "required": ["query"],
    },
}
