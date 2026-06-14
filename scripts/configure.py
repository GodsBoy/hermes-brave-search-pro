#!/usr/bin/env python3
"""Run the Brave Search Pro configuration helper from a git plugin checkout."""

from __future__ import annotations

import sys
from pathlib import Path

src = Path(__file__).resolve().parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from hermes_brave_search.configure import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
