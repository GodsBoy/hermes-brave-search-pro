"""Command-line configuration helper for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse

from .compat import apply_runtime_compat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Configure Hermes to prefer Brave Search Pro for web search.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite existing web backend settings with Brave Pro and Tavily "
            "extraction config. Enable web-tavily separately for web_extract."
        ),
    )
    args = parser.parse_args(argv)

    report = apply_runtime_compat(force=args.force)

    if report.errors:
        for error in report.errors:
            print(f"Error: {error}")
        return 1
    if report.config_changed:
        print("Updated Hermes config: " + ", ".join(report.config_changed))
    else:
        print("Hermes Brave Search Pro config already looks correct.")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
