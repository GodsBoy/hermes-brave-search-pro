"""Doctor checks for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from .compat import (
    BRAVE_PRO_BACKEND,
    TAVILY_API_KEY_ENV,
    TAVILY_BACKEND,
    _get_env_value,
    _has_brave_api_key,
    apply_runtime_compat,
    ensure_recommended_web_config,
)
from .constants import BRAVE_API_KEY_COMPAT_ENV, BRAVE_API_KEY_ENV


@dataclass
class Check:
    name: str
    ok: bool
    detail: str

    @property
    def mark(self) -> str:
        return "✓" if self.ok else "✗"


def _load_web_config() -> dict:
    try:
        from hermes_cli.config import load_config  # type: ignore

        config = load_config()
    except Exception:
        config = {}
    web = config.get("web", {}) if isinstance(config, dict) else {}
    return web if isinstance(web, dict) else {}


def run_checks() -> list[Check]:
    web = _load_web_config()
    brave_key = _has_brave_api_key()
    tavily_key = bool(_get_env_value(TAVILY_API_KEY_ENV))
    backend = web.get("backend")
    search_backend = web.get("search_backend")
    extract_backend = web.get("extract_backend")

    return [
        Check(
            f"{BRAVE_API_KEY_ENV} or {BRAVE_API_KEY_COMPAT_ENV}",
            brave_key,
            "present" if brave_key else "missing. Get one from https://brave.com/search/api/",
        ),
        Check(
            TAVILY_API_KEY_ENV,
            tavily_key,
            "present"
            if tavily_key
            else "missing. Recommended for web_extract. Free key: https://app.tavily.com/",
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
        changed = ensure_recommended_web_config(force=args.force)
        if changed:
            print("Updated Hermes config: " + ", ".join(changed))
        else:
            print("No config changes were needed or possible.")

    report = apply_runtime_compat()
    if report.picker_patched:
        print("Applied Brave Pro provider-picker compatibility shim for this process.")
    for error in report.errors:
        print(f"Warning: {error}")

    print("\nBrave Search Pro doctor")
    checks = run_checks()
    for check in checks:
        print(f"{check.mark} {check.name}: {check.detail}")

    failures = [check for check in checks if not check.ok]
    if failures:
        print("\nNext steps:")
        print(
            "- Missing API keys can be added during plugin install or in "
            "~/.hermes/.env."
        )
        print(
            "- Run with --fix after adding keys to apply the recommended "
            "provider config."
        )
        print("- Restart the gateway after changing plugin, env, or provider config.")
        return 1

    print("\nAll Brave Search Pro checks passed.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
