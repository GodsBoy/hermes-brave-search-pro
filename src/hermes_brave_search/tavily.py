"""Keyed Tavily extraction provider for Hermes."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .compat import TAVILY_API_KEY_ENV, _get_env_value
from .provider import WebSearchProvider

TAVILY_EXTRACT_ENDPOINT = "https://api.tavily.com/extract"
TAVILY_HTTP_TIMEOUT_SECONDS = 60.0


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


class TavilyExtractProvider(WebSearchProvider):
    """Extraction-only Tavily provider using an operator-supplied API key."""

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

        payload: dict[str, Any] = {
            "urls": urls,
            "include_images": False,
        }
        output_format = kwargs.get("format")
        if output_format in {"markdown", "text"}:
            payload["format"] = output_format

        try:
            import httpx

            response = httpx.post(
                TAVILY_EXTRACT_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=TAVILY_HTTP_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException:
            return _error_results(urls, "Tavily extract request timed out")
        except httpx.TransportError:
            return _error_results(urls, "Tavily extract request failed")

        if response.status_code != 200:
            return _error_results(urls, self._http_error(response.status_code))

        try:
            body = response.json()
        except (TypeError, ValueError):
            return _error_results(urls, "Tavily returned an invalid response")
        if not isinstance(body, dict):
            return _error_results(urls, "Tavily returned an invalid response")

        success_rows = body.get("results", [])
        failure_rows = body.get("failed_results", [])
        if not isinstance(success_rows, list) or not isinstance(failure_rows, list):
            return _error_results(urls, "Tavily returned an invalid response")

        successes: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        failures: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        for row in success_rows:
            if isinstance(row, dict) and isinstance(row.get("url"), str):
                successes[row["url"]].append(row)
        for row in failure_rows:
            if isinstance(row, dict) and isinstance(row.get("url"), str):
                failures[row["url"]].append(row)

        normalized: list[dict[str, Any]] = []
        for url in urls:
            success_rows = successes.get(url)
            failure_rows = failures.get(url)
            if success_rows:
                row = success_rows.popleft()
                content = row.get("raw_content")
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

    @staticmethod
    def _http_error(status_code: int) -> str:
        if status_code == 400:
            label = "request was rejected"
        elif status_code == 401:
            label = "authentication failed"
        elif status_code == 429:
            label = "rate limit reached"
        elif status_code in {432, 433}:
            label = "quota is unavailable"
        elif status_code >= 500:
            label = "service failed"
        else:
            label = "request failed"
        return f"Tavily {label} (HTTP {status_code})"
