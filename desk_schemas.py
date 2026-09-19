"""Tool schemas — what the LLM sees."""

DEBUG_DAILY_REPORT = {
    "name": "debug_daily_report",
    "description": (
        "Summarise today's git commits in a local repository (since local midnight). "
        "Returns commit count, conventional-commit type counts (feat/fix/wip/…), "
        "touched files, and recent subjects. Does not call a model. "
        "Use when the user asks what landed today, for a daily git digest, "
        "or before writing a standup note."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "cwd": {
                "type": "string",
                "description": "Repository path. Defaults to the current working directory.",
            }
        },
        "required": [],
    },
}

DEBUG_LAST_FAILURE = {
    "name": "debug_last_failure",
    "description": (
        "Return the last failed terminal/process command captured from this Hermes "
        "agent (exit code or traceback). Optionally summarise it with the user's "
        "active model via ctx.llm. Use when debugging a failed build/test the agent "
        "just ran, or when the user asks 'what broke'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "summarize": {
                "type": "boolean",
                "description": "If true, ask the active model for a short actionable summary.",
                "default": False,
            }
        },
        "required": [],
    },
}
