"""Brave Search Pro HTTP client and response normalisation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx

from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV, BRAVE_MODE_ENDPOINTS

DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_LIMIT = 20
MAX_CONTEXT_LIMIT = 50
MIN_CONTEXT_TOKENS = 1024
MAX_CONTEXT_TOKENS = 32768
CONTEXT_THRESHOLD_MODES = {"balanced", "disabled", "lenient", "strict"}


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

    def search(
        self,
        query: str,
        mode: str = "both",
        limit: int = 5,
        max_tokens: int | None = None,
        max_urls: int | None = None,
        context_threshold_mode: str | None = None,
    ) -> dict[str, Any]:
        """Run a Brave search mode and return a JSON-serialisable envelope."""

        mode = (mode or "both").strip().lower()
        if mode not in self.MODE_ENDPOINTS:
            return {
                "success": False,
                "error": f"Unsupported Brave search mode: {mode}",
            }
        if not query or not query.strip():
            return {"success": False, "error": "query is required"}
        threshold = normalise_context_threshold(context_threshold_mode)
        if context_threshold_mode and threshold is None:
            return {
                "success": False,
                "error": (
                    "Unsupported context_threshold_mode: "
                    f"{context_threshold_mode}"
                ),
            }
        api_key = self.resolved_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "BRAVE_SEARCH_API_KEY is required",
            }

        headers = self._headers(api_key)
        if mode == "both":
            return self._search_both(
                query=query,
                limit=limit,
                headers=headers,
                max_tokens=max_tokens,
                max_urls=max_urls,
                context_threshold_mode=threshold,
            )

        params = self._params_for_mode(
            query=query,
            mode=mode,
            limit=limit,
            max_tokens=max_tokens,
            max_urls=max_urls,
            context_threshold_mode=threshold,
        )
        request_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS[mode], params=params, headers=headers
        )
        if not request_result["success"]:
            return {"success": False, "error": request_result["error"]}

        payload = request_result["payload"]
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

        if mode in {"both", "llm", "context"}:
            data["llm_context"] = self._normalise_llm_context(payload)

        if mode == "discussions":
            data["discussions"] = self._normalise_nested_results(
                payload, "discussions"
            )

        if mode == "news":
            data["news"] = self._normalise_media_results(payload, "news")

        if mode == "images":
            data["images"] = self._normalise_media_results(payload, "images")

        if mode == "videos":
            data["videos"] = self._normalise_media_results(payload, "videos")

        return {"success": True, "data": data}

    def _search_both(
        self,
        query: str,
        limit: int,
        headers: dict[str, str],
        max_tokens: int | None,
        max_urls: int | None,
        context_threshold_mode: str | None,
    ) -> dict[str, Any]:
        web_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS["web"],
            params=self._params_for_web(query=query, limit=limit),
            headers=headers,
        )
        if not web_result["success"]:
            return {"success": False, "error": web_result["error"]}

        context_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS["context"],
            params=self._params_for_context(
                query=query,
                limit=limit,
                max_tokens=max_tokens,
                max_urls=max_urls,
                context_threshold_mode=context_threshold_mode,
            ),
            headers=headers,
        )
        data: dict[str, Any] = {
            "web": self._normalise_web_results(web_result["payload"]),
            "llm_context": [],
        }
        if context_result["success"]:
            data["llm_context"] = self._normalise_llm_context(
                context_result["payload"]
            )
        else:
            data["llm_context_error"] = context_result["error"]

        return {"success": True, "data": data}

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
            **(self.base_headers or {}),
        }

    def _get_payload(
        self, endpoint: str, params: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        try:
            response = httpx.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return {"success": True, "payload": response.json()}
        except (httpx.HTTPError, ValueError) as exc:
            return {"success": False, "error": str(exc)}

    def _params_for_mode(
        self,
        query: str,
        mode: str,
        limit: int,
        max_tokens: int | None,
        max_urls: int | None,
        context_threshold_mode: str | None,
    ) -> dict[str, Any]:
        if mode in {"llm", "context"}:
            return self._params_for_context(
                query=query,
                limit=limit,
                max_tokens=max_tokens,
                max_urls=max_urls,
                context_threshold_mode=context_threshold_mode,
            )

        params = self._params_for_web(query=query, limit=limit)
        if mode == "discussions":
            params["result_filter"] = "discussions"
        return params

    def _params_for_web(self, query: str, limit: int) -> dict[str, Any]:
        return {"q": query.strip(), "count": clamp_limit(limit)}

    def _params_for_context(
        self,
        query: str,
        limit: int,
        max_tokens: int | None,
        max_urls: int | None,
        context_threshold_mode: str | None,
    ) -> dict[str, Any]:
        count = clamp_context_limit(limit)
        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "maximum_number_of_urls": clamp_context_limit(max_urls or count),
        }
        if max_tokens is not None:
            params["maximum_number_of_tokens"] = clamp_context_tokens(max_tokens)
        if context_threshold_mode:
            params["context_threshold_mode"] = context_threshold_mode
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
        grounding = payload.get("grounding")
        if isinstance(grounding, dict):
            return self._normalise_grounding_context(payload)

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
            context.append(self._normalise_context_item(item, sources={}))
        return context

    def _normalise_grounding_context(
        self, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        grounding = payload.get("grounding")
        sources = payload.get("sources")
        if not isinstance(grounding, dict):
            return []
        if not isinstance(sources, dict):
            sources = {}

        context: list[dict[str, Any]] = []
        generic = grounding.get("generic")
        if isinstance(generic, list):
            for item in generic:
                if isinstance(item, dict):
                    context.append(self._normalise_context_item(item, sources=sources))

        poi = grounding.get("poi")
        if isinstance(poi, dict):
            context.append(self._normalise_context_item(poi, sources=sources))

        map_results = grounding.get("map")
        if isinstance(map_results, list):
            for item in map_results:
                if isinstance(item, dict):
                    context.append(self._normalise_context_item(item, sources=sources))

        return context

    def _normalise_context_item(
        self, item: dict[str, Any], sources: dict[str, Any]
    ) -> dict[str, Any]:
        url = str(item.get("url") or "")
        source = sources.get(url)
        if not isinstance(source, dict):
            source = {}
        title = str(
            item.get("title") or item.get("name") or source.get("title") or ""
        )
        snippets = item.get("snippets") or item.get("text") or item.get("content")
        return {"title": title, "url": url, "snippets": normalise_snippets(snippets)}

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


def clamp_limit(limit: Any) -> int:
    """Clamp user supplied limits to the Brave/Hermes safe range."""

    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 5
    return max(1, min(parsed, MAX_LIMIT))


def clamp_context_limit(limit: Any) -> int:
    """Clamp limits for Brave LLM Context API count/URL parameters."""

    try:
        parsed = int(limit)
    except (TypeError, ValueError):
        parsed = 5
    return max(1, min(parsed, MAX_CONTEXT_LIMIT))


def clamp_context_tokens(tokens: Any) -> int:
    """Clamp Brave LLM Context token budget parameters."""

    try:
        parsed = int(tokens)
    except (TypeError, ValueError):
        parsed = 8192
    return max(MIN_CONTEXT_TOKENS, min(parsed, MAX_CONTEXT_TOKENS))


def normalise_context_threshold(value: str | None) -> str | None:
    """Return a validated Brave LLM Context threshold mode."""

    if value is None:
        return None
    parsed = str(value).strip().lower()
    if not parsed:
        return None
    if parsed not in CONTEXT_THRESHOLD_MODES:
        return None
    return parsed


def normalise_snippets(snippets: Any) -> list[Any]:
    """Return snippets as a list while preserving Brave's structured chunks."""

    if snippets is None:
        return []
    if isinstance(snippets, str):
        return [snippets]
    if isinstance(snippets, list):
        return snippets
    return [snippets]


def nested_results(payload: dict[str, Any], key: str) -> list[Any]:
    nested = payload.get(key)
    if not isinstance(nested, dict):
        return []
    results = nested.get("results", [])
    return results if isinstance(results, list) else []
