#!/usr/bin/env python3
"""Run Brave Search Pro doctor checks from a git plugin checkout."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path


def _hermes_python() -> str | None:
    hermes = shutil.which("hermes")
    if not hermes:
        return None
    try:
        first_line = Path(hermes).read_text(encoding="utf-8").splitlines()[0]
    except (OSError, IndexError, UnicodeDecodeError):
        return None
    if not first_line.startswith("#!"):
        return None
    python = first_line[2:].strip().split()[0]
    if python and Path(python).exists():
        return python
    return None


if importlib.util.find_spec("hermes_cli") is None:
    python = _hermes_python()
    if python and Path(python).resolve() != Path(sys.executable).resolve():
        os.execv(python, [python, *sys.argv])

src = Path(__file__).resolve().parents[1] / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from hermes_brave_search.doctor import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
