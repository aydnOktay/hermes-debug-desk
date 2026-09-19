"""Local checks that do not require Hermes."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HERMES_HOME"] = tempfile.mkdtemp(prefix="debug-desk-test-")

import desk_hooks
import desk_tools
import desk_store


def test_redact() -> None:
    text = desk_store.redact("token=ghp_abcdefghijklmnopqrstuvwxyz0123 password=supersecret")
    assert "ghp_" not in text
    assert "supersecret" not in text
    assert "[REDACTED]" in text


def test_classify() -> None:
    assert desk_store.classify_subject("feat: add pane") == "feat"
    assert desk_store.classify_subject("WIP on the parser") == "wip"
    assert desk_store.classify_subject("hello") == "other"


def test_failure_capture() -> None:
    payload = json.dumps(
        {
            "command": "pytest -q",
            "exit_code": 1,
            "output": "FAILED tests/test_demo.py::test_x\nAssertionError: boom",
        }
    )
    desk_hooks.on_post_tool_call(
        "terminal",
        {"command": "pytest -q"},
        payload,
    )
    last = desk_store.get_last_failure()
    assert last is not None
    assert last["exit_code"] == 1
    assert last["command"] == "pytest -q"
    assert any("AssertionError" in ln for ln in last["lines"])


def test_ignore_success() -> None:
    desk_store.save_state({})
    desk_hooks.on_post_tool_call(
        "terminal",
        {"command": "echo ok"},
        json.dumps({"exit_code": 0, "output": "ok"}),
    )
    assert desk_store.get_last_failure() is None


def test_daily_report_this_repo() -> None:
    root = Path(__file__).resolve().parents[1]
    report = desk_store.daily_git_report(root)
    assert "ok" in report
    if report["ok"]:
        assert "commit_count" in report
        assert "types" in report


def test_tool_json() -> None:
    raw = desk_tools.debug_last_failure({}, foo="bar")
    data = json.loads(raw)
    assert "ok" in data


if __name__ == "__main__":
    test_redact()
    test_classify()
    test_failure_capture()
    test_ignore_success()
    test_daily_report_this_repo()
    test_tool_json()
    print("ok")
