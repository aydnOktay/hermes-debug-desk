# debug-desk

Hermes plugin: **today's git digest** plus the **last failed terminal command** the agent ran. Optional summary uses the user's active model (`ctx.llm`). Desktop pane + status chip.

Does not watch VS Code, PowerShell, or any terminal outside Hermes.

## Install

From this folder (or a git remote later):

```bash
hermes plugins install .
hermes plugins enable debug-desk
```

Restart the gateway. In Desktop: **Capabilities → Plugins** and enable **Debug Desk** (the UI half is a separate switch).

Slash:

```
/debug-desk today
/debug-desk last
/debug-desk last summarize
```

Agent tools: `debug_daily_report`, `debug_last_failure`.

## Layout

```
plugin.yaml
__init__.py              # register() — tools, hook, slash, skill
desk_tools.py            # handlers (JSON string, never raise)
desk_hooks.py            # post_tool_call on terminal / process
desk_context.py
store.py                 # git + redacted failure state
schemas.py
skills/debug-desk/SKILL.md
dashboard/manifest.json
dashboard/plugin_api.py  # /api/plugins/debug-desk/board
desktop/plugin.js        # pane + status chip (no JSX)
```

State lives in `$HERMES_HOME/plugin-data/debug-desk/state.json`, not in the install tree.

## v1 rules

- Git report is deterministic (`git log --since=midnight`). No LLM.
- Failures: nonzero exit or traceback-like output. Last 8 lines, secrets redacted, 120s debounce.
- Status chip turns red if a failure is less than 15 minutes old.
- "Refresh summary" calls the active model; if `ctx.llm` is missing it shows the raw lines.

## Doctor

```bash
hermes plugins doctor . --ci
```
