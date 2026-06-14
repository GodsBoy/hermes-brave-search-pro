"""Compatibility helpers for Hermes Brave Search Pro.

The plugin can run on Hermes builds where the Web Search provider picker still
prefers the first credentialed provider over an explicitly configured provider.
Brave Free and Brave Pro share the same Brave API key, so older pickers can land
on Free even when Pro is configured or installed intentionally.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV

BRAVE_PRO_BACKEND = "brave-pro"
BRAVE_FREE_BACKEND = "brave-free"
TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
TAVILY_BACKEND = "tavily"


@dataclass
class CompatReport:
    """Result of applying Brave Pro compatibility helpers."""

    picker_patched: bool = False
    config_changed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.picker_patched or bool(self.config_changed)


def _provider_backend(provider: dict[str, Any]) -> str | None:
    backend = provider.get("web_backend") or provider.get("backend")
    return str(backend) if backend else None


def _env_key_name(env_spec: Any) -> str | None:
    if isinstance(env_spec, str):
        return env_spec
    if isinstance(env_spec, dict):
        key = env_spec.get("key") or env_spec.get("name")
        return str(key) if key else None
    return None


def _provider_env_present(tools_config: Any, provider: dict[str, Any]) -> bool:
    env_vars = provider.get("env_vars", []) or []
    if not env_vars:
        return False

    get_env_value = getattr(tools_config, "get_env_value", None)
    if get_env_value is None:
        get_env_value = os.environ.get

    for spec in env_vars:
        key = _env_key_name(spec)
        if not key or not get_env_value(key):
            return False
    return True


def patch_tools_config_picker() -> bool:
    """Patch older Hermes provider-picker behaviour in the current process.

    This does not edit Hermes source files. It only replaces the loaded
    ``hermes_cli.tools_config._detect_active_provider_index`` function for the
    current CLI/gateway process. The replacement keeps the intended generic
    behaviour: explicit config wins first, env-var fallback second. The fallback
    additionally prefers Brave Pro over Brave Free when both are credentialed,
    because installing this plugin is an explicit Brave Pro signal.
    """

    try:
        from hermes_cli import tools_config  # type: ignore
    except Exception:
        return False

    current = getattr(tools_config, "_detect_active_provider_index", None)
    if current is None or getattr(current, "_brave_pro_compat", False):
        return False

    is_provider_active = getattr(tools_config, "_is_provider_active", None)
    if is_provider_active is None:
        return False

    def _detect_active_provider_index(  # type: ignore[no-untyped-def]
        providers: list[dict[str, Any]],
        config: dict[str, Any],
        *,
        force_fresh: bool = False,
    ) -> int:
        for i, provider in enumerate(providers):
            if is_provider_active(provider, config, force_fresh=force_fresh):
                return i

        credentialed: list[int] = []
        for i, provider in enumerate(providers):
            if _provider_env_present(tools_config, provider):
                credentialed.append(i)

        for i in credentialed:
            if _provider_backend(providers[i]) == BRAVE_PRO_BACKEND:
                return i

        return credentialed[0] if credentialed else 0

    _detect_active_provider_index._brave_pro_compat = True  # type: ignore[attr-defined]
    _detect_active_provider_index._brave_pro_original = current  # type: ignore[attr-defined]
    tools_config._detect_active_provider_index = _detect_active_provider_index
    return True


def _get_env_value(name: str) -> str | None:
    try:
        from hermes_cli.config import get_env_value  # type: ignore

        value = get_env_value(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.environ.get(name)


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
    except Exception:
        return []

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


def apply_runtime_compat() -> CompatReport:
    """Apply all safe Brave Pro compatibility helpers.

    This is called from ``register()`` and must never prevent the plugin from
    loading. Errors are captured in the report instead of raised.
    """

    report = CompatReport()

    try:
        report.picker_patched = patch_tools_config_picker()
    except Exception as exc:  # pragma: no cover - defensive plugin boundary
        report.errors.append(f"picker patch failed: {exc}")

    try:
        report.config_changed = ensure_recommended_web_config()
    except Exception as exc:  # pragma: no cover - defensive plugin boundary
        report.errors.append(f"config update failed: {exc}")

    return report
