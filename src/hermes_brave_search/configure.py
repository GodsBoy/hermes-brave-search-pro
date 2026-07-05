"""Command-line configuration helper for Hermes Brave Search Pro."""

from __future__ import annotations

import argparse

from .compat import ensure_recommended_web_config, patch_tools_config_picker


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

    changed = ensure_recommended_web_config(force=args.force)

    if changed:
        print("Updated Hermes config: " + ", ".join(changed))
    else:
        print("Hermes Brave Search Pro config already looks correct.")

    if patch_tools_config_picker():
        print("Applied Brave Pro provider-picker compatibility shim for this process.")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
