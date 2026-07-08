"""Advanced Brave search Hermes tool handler."""

from __future__ import annotations

import json
from typing import Any

from .constants import BRAVE_SEARCH_MODES


def brave_search_tool(params: dict[str, Any], **kwargs: Any) -> str:
    """Hermes tool handler for Brave-specific search modes."""

    del kwargs
    query = str(params.get("query") or "").strip()
    mode = str(params.get("mode") or "both").strip().lower()
    limit = params.get("limit")

    if mode not in BRAVE_SEARCH_MODES:
        return json.dumps(
            {"success": False, "error": f"Unsupported Brave search mode: {mode}"}
        )

    from .client import BraveSearchClient

    result = BraveSearchClient().search(
        query=query,
        mode=mode,
        limit=limit,
        context_count=params.get("context_count"),
        max_tokens=params.get("max_tokens"),
        max_urls=params.get("max_urls"),
        max_snippets=params.get("max_snippets"),
        max_tokens_per_url=params.get("max_tokens_per_url"),
        max_snippets_per_url=params.get("max_snippets_per_url"),
        context_threshold_mode=params.get("context_threshold_mode"),
        freshness=params.get("freshness"),
        country=params.get("country"),
        search_lang=params.get("search_lang"),
        goggles=params.get("goggles"),
        spellcheck=params.get("spellcheck"),
        enable_local=params.get("enable_local"),
        enable_source_metadata=params.get("enable_source_metadata"),
        loc_lat=params.get("loc_lat"),
        loc_long=params.get("loc_long"),
        loc_timezone=params.get("loc_timezone"),
        loc_city=params.get("loc_city"),
        loc_state=params.get("loc_state"),
        loc_state_name=params.get("loc_state_name"),
        loc_country=params.get("loc_country"),
        loc_postal_code=params.get("loc_postal_code"),
        latitude=params.get("latitude"),
        longitude=params.get("longitude"),
        location=params.get("location"),
        radius=params.get("radius"),
        count=params.get("count"),
        ui_lang=params.get("ui_lang"),
        units=params.get("units"),
        safesearch=params.get("safesearch"),
        geoloc=params.get("geoloc"),
        ids=params.get("ids"),
    )
    return json.dumps(result, ensure_ascii=False)
