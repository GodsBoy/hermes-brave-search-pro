"""Brave Search Pro HTTP client and response normalisation."""

from __future__ import annotations

import math
import os
import re
import time
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx

from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV, BRAVE_MODE_ENDPOINTS

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_LIMIT = 20
MAX_PLACE_COUNT = 100
MAX_LOCAL_IDS = 20
QUERY_OPTIONAL_MODES = {"place", "local", "pois", "descriptions"}
PLACE_MODES = {"place", "local"}
LOCAL_ID_MODES = {"pois", "descriptions"}
PLACE_BUCKET_KEYS = (
    "cities",
    "countries",
    "regions",
    "neighborhoods",
    "addresses",
    "streets",
    "mixed",
)
DEFAULT_CONTEXT_COUNT = 20
MAX_CONTEXT_LIMIT = 50
MIN_CONTEXT_TOKENS = 1024
MAX_CONTEXT_TOKENS = 32768
MAX_CONTEXT_SNIPPETS = 256
MIN_CONTEXT_TOKENS_PER_URL = 512
MAX_CONTEXT_TOKENS_PER_URL = 8192
MAX_CONTEXT_SNIPPETS_PER_URL = 100
CONTEXT_THRESHOLD_MODES = {"balanced", "disabled", "lenient", "strict"}
FRESHNESS_MODES = {"pd", "pw", "pm", "py"}
FRESHNESS_RANGE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2}$")
SEARCH_LANG_RE = re.compile(r"^[A-Za-z][A-Za-z-]{1,15}$")
CONTEXT_POST_PARAMS = {
    "context_threshold_mode",
    "country",
    "search_lang",
    "freshness",
    "goggles",
    "spellcheck",
    "maximum_number_of_snippets",
    "maximum_number_of_tokens_per_url",
    "maximum_number_of_snippets_per_url",
    "enable_local",
    "enable_source_metadata",
}
LOCATION_HEADER_MAP = {
    "loc_lat": "X-Loc-Lat",
    "loc_long": "X-Loc-Long",
    "loc_timezone": "X-Loc-Timezone",
    "loc_city": "X-Loc-City",
    "loc_state": "X-Loc-State",
    "loc_state_name": "X-Loc-State-Name",
    "loc_country": "X-Loc-Country",
    "loc_postal_code": "X-Loc-Postal-Code",
}


