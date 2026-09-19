"""Dashboard/Desktop backend — mounted at /api/plugins/debug-desk/."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

_ROOT = Path(__file__).resolve().parent.parent
_root_str = str(_ROOT)
if _root_str in sys.path:
    sys.path.remove(_root_str)
sys.path.insert(0, _root_str)

import desk_store  # noqa: E402
import desk_tools  # noqa: E402

router = APIRouter()


def _board_payload(cwd: str | None) -> dict:
    report = (
        desk_store.daily_git_report(cwd)
        if cwd
        else {"ok": False, "error": "No working directory yet."}
    )
    failure = desk_store.get_last_failure()
    return {
        "git": report,
        "failure": failure,
        "fresh": desk_store.failure_is_fresh(failure),
    }


@router.get("/board")
async def board(cwd: str | None = None) -> dict:
    return _board_payload(cwd)


@router.post("/summarize")
async def summarize() -> dict:
    record = desk_store.get_last_failure()
    return desk_tools.summarize_failure(record)
