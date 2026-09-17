"""debug-desk — git daily digest + last terminal failure for Hermes."""

from __future__ import annotations

import sys
from pathlib import Path

_DIR = str(Path(__file__).resolve().parent)
if _DIR not in sys.path:
    sys.path.append(_DIR)

import desk_context
import desk_hooks
import desk_tools
import schemas


def _handle_slash(ctx, raw_args: str) -> str:
    parts = (raw_args or "").strip().split()
    verb = parts[0].lower() if parts else "help"
    if verb in {"today", "git", "report"}:
        return ctx.dispatch_tool("debug_daily_report", {})
    if verb in {"last", "fail", "failure"}:
        summarize = len(parts) > 1 and parts[1].lower() in {"summarize", "llm", "summary"}
        return ctx.dispatch_tool("debug_last_failure", {"summarize": summarize})
    return (
        "Usage:\n"
        "  /debug-desk today     — git commits since local midnight\n"
        "  /debug-desk last      — last captured terminal failure\n"
        "  /debug-desk last summarize — same, with an LLM summary"
    )


def register(ctx) -> None:
    desk_context.set_ctx(ctx)

    ctx.register_tool(
        name="debug_daily_report",
        toolset="debug_desk",
        schema=schemas.DEBUG_DAILY_REPORT,
        handler=desk_tools.debug_daily_report,
    )
    ctx.register_tool(
        name="debug_last_failure",
        toolset="debug_desk",
        schema=schemas.DEBUG_LAST_FAILURE,
        handler=desk_tools.debug_last_failure,
    )
    ctx.register_hook("post_tool_call", desk_hooks.on_post_tool_call)
    try:
        ctx.register_command(
            "debug-desk",
            handler=lambda raw: _handle_slash(ctx, raw),
            description="Today's git digest or last terminal failure",
            args_hint="today|last [summarize]",
        )
    except TypeError:
        ctx.register_command(
            "debug-desk",
            handler=lambda raw: _handle_slash(ctx, raw),
            description="Today's git digest or last terminal failure",
        )

    skill_md = Path(__file__).parent / "skills" / "debug-desk" / "SKILL.md"
    if skill_md.is_file():
        try:
            ctx.register_skill("debug-desk", skill_md)
        except TypeError:
            ctx.register_skill("debug-desk", str(skill_md))
