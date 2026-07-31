"""Compatibility helpers for Hermes Brave Search Pro."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV

BRAVE_PRO_BACKEND = "brave-pro"
BRAVE_FREE_BACKEND = "brave-free"
TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
TAVILY_BACKEND = "tavily"


@dataclass
class CompatReport:
    """Result of applying Brave Pro compatibility helpers."""

    config_changed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.config_changed)


def _get_env_value(name: str) -> str | None:
    try:
        from hermes_cli.config import get_env_value  # type: ignore

        value = get_env_value(name)
        if value and (normalized := str(value).strip()):
            return normalized
    except Exception:
        pass

    value = os.environ.get(name, "").strip()
    return value or None


def _has_brave_api_key() -> bool:
    return bool(
        _get_env_value(BRAVE_API_KEY_ENV) or _get_env_value(BRAVE_API_KEY_COMPAT_ENV)
    )


def ensure_recommended_web_config(*, force: bool = False) -> list[str]:
    """Persist safe Brave Pro web defaults when the plugin is installed.

    The function is intentionally conservative. It only replaces missing values
    or the built-in Brave Free backend. It does not overwrite a user-selected
    non-Brave provider.
    """

    if not _has_brave_api_key():
        return []

    try:
        from hermes_cli.config import load_config, save_config  # type: ignore
    except Exception as exc:
        raise RuntimeError("Hermes configuration API is unavailable") from exc

    config = load_config()
    web = config.setdefault("web", {})
    if not isinstance(web, dict):
        web = {}
        config["web"] = web

    changed: list[str] = []

    backend = web.get("backend")
    if (
        force or backend in (None, "", BRAVE_FREE_BACKEND)
    ) and backend != BRAVE_PRO_BACKEND:
        web["backend"] = BRAVE_PRO_BACKEND
        changed.append("web.backend")

    search_backend = web.get("search_backend")
    if (
        force or search_backend in (None, "", BRAVE_FREE_BACKEND)
    ) and search_backend != BRAVE_PRO_BACKEND:
        web["search_backend"] = BRAVE_PRO_BACKEND
        changed.append("web.search_backend")

    extract_backend = web.get("extract_backend")
    if (
        _get_env_value(TAVILY_API_KEY_ENV)
        and (force or extract_backend in (None, ""))
        and extract_backend != TAVILY_BACKEND
    ):
        web["extract_backend"] = TAVILY_BACKEND
        changed.append("web.extract_backend")

    if changed:
        save_config(config)

    return changed


def apply_runtime_compat(*, force: bool = False) -> CompatReport:
    """Apply safe Brave Pro compatibility helpers without blocking plugin load."""

    report = CompatReport()

    try:
        report.config_changed = ensure_recommended_web_config(force=force)
    except Exception as exc:  # pragma: no cover - defensive plugin boundary
        report.errors.append(f"config update failed: {exc}")

    return report
