"""Tool schema for the advanced Brave search tool."""

from __future__ import annotations

from .constants import BRAVE_SEARCH_MODES

BRAVE_SEARCH_SCHEMA = {
    "name": "brave_search",
    "description": (
        "Search Brave Search Pro. Use mode='both' for web results plus Brave "
        "LLM Context API chunks, or choose web, llm/context, place/local, "
        "pois, descriptions, images, news, videos, discussions, suggest, or raw."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search query to send to Brave. Required for web/media/context "
                    "modes; optional for place/local Explore Mode and unused for "
                    "pois/descriptions."
                ),
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
                "description": (
                    "Maximum web/media result count where supported. For place/local "
                    "modes, use count for values up to 100."
                ),
            },
            "context_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "default": 20,
                "description": (
                    "Number of search results Brave should consider for "
                    "mode='both', 'llm', or 'context'."
                ),
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
                    "Context API. Defaults to context_count."
                ),
            },
            "max_snippets": {
                "type": "integer",
                "minimum": 1,
                "maximum": 256,
                "description": "Optional total Brave LLM Context snippet budget.",
            },
            "max_tokens_per_url": {
                "type": "integer",
                "minimum": 512,
                "maximum": 8192,
                "description": "Optional Brave LLM Context token budget per URL.",
            },
            "max_snippets_per_url": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": "Optional Brave LLM Context snippet budget per URL.",
            },
            "context_threshold_mode": {
                "type": "string",
                "enum": ["strict", "balanced", "lenient", "disabled"],
                "description": (
                    "Optional relevance threshold for Brave LLM Context API."
                ),
            },
            "freshness": {
                "type": "string",
                "description": (
                    "Optional freshness filter: pd, pw, pm, py, or "
                    "YYYY-MM-DDtoYYYY-MM-DD."
                ),
            },
            "country": {
                "type": "string",
                "minLength": 2,
                "maxLength": 2,
                "description": "Optional two-letter country code for Brave results.",
            },
            "search_lang": {
                "type": "string",
                "description": "Optional Brave search language preference.",
            },
            "ui_lang": {
                "type": "string",
                "description": (
                    "Optional UI locale for Brave local/place responses, e.g. en-US."
                ),
            },
            "units": {
                "type": "string",
                "enum": ["metric", "imperial"],
                "description": "Measurement units for Brave local/place results.",
            },
            "safesearch": {
                "type": "string",
                "enum": ["off", "moderate", "strict"],
                "description": "Safe search level for Brave Place Search.",
            },
            "goggles": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 3,
                    },
                ],
                "description": "Optional Brave Goggles URL, definition, or list.",
            },
            "spellcheck": {
                "type": "boolean",
                "description": "Whether Brave should spellcheck the query.",
            },
            "enable_local": {
                "type": "boolean",
                "description": (
                    "Whether Brave should force local recall for LLM Context."
                ),
            },
            "enable_source_metadata": {
                "type": "boolean",
                "description": "Whether Brave should enrich LLM Context sources.",
            },
            "loc_lat": {
                "type": "number",
                "description": (
                    "Optional latitude for Brave location-aware context or local "
                    "detail calls."
                ),
            },
            "loc_long": {
                "type": "number",
                "description": (
                    "Optional longitude for Brave location-aware context or local "
                    "detail calls."
                ),
            },
            "loc_timezone": {
                "type": "string",
                "description": "Optional IANA timezone for Brave location headers.",
            },
            "loc_city": {
                "type": "string",
                "description": "Optional city for Brave location-aware context.",
            },
            "loc_state": {
                "type": "string",
                "description": (
                    "Optional state or region code for Brave location headers."
                ),
            },
            "loc_state_name": {
                "type": "string",
                "description": (
                    "Optional state or region name for Brave location headers."
                ),
            },
            "loc_country": {
                "type": "string",
                "minLength": 2,
                "maxLength": 2,
                "description": "Optional country code for Brave location headers.",
            },
            "loc_postal_code": {
                "type": "string",
                "description": "Optional postal code for Brave location headers.",
            },
            "latitude": {
                "type": "number",
                "minimum": -90,
                "maximum": 90,
                "description": (
                    "Latitude for mode='place' or mode='local'. Use with longitude."
                ),
            },
            "longitude": {
                "type": "number",
                "minimum": -180,
                "maximum": 180,
                "description": (
                    "Longitude for mode='place' or mode='local'. Use with latitude."
                ),
            },
            "location": {
                "type": "string",
                "description": (
                    "Location string for mode='place' or mode='local', e.g. "
                    "'san francisco ca united states' or 'tokyo japan'."
                ),
            },
            "radius": {
                "type": "number",
                "minimum": 0,
                "description": "Optional Place Search radius bias in metres.",
            },
            "count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "description": "Number of Place Search results to request, 1 to 100.",
            },
            "geoloc": {
                "type": "string",
                "description": (
                    "Optional Brave geoloc value for Place Search, formatted as "
                    "latitude x longitude."
                ),
            },
            "ids": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 20,
                    },
                ],
                "description": (
                    "Temporary Brave POI id or ids for mode='pois' or "
                    "mode='descriptions'. POI ids expire after roughly 8 hours."
                ),
            },
        },
        "required": [],
    },
}
