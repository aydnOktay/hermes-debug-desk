"""Process-wide PluginContext handle for hooks, tools, and the dashboard API."""

from __future__ import annotations

_CTX = None


def set_ctx(ctx) -> None:
    global _CTX
    _CTX = ctx


def get_ctx():
    return _CTX
