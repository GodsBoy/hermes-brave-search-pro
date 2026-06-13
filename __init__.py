"""Directory-plugin shim for Hermes user plugin installs.

This file lets the repository root be copied or symlinked into
`~/.hermes/plugins/brave-search/` while the actual package code remains in
`src/hermes_brave_search`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from hermes_brave_search import register  # noqa: E402,F401
