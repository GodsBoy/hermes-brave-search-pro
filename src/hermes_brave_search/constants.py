"""Shared constants for the Brave Search Hermes plugin."""

from __future__ import annotations

BRAVE_SEARCH_MODES = [
    "both",
    "web",
    "llm",
    "images",
    "news",
    "videos",
    "discussions",
    "suggest",
    "raw",
]

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
BRAVE_NEWS_ENDPOINT = "https://api.search.brave.com/res/v1/news/search"
BRAVE_IMAGES_ENDPOINT = "https://api.search.brave.com/res/v1/images/search"
BRAVE_VIDEOS_ENDPOINT = "https://api.search.brave.com/res/v1/videos/search"
BRAVE_SUGGEST_ENDPOINT = "https://api.search.brave.com/res/v1/suggest/search"

BRAVE_MODE_ENDPOINTS = {
    "web": BRAVE_SEARCH_ENDPOINT,
    "both": BRAVE_SEARCH_ENDPOINT,
    "llm": BRAVE_SEARCH_ENDPOINT,
    "discussions": BRAVE_SEARCH_ENDPOINT,
    "raw": BRAVE_SEARCH_ENDPOINT,
    "news": BRAVE_NEWS_ENDPOINT,
    "images": BRAVE_IMAGES_ENDPOINT,
    "videos": BRAVE_VIDEOS_ENDPOINT,
    "suggest": BRAVE_SUGGEST_ENDPOINT,
}

BRAVE_API_KEY_ENV = "BRAVE_SEARCH_API_KEY"
BRAVE_API_KEY_COMPAT_ENV = "BRAVE_API_KEY"
