"""Doctor checks for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass

from .compat import (
    BRAVE_PRO_BACKEND,
    TAVILY_API_KEY_ENV,
    TAVILY_BACKEND,
    _get_env_value,
    _has_brave_api_key,
    _suspend_runtime_compat_writes,
    apply_runtime_compat,
)
from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    blocking: bool = True

    @property
    def mark(self) -> str:
        if self.ok:
            return "✓"
        return "✗" if self.blocking else "!"


def _load_config() -> dict:
    try:
        from hermes_cli.config import load_config  # type: ignore

        config = load_config()
    except Exception:
        return {}
    return config if isinstance(config, dict) else {}


def _plugin_statuses() -> dict[str, bool] | None:
    try:
        result = subprocess.run(
            ["hermes", "plugins", "list", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    try:
        plugins = json.loads(result.stdout)
    except ValueError:
        return None
    if not isinstance(plugins, list):
        return None

    statuses: dict[str, bool] = {}
    for plugin in plugins:
        if not isinstance(plugin, dict):
            continue
        name = plugin.get("name")
        if isinstance(name, str):
            statuses[name] = plugin.get("status") == "enabled"
    return statuses


def _plugin_enabled(statuses: dict[str, bool] | None, name: str) -> bool | None:
    if statuses is None:
        return None
    return statuses.get(name, False)


def _tavily_provider_status() -> bool | None:
    """Return whether Hermes' bundled Tavily provider is ready for extraction.

    Provider registration is owned by Hermes' web provider registry, so this
    check must not infer readiness from a plugin name in the CLI list. Hermes
    versions that expose web-plugin discovery are loaded before the registry
    lookup; unavailable APIs or discovery failures are reported as unknown.
    """

    try:
        from agent.web_search_registry import get_provider
    except Exception:
        return None

    try:
        from plugins.web.tavily.provider import TavilyWebSearchProvider
    except ModuleNotFoundError as exc:
        if exc.name == "plugins.web.tavily.provider":
            return False
        return None
    except Exception:
        return None

    try:
        from tools.web_tools import _ensure_web_plugins_loaded, _provider_is_ready
    except Exception:
        return None

    if not callable(_ensure_web_plugins_loaded) or not callable(_provider_is_ready):
        return None

    try:
        with _suspend_runtime_compat_writes():
            _ensure_web_plugins_loaded()
        provider = get_provider(TAVILY_BACKEND)
        if not isinstance(provider, TavilyWebSearchProvider):
            return False
        supports_extract = getattr(provider, "supports_extract", None)
        if not callable(supports_extract):
            return False
        if not supports_extract():
            return False
        return bool(_provider_is_ready(provider))
    except Exception:
        return None


def _tool_override_allowed(config: dict) -> bool:
    try:
        from hermes_cli.plugin_capabilities import plugin_capability_granted
    except Exception:
        plugins = config.get("plugins", {})
        if not isinstance(plugins, dict):
            return False
        entries = plugins.get("entries", {})
        if not isinstance(entries, dict):
            return False
        brave_entry = entries.get("brave-search", {})
        if not isinstance(brave_entry, dict):
            return False
        granted = brave_entry.get("granted_capabilities", [])
        return (
            isinstance(granted, list)
            and "tools.override" in granted
        ) or brave_entry.get("allow_tool_override") is True

    return plugin_capability_granted(
        "brave-search",
        "tools.override",
        config=config,
    )


def _plugin_check(
    name: str,
    enabled: bool | None,
    enable_command: str,
    *,
    blocking: bool = True,
) -> Check:
    if enabled is True:
        detail = "enabled"
    elif enabled is False:
        detail = f"not enabled. Run: {enable_command}"
    else:
        detail = "unable to verify. Run: hermes plugins list"
    return Check(f"{name} plugin", enabled is True, detail, blocking=blocking)


def _tavily_provider_check(
    status: bool | None,
    *,
    blocking: bool,
) -> Check:
    if status is True:
        detail = (
            "Hermes-bundled provider is registered, supports extraction, and is "
            "ready"
        )
    elif status is False:
        detail = (
            "Hermes-bundled provider is not registered, does not support "
            "extraction, or is not ready. Run: hermes tools"
        )
    else:
        detail = "unable to verify. Run: hermes tools"
    return Check("tavily provider", status is True, detail, blocking=blocking)


def run_checks() -> list[Check]:
    config = _load_config()
    web = config.get("web", {})
    if not isinstance(web, dict):
        web = {}

    statuses = _plugin_statuses()
    brave_enabled = _plugin_enabled(statuses, "brave-search")
    tavily_provider_status = _tavily_provider_status()
    brave_key = _has_brave_api_key()
    tavily_key = bool(_get_env_value(TAVILY_API_KEY_ENV))
    override_allowed = _tool_override_allowed(config)
    search_backend = web.get("search_backend")
    extract_backend = web.get("extract_backend")
    tavily_selected = extract_backend == TAVILY_BACKEND
    extract_configured = isinstance(extract_backend, str) and bool(
        extract_backend.strip()
    )

    return [
        Check(
            f"{BRAVE_API_KEY_ENV} or {BRAVE_API_KEY_COMPAT_ENV}",
            brave_key,
            "present" if brave_key else "missing. Get one from https://brave.com/search/api/",
        ),
        _plugin_check(
            "brave-search",
            brave_enabled,
            "hermes plugins enable brave-search",
        ),
        Check(
            "brave-search tool override",
            override_allowed,
            "granted"
            if override_allowed
            else (
                "missing. Run: hermes plugins enable brave-search, then grant "
                "tools.override when prompted"
            ),
        ),
        Check(
            TAVILY_API_KEY_ENV,
            tavily_key,
            "present"
            if tavily_key
            else (
                "missing. Optional: Hermes-bundled Tavily supports keyless "
                "web_extract when selected."
            ),
            blocking=False,
        ),
        _tavily_provider_check(
            tavily_provider_status,
            blocking=tavily_selected,
        ),
        Check(
            "web.search_backend",
            search_backend == BRAVE_PRO_BACKEND,
            f"{search_backend!r}" if search_backend else "not set",
        ),
        Check(
            "web.extract_backend",
            extract_configured,
            f"{extract_backend!r}" if extract_configured else "not set",
            blocking=False,
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Hermes Brave Search Pro and bundled Tavily setup.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Apply a safe Brave Pro web.search_backend default when a Brave "
            "API key is present."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --fix, overwrite existing web provider settings.",
    )
    args = parser.parse_args(argv)

    if args.fix:
        report = apply_runtime_compat(force=args.force)
        if report.config_changed:
            print("Updated Hermes config: " + ", ".join(report.config_changed))
        else:
            print("No config changes were needed or possible.")
        for error in report.errors:
            print(f"Warning: {error}")

    print("\nBrave Search Pro doctor")
    checks = run_checks()
    for check in checks:
        advisory = " [advisory]" if not check.ok and not check.blocking else ""
        print(f"{check.mark} {check.name}: {check.detail}{advisory}")

    if any(not check.ok and check.blocking for check in checks):
        print("\nNext steps:")
        print(
            "- Missing API keys can be added during plugin install or in "
            "~/.hermes/.env."
        )
        print(
            "- Run hermes plugins enable brave-search, then grant the declared "
            "tools.override capability and restart the gateway."
        )
        print(
            "- Run with --fix after adding keys to apply the recommended "
            "provider config."
        )
        print(
            "- Run hermes plugins capabilities brave-search to review consent, "
            "then run hermes tools to verify bundled Tavily supports web_extract."
        )
        print("- Restart the gateway after changing plugin, env, or provider config.")
        return 1

    print("\nAll required Brave Search Pro checks passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
