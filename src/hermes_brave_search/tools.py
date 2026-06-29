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
    limit = params.get("limit", 5)

    if mode not in BRAVE_SEARCH_MODES:
        return json.dumps(
            {"success": False, "error": f"Unsupported Brave search mode: {mode}"}
        )

    from .client import BraveSearchClient

    result = BraveSearchClient().search(
        query=query,
        mode=mode,
        limit=limit,
        max_tokens=params.get("max_tokens"),
        max_urls=params.get("max_urls"),
        context_threshold_mode=params.get("context_threshold_mode"),
    )
    return json.dumps(result, ensure_ascii=False)
