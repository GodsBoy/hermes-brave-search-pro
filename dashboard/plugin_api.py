"""Hermes dashboard routes for the Brave Search Desktop plugin."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import APIRouter  # noqa: E402

from hermes_brave_search.desktop import search_desktop_web  # noqa: E402

router = APIRouter()


@router.post("/search")
def search(payload: dict[str, Any]) -> dict[str, Any]:
    """Search Brave web results through the active profile's plugin route."""

    return search_desktop_web(payload.get("query"))
