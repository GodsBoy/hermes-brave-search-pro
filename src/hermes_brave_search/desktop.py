"""Safe backend adapter for the Hermes Desktop Brave Search page."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .client import BraveSearchClient

DESKTOP_RESULT_LIMIT = 5
DESKTOP_REQUEST_TIMEOUT_SECONDS = 6.0
DESKTOP_MAX_RETRIES = 2
DESKTOP_RETRY_BACKOFF_SECONDS = 0.5
MAX_QUERY_CHARACTERS = 400
MAX_QUERY_WORDS = 50

_MAX_TITLE_CHARACTERS = 500
_MAX_DESCRIPTION_CHARACTERS = 2_000
_MAX_URL_CHARACTERS = 2_048


def search_desktop_web(
    query: object, *, client: BraveSearchClient | None = None
) -> dict[str, Any]:
    """Run one bounded web search and return only Desktop presentation fields."""

    clean_query, validation_error = _validate_query(query)
    if validation_error:
        return {"outcome": "validation_error", "message": validation_error}

    if client is None:
        client = BraveSearchClient()
        client.timeout = DESKTOP_REQUEST_TIMEOUT_SECONDS
        client.max_retries = DESKTOP_MAX_RETRIES
        client.backoff_seconds = DESKTOP_RETRY_BACKOFF_SECONDS
    if not client.resolved_api_key():
        return _api_failure("missing_credential")

    try:
        result = client.search(clean_query, mode="web", limit=DESKTOP_RESULT_LIMIT)
    except Exception:
        return _api_failure("api_error")

    if not isinstance(result, dict):
        return _api_failure("api_error")
    if result.get("success") is not True:
        return _api_failure(_failure_outcome(result.get("error")))

    data = result.get("data")
    web_results = data.get("web") if isinstance(data, dict) else None
    results = _presentation_results(web_results)
    if not results:
        return {"outcome": "empty", "results": []}
    return {"outcome": "results", "results": results}


def _validate_query(query: object) -> tuple[str, str | None]:
    clean_query = query.strip() if isinstance(query, str) else ""
    if not clean_query:
        return "", "Enter a search query."
    if len(clean_query) > MAX_QUERY_CHARACTERS:
        return "", "Search queries must be 400 characters or fewer."
    if len(clean_query.split()) > MAX_QUERY_WORDS:
        return "", "Search queries must contain 50 words or fewer."
    return clean_query, None


def _failure_outcome(error: object) -> str:
    error_text = error.lower() if isinstance(error, str) else ""
    if "brave_search_api_key" in error_text or "missing credential" in error_text:
        return "missing_credential"
    if any(marker in error_text for marker in ("401", "403", "invalid key")):
        return "invalid_credential"
    if any(marker in error_text for marker in ("429", "quota", "rate limit")):
        return "rate_limited"
    return "api_error"


def _api_failure(outcome: str) -> dict[str, str]:
    messages = {
        "missing_credential": "BRAVE_SEARCH_API_KEY is required for Brave Search.",
        "invalid_credential": "Brave Search credentials were not accepted.",
        "rate_limited": "Brave Search is temporarily unavailable. Try again later.",
        "api_error": "Brave Search could not complete this request. Try again.",
    }
    return {"outcome": outcome, "message": messages[outcome]}


def _presentation_results(web_results: object) -> list[dict[str, Any]]:
    if not isinstance(web_results, list):
        return []

    results: list[dict[str, Any]] = []
    for index, result in enumerate(web_results[:DESKTOP_RESULT_LIMIT], start=1):
        if not isinstance(result, dict):
            continue
        position = result.get("position")
        results.append(
            {
                "title": _safe_text(result.get("title"), _MAX_TITLE_CHARACTERS),
                "description": _safe_text(
                    result.get("description"), _MAX_DESCRIPTION_CHARACTERS
                ),
                "url": _safe_url(result.get("url")),
                "position": position
                if isinstance(position, int) and not isinstance(position, bool)
                else index,
            }
        )
    return results


def _safe_text(value: object, limit: int) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def _safe_url(value: object) -> str:
    if not isinstance(value, str):
        return ""
    url = value.strip()[:_MAX_URL_CHARACTERS]
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return ""
    return url
