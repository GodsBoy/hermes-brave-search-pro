"""Compatibility access to Hermes' bundled Tavily provider."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .compat import TAVILY_API_KEY_ENV, _get_env_value
from .provider import WebSearchProvider


def _error_results(urls: list[str], message: str) -> list[dict[str, Any]]:
    return [
        {
            "url": url,
            "title": "",
            "content": "",
            "raw_content": "",
            "error": message,
        }
        for url in urls
    ]


def _normalize_results(
    urls: list[str], delegated: Any
) -> list[dict[str, Any]]:
    """Restore the legacy one-result-per-input extraction contract."""

    if not isinstance(delegated, list):
        return _error_results(urls, "Tavily returned an invalid response")

    successes: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    failures: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for row in delegated:
        if not isinstance(row, dict) or not isinstance(row.get("url"), str):
            continue
        target = failures if "error" in row else successes
        target[row["url"]].append(row)

    normalized: list[dict[str, Any]] = []
    for url in urls:
        success_rows = successes.get(url)
        failure_rows = failures.get(url)
        if success_rows:
            row = success_rows.popleft()
            content = row.get("raw_content")
            if not isinstance(content, str):
                content = row.get("content")
            content = content if isinstance(content, str) else ""
            title = row.get("title")
            normalized.append(
                {
                    "url": url,
                    "title": title if isinstance(title, str) else "",
                    "content": content,
                    "raw_content": content,
                    "metadata": {},
                }
            )
        elif failure_rows:
            failure_rows.popleft()
            normalized.extend(
                _error_results([url], "Tavily could not extract this URL")
            )
        else:
            normalized.extend(
                _error_results([url], "Tavily returned no result for this URL")
            )
    return normalized


class TavilyExtractProvider(WebSearchProvider):
    """Unregistered, extract-only compatibility adapter for Hermes Tavily."""

    def __init__(self) -> None:
        try:
            from plugins.web.tavily.provider import TavilyWebSearchProvider
        except ImportError as exc:  # pragma: no cover - requires old Hermes
            raise RuntimeError(
                "Hermes v0.21.0 or newer with bundled web-tavily is required"
            ) from exc
        self._provider_type = TavilyWebSearchProvider

    @property
    def name(self) -> str:
        return "tavily"

    @property
    def display_name(self) -> str:
        return "Tavily Extract"

    def is_available(self) -> bool:
        return bool(_get_env_value(TAVILY_API_KEY_ENV))

    def supports_search(self) -> bool:
        return False

    def supports_extract(self) -> bool:
        return True

    def extract(self, urls: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        if not urls:
            return []

        api_key = _get_env_value(TAVILY_API_KEY_ENV)
        if not api_key:
            return _error_results(urls, f"{TAVILY_API_KEY_ENV} is required")

        delegated = self._provider_type().extract(urls, **kwargs)
        return _normalize_results(urls, delegated)

    def get_setup_schema(self) -> dict[str, Any]:
        return {
            "name": self.display_name,
            "badge": "pro",
            "tag": "Keyed Tavily extraction for Hermes web_extract.",
            "env_vars": [
                {
                    "key": TAVILY_API_KEY_ENV,
                    "prompt": "Tavily API key",
                    "url": "https://app.tavily.com/",
                    "secret": True,
                }
            ],
        }
