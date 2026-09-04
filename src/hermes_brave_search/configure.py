"""Command-line configuration helper for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse

from .compat import apply_runtime_compat


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Configure Hermes web search routing for Brave Search Pro. Existing "
            "extraction settings are preserved; select bundled Tavily explicitly "
            "when desired."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite existing web search routing with Brave Search Pro. Existing "
            "extraction settings are preserved; select bundled Tavily explicitly "
            "when desired."
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
        print(
            "Hermes Brave Search Pro config already looks correct; optional "
            "Tavily extraction remains separate."
        )

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
