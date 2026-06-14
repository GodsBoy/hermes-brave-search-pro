"""Command-line configuration helper for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse

from .compat import apply_runtime_compat, ensure_recommended_web_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure Hermes to prefer Brave Search Pro for web search.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing web backend settings with Brave Pro and Tavily.",
    )
    args = parser.parse_args(argv)

    report = apply_runtime_compat()
    changed = list(report.config_changed)
    if args.force:
        forced = ensure_recommended_web_config(force=True)
        changed = sorted(set(changed + forced))

    if changed:
        print("Updated Hermes config: " + ", ".join(changed))
    else:
        print("Hermes Brave Search Pro config already looks correct.")

    if report.picker_patched:
        print("Applied Brave Pro provider-picker compatibility shim for this process.")

    for error in report.errors:
        print(f"Warning: {error}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
