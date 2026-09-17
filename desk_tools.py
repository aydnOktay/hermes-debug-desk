"""Tool handlers — always return a JSON string, never raise."""

from __future__ import annotations

import json
import os
from typing import Any

import desk_context
import store


def _dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _cwd_from(args: dict[str, Any]) -> str:
    raw = args.get("cwd")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return os.getcwd()


def summarize_failure(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {"ok": False, "error": "No captured terminal failure yet."}

    ctx = desk_context.get_ctx()
    llm = getattr(ctx, "llm", None) if ctx is not None else None
    if llm is None:
        return {
            "ok": True,
            "failure": record,
            "summary": record.get("summary"),
            "llm": False,
            "note": "No plugin LLM context; showing captured lines only.",
        }

    command = record.get("command") or ""
    lines = record.get("lines") or []
    exit_code = record.get("exit_code")
    prompt = (
        f"Command: {command}\nExit: {exit_code}\n"
        + "\n".join(str(ln) for ln in lines)
    )
    try:
        result = llm.complete(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarise a failed terminal command for a developer. "
                        "Reply with at most 3 short sentences: what failed, likely cause, "
                        "one next step. No preamble, no secrets."
                    ),
                },
                {"role": "user", "content": prompt[:4000]},
            ],
            max_tokens=160,
            temperature=0.2,
            purpose="debug-desk.failure-summary",
        )
        text = (getattr(result, "text", None) or "").strip()
    except Exception as exc:  # noqa: BLE001 — never break the tool loop
        return {
            "ok": True,
            "failure": record,
            "summary": record.get("summary"),
            "llm": False,
            "error": f"LLM summary failed: {exc}",
        }

    if not text:
        return {
            "ok": True,
            "failure": record,
            "summary": record.get("summary"),
            "llm": False,
            "note": "Model returned an empty summary.",
        }

    updated = store.set_failure_summary(text) or record
    return {"ok": True, "failure": updated, "summary": text, "llm": True}


def debug_daily_report(args: dict, **kwargs) -> str:
    del kwargs
    try:
        report = store.daily_git_report(_cwd_from(args or {}))
        return _dumps(report)
    except Exception as exc:  # noqa: BLE001
        return _dumps({"ok": False, "error": str(exc)})


def debug_last_failure(args: dict, **kwargs) -> str:
    del kwargs
    try:
        record = store.get_last_failure()
        if not record:
            return _dumps({"ok": False, "error": "No captured terminal failure yet."})
        summarize = bool((args or {}).get("summarize"))
        if summarize:
            return _dumps(summarize_failure(record))
        return _dumps(
            {
                "ok": True,
                "failure": record,
                "fresh": store.failure_is_fresh(record),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _dumps({"ok": False, "error": str(exc)})
