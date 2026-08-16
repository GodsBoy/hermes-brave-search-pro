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


def _tool_override_allowed(config: dict) -> bool:
    plugins = config.get("plugins", {})
    if not isinstance(plugins, dict):
        return False
    entries = plugins.get("entries", {})
    if not isinstance(entries, dict):
        return False
    brave_entry = entries.get("brave-search", {})
    return (
        isinstance(brave_entry, dict)
        and brave_entry.get("allow_tool_override") is True
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


def run_checks() -> list[Check]:
    config = _load_config()
    web = config.get("web", {})
    if not isinstance(web, dict):
        web = {}

    statuses = _plugin_statuses()
    brave_enabled = _plugin_enabled(statuses, "brave-search")
    web_tavily_enabled = _plugin_enabled(statuses, "web-tavily")
    brave_key = _has_brave_api_key()
    tavily_key = bool(_get_env_value(TAVILY_API_KEY_ENV))
    override_allowed = _tool_override_allowed(config)
    backend = web.get("backend")
    search_backend = web.get("search_backend")
    extract_backend = web.get("extract_backend")
    tavily_selected = extract_backend == TAVILY_BACKEND

    return [
        Check(
            f"{BRAVE_API_KEY_ENV} or {BRAVE_API_KEY_COMPAT_ENV}",
            brave_key,
            "present" if brave_key else "missing. Get one from https://brave.com/search/api/",
        ),
        _plugin_check(
            "brave-search",
            brave_enabled,
            "hermes plugins enable brave-search --allow-tool-override",
        ),
        Check(
            "brave-search tool override",
            override_allowed,
            "granted"
            if override_allowed
            else (
                "missing. Run: hermes plugins enable brave-search "
                "--allow-tool-override"
            ),
        ),
        Check(
            TAVILY_API_KEY_ENV,
            tavily_key,
            "present"
            if tavily_key
            else "missing. Recommended for web_extract. Free key: https://app.tavily.com/",
            blocking=tavily_selected,
        ),
        _plugin_check(
            "web-tavily",
            web_tavily_enabled,
            "hermes plugins enable web-tavily",
            blocking=tavily_selected,
        ),
        Check(
            "web.backend",
            backend == BRAVE_PRO_BACKEND,
            f"{backend!r}" if backend else "not set",
        ),
        Check(
            "web.search_backend",
            search_backend == BRAVE_PRO_BACKEND,
            f"{search_backend!r}" if search_backend else "not set",
        ),
        Check(
            "web.extract_backend",
            extract_backend == TAVILY_BACKEND,
            f"{extract_backend!r}" if extract_backend else "not set",
            blocking=tavily_selected,
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Hermes Brave Search Pro and Tavily extraction setup.",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Apply safe provider config defaults: Brave Pro for search and Tavily "
            "for extraction when the relevant API keys are present."
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
        advisory = " [advisory]" if not check.blocking else ""
        print(f"{check.mark} {check.name}: {check.detail}{advisory}")

    if any(not check.ok and check.blocking for check in checks):
        print("\nNext steps:")
        print(
            "- Missing API keys can be added during plugin install or in "
            "~/.hermes/.env."
        )
        print(
            "- Run hermes plugins enable brave-search --allow-tool-override, "
            "then restart the gateway."
        )
        print(
            "- Run with --fix after adding keys to apply the recommended "
            "provider config."
        )
        print("- Run hermes plugins enable web-tavily to use Tavily web_extract.")
        print("- Restart the gateway after changing plugin, env, or provider config.")
        return 1

    print("\nAll required Brave Search Pro checks passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
