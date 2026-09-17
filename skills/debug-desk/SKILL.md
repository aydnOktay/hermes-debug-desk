---
name: debug-desk
description: >
  Load when the user wants today's git activity, a standup digest, or an
  explanation of the last terminal/test/build failure the agent ran.
---

# Debug Desk

This plugin watches Hermes `terminal` / `process` tool calls. It does **not**
see the user's VS Code or PowerShell session.

## Tools

- `debug_daily_report` — git log since local midnight. No LLM. Pass `cwd` if
  the workspace is not the repo root.
- `debug_last_failure` — last captured fail (command, exit code, last 8
  redacted lines). Set `summarize: true` only when the user asks for a
  written explanation.

## Slash

- `/debug-desk today`
- `/debug-desk last`
- `/debug-desk last summarize`

## Rules

1. Prefer the tools over re-running `git log` in the terminal.
2. Never dump a full git history or unredacted env/secrets.
3. If there is no captured failure, say so; do not invent one.
4. The Desktop pane reads the same state; you do not need to format a UI.
