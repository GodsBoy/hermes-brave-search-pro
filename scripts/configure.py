#!/usr/bin/env python3
"""Run the Brave Search Pro configuration helper from a git plugin checkout."""

from __future__ import annotations

import sys
from pathlib import Path

scripts = Path(__file__).absolute().parent
if str(scripts) not in sys.path:
    sys.path.insert(0, str(scripts))

from doctor import (  # noqa: E402
    _reexec_with_hermes_python,
    _set_installed_hermes_home,
)


def _run() -> int:
    _set_installed_hermes_home()
    _reexec_with_hermes_python()

    src = scripts.parent / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from hermes_brave_search.configure import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
