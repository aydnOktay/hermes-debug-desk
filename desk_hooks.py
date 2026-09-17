"""post_tool_call observer — capture failed terminal/process runs."""

from __future__ import annotations

import store

WATCH_TOOLS = {"terminal", "process"}


def on_post_tool_call(tool_name: str, args: dict, result: str, **kwargs) -> None:
    del kwargs
    try:
        if tool_name not in WATCH_TOOLS:
            return
        payload = store.parse_tool_payload(result)
        command = store.extract_command(args if isinstance(args, dict) else {}, payload)
        output = store.extract_output(payload)
        exit_code = store.extract_exit_code(payload)
        if not store.looks_like_failure(exit_code, output):
            return
        cwd = ""
        if isinstance(args, dict):
            raw_cwd = args.get("cwd") or args.get("working_directory") or payload.get("cwd")
            if isinstance(raw_cwd, str):
                cwd = raw_cwd
        store.record_failure(
            tool=tool_name,
            command=command or tool_name,
            exit_code=exit_code,
            cwd=cwd,
            lines=store.last_lines(output),
        )
    except Exception:
        return