@dataclass(slots=True)
class BraveSearchClient:
    """Small synchronous client for Brave Search API calls."""

    api_key: str | None = None
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    base_headers: dict[str, str] | None = None
    max_retries: int = 2
    backoff_seconds: float = 0.25

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
        query: str | None,
        mode: str = "both",
        limit: int | str | None = None,
        context_count: int | None = None,
        max_tokens: int | None = None,
        max_urls: int | None = None,
        max_snippets: int | None = None,
        max_tokens_per_url: int | None = None,
        max_snippets_per_url: int | None = None,
        context_threshold_mode: str | None = None,
        freshness: str | None = None,
        country: str | None = None,
        search_lang: str | None = None,
        goggles: str | list[str] | None = None,
        spellcheck: bool | str | None = None,
        enable_local: bool | str | None = None,
        enable_source_metadata: bool | str | None = None,
        loc_lat: str | float | int | None = None,
        loc_long: str | float | int | None = None,
        loc_timezone: str | None = None,
        loc_city: str | None = None,
        loc_state: str | None = None,
        loc_state_name: str | None = None,
        loc_country: str | None = None,
        loc_postal_code: str | None = None,
        latitude: str | float | int | None = None,
        longitude: str | float | int | None = None,
        location: str | None = None,
        radius: str | float | int | None = None,
        count: int | str | None = None,
        ui_lang: str | None = None,
        units: str | None = None,
        safesearch: str | None = None,
        geoloc: str | None = None,
        ids: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a Brave search mode and return a JSON-serialisable envelope."""

        mode = (mode or "both").strip().lower()
        if mode not in self.MODE_ENDPOINTS:
            return {
                "success": False,
                "error": f"Unsupported Brave search mode: {mode}",
            }
        query = str(query or "").strip()
        query_required_modes = set(self.MODE_ENDPOINTS) - QUERY_OPTIONAL_MODES
        if mode in query_required_modes and not query:
            return {"success": False, "error": "query is required"}

        context_options: dict[str, Any] | None = None
        if mode in {"both", "llm", "context"}:
            normalized = normalise_context_options(
                context_threshold_mode=context_threshold_mode,
                freshness=freshness,
                country=country,
                search_lang=search_lang,
                goggles=goggles,
                spellcheck=spellcheck,
                enable_local=enable_local,
                enable_source_metadata=enable_source_metadata,
                loc_lat=loc_lat,
                loc_long=loc_long,
                loc_timezone=loc_timezone,
                loc_city=loc_city,
                loc_state=loc_state,
                loc_state_name=loc_state_name,
                loc_country=loc_country,
                loc_postal_code=loc_postal_code,
            )
            if not normalized["success"]:
                return {"success": False, "error": normalized["error"]}
            context_options = normalized

        local_headers: dict[str, str] = {}
        if mode in LOCAL_ID_MODES:
            local_headers = normalise_location_headers(
                loc_lat=loc_lat,
                loc_long=loc_long,
                loc_timezone=loc_timezone,
                loc_city=loc_city,
                loc_state=loc_state,
                loc_state_name=loc_state_name,
                loc_country=normalise_country(loc_country) or loc_country,
                loc_postal_code=loc_postal_code,
            )

        api_key = self.resolved_api_key()
        if not api_key:
            return {
                "success": False,
                "error": "BRAVE_SEARCH_API_KEY is required",
            }

        headers = self._headers(
            api_key,
            location_headers={
                **(context_options or {}).get("headers", {}),
                **local_headers,
            },
        )
        if mode == "both":
            return self._search_both(
                query=query,
                limit=limit,
                headers=headers,
                context_count=context_count,
                max_tokens=max_tokens,
                max_urls=max_urls,
                max_snippets=max_snippets,
                max_tokens_per_url=max_tokens_per_url,
                max_snippets_per_url=max_snippets_per_url,
                context_params=(context_options or {}).get("params", {}),
            )

        params = self._params_for_mode(
            query=query,
            mode=mode,
            limit=limit,
            context_count=context_count,
            max_tokens=max_tokens,
            max_urls=max_urls,
            max_snippets=max_snippets,
            max_tokens_per_url=max_tokens_per_url,
            max_snippets_per_url=max_snippets_per_url,
            context_params=(context_options or {}).get("params", {}),
            latitude=latitude,
            longitude=longitude,
            location=location,
            radius=radius,
            count=count,
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            units=units,
            safesearch=safesearch,
            spellcheck=spellcheck,
            geoloc=geoloc,
            ids=ids,
        )
        if not params["success"]:
            return {"success": False, "error": params["error"]}
        request_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS[mode],
            params=params["params"],
            headers=headers,
            method=self._method_for_mode(
                mode=mode,
                params=params["params"],
                headers=headers,
            ),
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
        if mode in PLACE_MODES:
            return {
                "success": True,
                "data": {"places": self._normalise_places(payload)},
            }
        if mode == "pois":
            return {
                "success": True,
                "data": {"local_pois": self._normalise_local_results(payload)},
            }
        if mode == "descriptions":
            return {
                "success": True,
                "data": {"local_descriptions": self._normalise_local_results(payload)},
            }

        data: dict[str, Any] = {}

        if mode in {"web", "both", "discussions"}:
            data["web"] = self._normalise_web_results(payload)

        if mode in {"both", "llm", "context"}:
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

    def _search_both(
        self,
        query: str,
        limit: int | str | None,
        headers: dict[str, str],
        context_count: int | None,
        max_tokens: int | None,
        max_urls: int | None,
        max_snippets: int | None,
        max_tokens_per_url: int | None,
        max_snippets_per_url: int | None,
        context_params: dict[str, Any],
    ) -> dict[str, Any]:
        web_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS["web"],
            params=self._params_for_web(query=query, limit=limit),
            headers=headers,
        )
        if not web_result["success"]:
            return {"success": False, "error": web_result["error"]}

        context_request_params = self._params_for_context(
            query=query,
            context_count=context_count,
            max_tokens=max_tokens,
            max_urls=max_urls,
            max_snippets=max_snippets,
            max_tokens_per_url=max_tokens_per_url,
            max_snippets_per_url=max_snippets_per_url,
            context_params=context_params,
        )
        context_result = self._get_payload(
            endpoint=self.MODE_ENDPOINTS["context"],
            params=context_request_params,
            headers=headers,
            method=self._method_for_mode(
                mode="context",
                params=context_request_params,
                headers=headers,
            ),
        )
        data: dict[str, Any] = {
            "web": self._normalise_web_results(web_result["payload"]),
            "llm_context": [],
        }
        if context_result["success"]:
            data["llm_context"] = self._normalise_llm_context(context_result["payload"])
        else:
            data["llm_context_error"] = context_result["error"]

        return {"success": True, "data": data}

    def _headers(
        self, api_key: str, location_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
            **(location_headers or {}),
            **(self.base_headers or {}),
        }

    def _get_payload(
        self,
        endpoint: str,
        params: dict[str, Any],
        headers: dict[str, str],
        method: str = "GET",
    ) -> dict[str, Any]:
        attempts = max(0, int(self.max_retries)) + 1
        for attempt in range(attempts):
            try:
                if method == "POST":
                    response = httpx.post(
                        endpoint,
                        json=params,
                        headers={**headers, "Content-Type": "application/json"},
                        timeout=self.timeout,
                    )
                else:
                    response = httpx.get(
                        endpoint,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                response.raise_for_status()
                return {"success": True, "payload": response.json()}
            except httpx.HTTPStatusError as exc:
                if not should_retry_status(exc.response.status_code) or (
                    attempt == attempts - 1
                ):
                    return {"success": False, "error": str(exc)}
                self._sleep_before_retry(attempt)
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                if attempt == attempts - 1:
                    return {"success": False, "error": str(exc)}
                self._sleep_before_retry(attempt)
            except ValueError as exc:
                return {"success": False, "error": str(exc)}

        return {"success": False, "error": "Brave request failed"}

    def _params_for_mode(
        self,
        query: str,
        mode: str,
        limit: int | str | None,
        context_count: int | None,
        max_tokens: int | None,
        max_urls: int | None,
        max_snippets: int | None,
        max_tokens_per_url: int | None,
        max_snippets_per_url: int | None,
        context_params: dict[str, Any],
        latitude: str | float | int | None,
        longitude: str | float | int | None,
        location: str | None,
        radius: str | float | int | None,
        count: int | str | None,
        country: str | None,
        search_lang: str | None,
        ui_lang: str | None,
        units: str | None,
        safesearch: str | None,
        spellcheck: bool | str | None,
        geoloc: str | None,
        ids: str | list[str] | None,
    ) -> dict[str, Any]:
        if mode in {"llm", "context"}:
            return {
                "success": True,
                "params": self._params_for_context(
                    query=query,
                    context_count=context_count,
                    max_tokens=max_tokens,
                    max_urls=max_urls,
                    max_snippets=max_snippets,
                    max_tokens_per_url=max_tokens_per_url,
                    max_snippets_per_url=max_snippets_per_url,
                    context_params=context_params,
                ),
            }

        if mode in PLACE_MODES:
            return self._params_for_place(
                query=query,
                limit=limit,
                latitude=latitude,
                longitude=longitude,
                location=location,
                radius=radius,
                count=count,
                country=country,
                search_lang=search_lang,
                ui_lang=ui_lang,
                units=units,
                safesearch=safesearch,
                spellcheck=spellcheck,
                geoloc=geoloc,
            )

        if mode in LOCAL_ID_MODES:
            return self._params_for_local_ids(
                ids=ids,
                search_lang=search_lang if mode == "pois" else None,
                ui_lang=ui_lang if mode == "pois" else None,
                units=units if mode == "pois" else None,
            )

        params = self._params_for_web(query=query, limit=limit)
        if mode == "discussions":
            params["result_filter"] = "discussions"
        return {"success": True, "params": params}

    def _params_for_web(self, query: str, limit: int | str | None) -> dict[str, Any]:
        return {"q": query.strip(), "count": clamp_limit(limit)}

    def _params_for_place(
        self,
        *,
        query: str,
        limit: int | str | None,
        latitude: str | float | int | None,
        longitude: str | float | int | None,
        location: str | None,
        radius: str | float | int | None,
        count: int | str | None,
        country: str | None,
        search_lang: str | None,
        ui_lang: str | None,
        units: str | None,
        safesearch: str | None,
        spellcheck: bool | str | None,
        geoloc: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "count": clamp_place_count(limit if count is None else count)
        }
        if query:
            params["q"] = query

        lat = normalise_float(latitude)
        lon = normalise_float(longitude)
        if (latitude is None) != (longitude is None):
            return {
                "success": False,
                "error": "latitude and longitude must be provided together",
            }
        if latitude is not None and lat is None:
            return {"success": False, "error": f"Unsupported latitude: {latitude}"}
        if longitude is not None and lon is None:
            return {"success": False, "error": f"Unsupported longitude: {longitude}"}
        if lat is not None:
            if not -90 <= lat <= 90:
                return {"success": False, "error": f"Unsupported latitude: {latitude}"}
            if lon is None or not -180 <= lon <= 180:
                return {
                    "success": False,
                    "error": f"Unsupported longitude: {longitude}",
                }
            params["latitude"] = lat
            params["longitude"] = lon

        normalized_location = str(location or "").strip()
        if normalized_location:
            params["location"] = normalized_location

        normalized_radius = normalise_float(radius)
        if radius is not None and normalized_radius is None:
            return {"success": False, "error": f"Unsupported radius: {radius}"}
        if normalized_radius is not None:
            if normalized_radius < 0:
                return {"success": False, "error": f"Unsupported radius: {radius}"}
            params["radius"] = normalized_radius

        locale_params = normalise_local_locale_options(
            country=country,
            search_lang=search_lang,
            ui_lang=ui_lang,
            units=units,
            safesearch=safesearch,
        )
        if not locale_params["success"]:
            return locale_params
        params.update(locale_params["params"])

        normalized_spellcheck = normalise_bool(spellcheck)
        if spellcheck is not None and normalized_spellcheck is None:
            return {"success": False, "error": f"Unsupported spellcheck: {spellcheck}"}
        if normalized_spellcheck is not None:
            params["spellcheck"] = normalized_spellcheck

        normalized_geoloc = str(geoloc or "").strip()
        if normalized_geoloc:
            params["geoloc"] = normalized_geoloc

        return {"success": True, "params": params}

    def _params_for_local_ids(
        self,
        *,
        ids: str | list[str] | None,
        search_lang: str | None,
        ui_lang: str | None,
        units: str | None,
    ) -> dict[str, Any]:
        normalized_ids = normalise_ids(ids)
        if not normalized_ids:
            return {"success": False, "error": "ids are required"}
        if len(normalized_ids) > MAX_LOCAL_IDS:
            return {"success": False, "error": "ids supports at most 20 values"}

        params: dict[str, Any] = {"ids": normalized_ids}
        locale_params = normalise_local_locale_options(
            country=None,
            search_lang=search_lang,
            ui_lang=ui_lang,
            units=units,
            safesearch=None,
        )
        if not locale_params["success"]:
            return locale_params
        params.update(locale_params["params"])
        return {"success": True, "params": params}

    def _params_for_context(
        self,
        query: str,
        context_count: int | None,
        max_tokens: int | None,
        max_urls: int | None,
        max_snippets: int | None,
        max_tokens_per_url: int | None,
        max_snippets_per_url: int | None,
        context_params: dict[str, Any],
    ) -> dict[str, Any]:
        count = clamp_context_limit(
            DEFAULT_CONTEXT_COUNT if context_count is None else context_count
        )
        params: dict[str, Any] = {
            "q": query.strip(),
            "count": count,
            "maximum_number_of_urls": clamp_context_limit(
                count if max_urls is None else max_urls
            ),
        }
        if max_tokens is not None:
            params["maximum_number_of_tokens"] = clamp_context_tokens(max_tokens)
        if max_snippets is not None:
            params["maximum_number_of_snippets"] = clamp_context_snippets(max_snippets)
        if max_tokens_per_url is not None:
            params["maximum_number_of_tokens_per_url"] = clamp_context_tokens_per_url(
                max_tokens_per_url
            )
        if max_snippets_per_url is not None:
            params["maximum_number_of_snippets_per_url"] = (
                clamp_context_snippets_per_url(max_snippets_per_url)
            )
        params.update(context_params)
        return params

    def _method_for_mode(
        self, mode: str, params: dict[str, Any], headers: dict[str, str]
    ) -> str:
        if mode not in {"both", "llm", "context"}:
            return "GET"
        if any(key in params for key in CONTEXT_POST_PARAMS):
            return "POST"
        if any(key in headers for key in LOCATION_HEADER_MAP.values()):
            return "POST"
        return "GET"

    def _sleep_before_retry(self, attempt: int) -> None:
        if self.backoff_seconds <= 0:
            return
        time.sleep(self.backoff_seconds * (attempt + 1))

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
        title = str(item.get("title") or item.get("name") or source.get("title") or "")
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

    def _normalise_places(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query")
        location = payload.get("location")
        return {
            "query": query if isinstance(query, dict) else {},
            "results": self._normalise_location_results(payload.get("results")),
            **{
                key: self._normalise_place_bucket(payload.get(key))
                for key in PLACE_BUCKET_KEYS
            },
            "location": location if isinstance(location, dict) else {},
        }

    def _normalise_location_results(self, raw_results: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_results, list):
            return []
        results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            results.append(self._normalise_location_item(item))
        return results

    def _normalise_location_item(self, item: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "type",
            "id",
            "title",
            "url",
            "provider_url",
            "description",
            "coordinates",
            "postal_address",
            "opening_hours",
            "contact",
            "zoom_level",
            "rating",
            "price_range",
            "distance",
            "categories",
            "serves_cuisine",
            "thumbnail",
            "pictures",
            "profiles",
            "reviews",
            "action",
            "icon_category",
            "results",
            "timezone",
            "timezone_offset",
        )
        normalized = {field: item[field] for field in fields if field in item}
        if "title" in normalized:
            normalized["title"] = str(normalized["title"] or "")
        if "url" in normalized:
            normalized["url"] = str(normalized["url"] or "")
        if "description" in normalized:
            normalized["description"] = str(normalized["description"] or "")
        return normalized

    def _normalise_place_bucket(self, bucket: Any) -> list[dict[str, Any]]:
        if not isinstance(bucket, list):
            return []
        return [item for item in bucket if isinstance(item, dict)]

    def _normalise_local_results(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw_results = payload.get("results")
        if isinstance(raw_results, dict):
            raw_results = list(raw_results.values())
        if not isinstance(raw_results, list):
            raw_results = payload.get("descriptions") or payload.get("pois") or []
        if isinstance(raw_results, dict):
            raw_results = list(raw_results.values())
        if not isinstance(raw_results, list):
            return []
        return [item for item in raw_results if isinstance(item, dict)]

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


def clamp_int(value: Any, *, default: int, lower: int, upper: int) -> int:
    """Clamp an integer-like value to an inclusive range."""

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(lower, min(parsed, upper))


def clamp_limit(limit: Any) -> int:
    """Clamp user supplied limits to the Brave/Hermes safe range."""

    return clamp_int(limit, default=5, lower=1, upper=MAX_LIMIT)


def clamp_place_count(count: Any) -> int:
    """Clamp Brave Place Search count values to its documented range."""

    return clamp_int(count, default=20, lower=1, upper=MAX_PLACE_COUNT)


def clamp_context_limit(limit: Any) -> int:
    """Clamp limits for Brave LLM Context API count/URL parameters."""

    return clamp_int(limit, default=5, lower=1, upper=MAX_CONTEXT_LIMIT)


def clamp_context_tokens(tokens: Any) -> int:
    """Clamp Brave LLM Context token budget parameters."""

    return clamp_int(
        tokens,
        default=8192,
        lower=MIN_CONTEXT_TOKENS,
        upper=MAX_CONTEXT_TOKENS,
    )


def clamp_context_snippets(snippets: Any) -> int:
    """Clamp Brave LLM Context total snippet count parameters."""

    return clamp_int(snippets, default=50, lower=1, upper=MAX_CONTEXT_SNIPPETS)


def clamp_context_tokens_per_url(tokens: Any) -> int:
    """Clamp Brave LLM Context per-URL token budget parameters."""

    return clamp_int(
        tokens,
        default=4096,
        lower=MIN_CONTEXT_TOKENS_PER_URL,
        upper=MAX_CONTEXT_TOKENS_PER_URL,
    )


def clamp_context_snippets_per_url(snippets: Any) -> int:
    """Clamp Brave LLM Context per-URL snippet count parameters."""

    return clamp_int(snippets, default=50, lower=1, upper=MAX_CONTEXT_SNIPPETS_PER_URL)


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


def normalise_freshness(value: str | None) -> str | None:
    """Return a validated Brave freshness value."""

    if value is None:
        return None
    parsed = str(value).strip().lower()
    if not parsed:
        return None
    if parsed in FRESHNESS_MODES or FRESHNESS_RANGE_RE.match(parsed):
        return parsed
    return None


def normalise_country(value: str | None) -> str | None:
    """Return a normalized two-letter country code."""

    if value is None:
        return None
    parsed = str(value).strip().upper()
    if not parsed:
        return None
    if len(parsed) == 2 and parsed.isalpha():
        return parsed
    return None


def normalise_search_lang(value: str | None) -> str | None:
    """Return a normalized Brave search language preference."""

    if value is None:
        return None
    parsed = str(value).strip().lower()
    if not parsed:
        return None
    if SEARCH_LANG_RE.match(parsed):
        return parsed
    return None


def normalise_float(value: Any) -> float | None:
    """Return a float for numeric API parameters."""

    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalise_units(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = str(value).strip().lower()
    return parsed if parsed in {"metric", "imperial"} else None


def normalise_safesearch(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = str(value).strip().lower()
    return parsed if parsed in {"off", "moderate", "strict"} else None


def normalise_ids(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates: list[str] = value.split(",")
    elif isinstance(value, list):
        candidates = value
    else:
        return []
    return [str(item).strip() for item in candidates if str(item).strip()]


def normalise_local_locale_options(
    *,
    country: str | None,
    search_lang: str | None,
    ui_lang: str | None,
    units: str | None,
    safesearch: str | None,
) -> dict[str, Any]:
    """Normalize locale parameters shared by Brave local endpoints."""

    params: dict[str, Any] = {}
    normalized_country = normalise_country(country)
    if country and normalized_country is None:
        return {"success": False, "error": f"Unsupported country: {country}"}
    if normalized_country:
        params["country"] = normalized_country

    normalized_search_lang = normalise_search_lang(search_lang)
    if search_lang and normalized_search_lang is None:
        return {"success": False, "error": f"Unsupported search_lang: {search_lang}"}
    if normalized_search_lang:
        params["search_lang"] = normalized_search_lang

    normalized_ui_lang = normalise_search_lang(ui_lang)
    if ui_lang and normalized_ui_lang is None:
        return {"success": False, "error": f"Unsupported ui_lang: {ui_lang}"}
    if normalized_ui_lang:
        params["ui_lang"] = normalized_ui_lang

    normalized_units = normalise_units(units)
    if units and normalized_units is None:
        return {"success": False, "error": f"Unsupported units: {units}"}
    if normalized_units:
        params["units"] = normalized_units

    normalized_safesearch = normalise_safesearch(safesearch)
    if safesearch and normalized_safesearch is None:
        return {"success": False, "error": f"Unsupported safesearch: {safesearch}"}
    if normalized_safesearch:
        params["safesearch"] = normalized_safesearch

    return {"success": True, "params": params}


def normalise_goggles(value: str | list[str] | None) -> str | list[str] | None:
    """Return a validated Brave Goggles value."""

    if value is None:
        return None
    if isinstance(value, str):
        parsed = value.strip()
        return parsed or None
    if isinstance(value, list):
        parsed = [str(item).strip() for item in value if str(item).strip()]
        if not parsed:
            return None
        if len(parsed) > 3:
            return None
        return parsed
    return None


def normalise_bool(value: bool | str | None) -> bool | None:
    """Return a bool from JSON booleans or common string booleans."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    parsed = str(value).strip().lower()
    if parsed in {"true", "1", "yes", "on"}:
        return True
    if parsed in {"false", "0", "no", "off"}:
        return False
    return None


