"""Brave Search Pro HTTP client and response normalisation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx

from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV, BRAVE_MODE_ENDPOINTS

DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_LIMIT = 20


@dataclass(slots=True)
class BraveSearchClient:
    """Small synchronous client for Brave Search API calls."""

    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    base_headers: dict[str, str] | None = None

    MODE_ENDPOINTS: ClassVar[dict[str, str]] = BRAVE_MODE_ENDPOINTS

    def resolved_api_key(self) -> str | None:
        raw_key = (
            self.api_key
            or os.getenv(BRAVE_API_KEY_ENV)
            or os.getenv(BRAVE_API_KEY_COMPAT_ENV)
        )
        if not raw_key:
            return None
        return raw_key.strip() or None

    def search(self, query: str, mode: str = "both", limit: int = 5) -> dict[str, Any]:
        """Run a Brave search mode and return a JSON-serialisable envelope."""

        mode = (mode or "both").strip().lower()
        if mode not in self.MODE_ENDPOINTS:
            return {
                "success": False,
                "error": f"Unsupported Brave search mode: {mode}",
            }

        if not query or not query.strip():
            return {"success": False, "error": "query is required"}

        api_key = self.resolved_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "BRAVE_SEARCH_API_KEY is required",
            }

        params = self._params_for_mode(query=query, mode=mode, limit=limit)
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
            **(self.base_headers or {}),
        }

        try:
            response = httpx.get(
                self.MODE_ENDPOINTS[mode],
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {"success": False, "error": str(exc)}

        if mode == "raw":
            return {"success": True, "data": payload}

        try:
            return self.normalise_payload(payload, mode=mode)
        except (AttributeError, TypeError, ValueError) as exc:
            return {"success": False, "error": f"Invalid Brave response: {exc}"}

    def normalise_payload(self, payload: Any, mode: str = "both") -> dict[str, Any]:
        """Normalise Brave payloads to stable Hermes-friendly output."""

        mode = (mode or "both").strip().lower()
        if not isinstance(payload, dict):
            payload = {}
        if mode == "suggest":
            return {
                "success": True,
                "data": {"suggestions": self._normalise_suggestions(payload)},
            }

        data: dict[str, Any] = {}

        if mode in {"web", "both", "discussions"}:
            data["web"] = self._normalise_web_results(payload)

        if mode in {"both", "llm"}:
            data["llm_context"] = self._normalise_llm_context(payload)

        if mode == "discussions":
            data["discussions"] = self._normalise_nested_results(payload, "discussions")

        if mode == "news":
            data["news"] = self._normalise_media_results(payload, "news")

        if mode == "images":
            data["images"] = self._normalise_media_results(payload, "images")

        if mode == "videos":
            data["videos"] = self._normalise_media_results(payload, "videos")

        return {"success": True, "data": data}

    def _params_for_mode(self, query: str, mode: str, limit: int) -> dict[str, Any]:
        count = clamp_limit(limit)
        params: dict[str, Any] = {"q": query.strip(), "count": count}
        if mode in {"both", "llm"}:
            params["summary"] = "1"
        if mode == "discussions":
            params["result_filter"] = "discussions"
        return params

    def _normalise_web_results(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        web_payload = payload.get("web")
        if not isinstance(web_payload, dict):
            return []
        raw_results = web_payload.get("results", [])
        if not isinstance(raw_results, list):
            return []
        results = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("url") or ""),
                    "description": str(
                        item.get("description") or item.get("snippet") or ""
                    ),
                    "position": index,
                }
            )
        return results

    def _normalise_llm_context(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = (
            nested_results(payload, "summarizer")
            or payload.get("llm_context")
            or nested_results(payload, "infobox")
            or []
        )
        if isinstance(candidates, dict):
            candidates = [candidates]
        if not isinstance(candidates, list):
            return []

        context = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            snippets = item.get("snippets") or item.get("text") or item.get("content")
            if isinstance(snippets, str):
                snippets = [snippets]
            context.append(
                {
                    "title": str(item.get("title") or item.get("name") or ""),
                    "url": str(item.get("url") or ""),
                    "snippets": snippets or [],
                }
            )
        return context

    def _normalise_nested_results(
        self, payload: dict[str, Any], key: str
    ) -> list[dict[str, Any]]:
        raw_results = nested_results(payload, key)
        if not isinstance(raw_results, list):
            return []
        return [item for item in raw_results if isinstance(item, dict)]

    def _normalise_media_results(
        self, payload: dict[str, Any], key: str
    ) -> list[dict[str, Any]]:
        raw_results = payload.get("results") or nested_results(payload, key)
        if not isinstance(raw_results, list):
            return []
        results = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            results.append(
                {
                    "title": str(item.get("title") or item.get("source") or ""),
                    "url": str(item.get("url") or item.get("page_url") or ""),
                    "description": str(item.get("description") or ""),
                    "thumbnail": item.get("thumbnail") or item.get("thumbnail_url"),
                    "position": index,
                }
            )
        return results

    def _normalise_suggestions(self, payload: dict[str, Any]) -> list[str]:
        raw_results = payload.get("results") or payload.get("suggestions") or []
        if not isinstance(raw_results, list):
            return []
        suggestions = []
        for item in raw_results:
            if isinstance(item, str):
                suggestions.append(item)
            elif isinstance(item, dict):
                value = item.get("query") or item.get("text") or item.get("value")
                if value:
                    suggestions.append(str(value))
        return suggestions


def clamp_limit(limit: int) -> int:
    """Clamp user supplied limits to the Brave/Hermes safe range."""

    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 5
    return max(1, min(parsed, MAX_LIMIT))


def nested_results(payload: dict[str, Any], key: str) -> list[Any]:
    nested = payload.get(key)
    if not isinstance(nested, dict):
        return []
    results = nested.get("results", [])
    return results if isinstance(results, list) else []