def normalise_location_headers(**values: Any) -> dict[str, str]:
    """Convert optional location fields to Brave location headers."""

    headers: dict[str, str] = {}
    for key, header in LOCATION_HEADER_MAP.items():
        value = values.get(key)
        if value is None:
            continue
        parsed = str(value).strip()
        if parsed:
            headers[header] = parsed
    return headers


def normalise_context_options(
    *,
    context_threshold_mode: str | None,
    freshness: str | None,
    country: str | None,
    search_lang: str | None,
    goggles: str | list[str] | None,
    spellcheck: bool | str | None,
    enable_local: bool | str | None,
    enable_source_metadata: bool | str | None,
    loc_lat: str | float | int | None,
    loc_long: str | float | int | None,
    loc_timezone: str | None,
    loc_city: str | None,
    loc_state: str | None,
    loc_state_name: str | None,
    loc_country: str | None,
    loc_postal_code: str | None,
) -> dict[str, Any]:
    """Normalize context query parameters and headers."""

    params: dict[str, Any] = {}

    threshold = normalise_context_threshold(context_threshold_mode)
    if context_threshold_mode and threshold is None:
        return {
            "success": False,
            "error": f"Unsupported context_threshold_mode: {context_threshold_mode}",
        }
    if threshold:
        params["context_threshold_mode"] = threshold

    normalized_freshness = normalise_freshness(freshness)
    if freshness and normalized_freshness is None:
        return {"success": False, "error": f"Unsupported freshness: {freshness}"}
    if normalized_freshness:
        params["freshness"] = normalized_freshness

    normalized_country = normalise_country(country)
    if country and normalized_country is None:
        return {"success": False, "error": f"Unsupported country: {country}"}
    if normalized_country:
        params["country"] = normalized_country

    normalized_search_lang = normalise_search_lang(search_lang)
    if search_lang and normalized_search_lang is None:
        return {
            "success": False,
            "error": f"Unsupported search_lang: {search_lang}",
        }
    if normalized_search_lang:
        params["search_lang"] = normalized_search_lang

    normalized_goggles = normalise_goggles(goggles)
    if goggles and normalized_goggles is None:
        return {"success": False, "error": "Unsupported goggles value"}
    if normalized_goggles:
        params["goggles"] = normalized_goggles

    for key, value in {
        "spellcheck": spellcheck,
        "enable_local": enable_local,
        "enable_source_metadata": enable_source_metadata,
    }.items():
        normalized = normalise_bool(value)
        if value is not None and normalized is None:
            return {"success": False, "error": f"Unsupported {key}: {value}"}
        if normalized is not None:
            params[key] = normalized

    headers = normalise_location_headers(
        loc_lat=loc_lat,
        loc_long=loc_long,
        loc_timezone=loc_timezone,
        loc_city=loc_city,
        loc_state=loc_state,
        loc_state_name=loc_state_name,
        loc_country=normalise_country(loc_country) or loc_country,
        loc_postal_code=loc_postal_code,
    )

    return {"success": True, "params": params, "headers": headers}


def should_retry_status(status_code: int) -> bool:
    """Return True for Brave HTTP statuses worth retrying."""

    return status_code == 429 or status_code >= 500


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
