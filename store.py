"""Durable state, git helpers, and secret redaction for debug-desk."""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLUGIN_ID = "debug-desk"
DEBOUNCE_SECONDS = 120
FRESH_FAIL_SECONDS = 15 * 60
MAX_LINES = 8
MAX_LINE_CHARS = 240
MAX_FILES = 40

_TYPE_RE = re.compile(
    r"^(feat|fix|wip|docs|chore|refactor|test|style|perf|build|ci)(\([^)]+\))?(!)?:\s*",
    re.IGNORECASE,
)

_SECRET_RES = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|authorization)\s*[:=]\s*\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"),
)

_FAIL_HINT = re.compile(
    r"(Traceback \(most recent call last\)|^(ERROR|FATAL|FAILED|FAILURE)\b|"
    r"Exception: |Error: |panic: |npm ERR!|FAILED tests/)",
    re.MULTILINE | re.IGNORECASE,
)


def data_dir() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir  # type: ignore

        return plugin_data_dir(PLUGIN_ID)
    except Exception:
        home = Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))
        path = home / "plugin-data" / PLUGIN_ID
        path.mkdir(parents=True, exist_ok=True)
        return path


def state_path() -> Path:
    return data_dir() / "state.json"


def load_state() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_state(state: dict[str, Any]) -> None:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(text: str) -> str:
    out = text or ""
    for pat in _SECRET_RES:
        out = pat.sub("[REDACTED]", out)
    return out


def last_lines(text: str, n: int = MAX_LINES) -> list[str]:
    cleaned = redact(text or "")
    lines = [ln.rstrip() for ln in cleaned.splitlines() if ln.strip()]
    clipped = [ln[:MAX_LINE_CHARS] for ln in lines[-n:]]
    return clipped


def parse_tool_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    if not isinstance(result, str) or not result.strip():
        return {}
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError:
        return {"output": result}
    return parsed if isinstance(parsed, dict) else {"output": result}


def extract_command(args: dict[str, Any], payload: dict[str, Any]) -> str:
    for key in ("command", "cmd", "shell_command"):
        val = args.get(key) or payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()[:500]
    argv = args.get("argv") or payload.get("argv")
    if isinstance(argv, list) and argv:
        return " ".join(str(x) for x in argv)[:500]
    return ""


def extract_exit_code(payload: dict[str, Any]) -> int | None:
    for key in ("exit_code", "exit", "returncode", "return_code"):
        val = payload.get(key)
        if isinstance(val, bool) or val is None:
            continue
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return None


def extract_output(payload: dict[str, Any]) -> str:
    for key in ("output", "stdout", "stderr", "result", "error"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return ""


def looks_like_failure(exit_code: int | None, output: str) -> bool:
    if exit_code is not None and exit_code != 0:
        return True
    return bool(output and _FAIL_HINT.search(output))


def failure_signature(command: str, exit_code: int | None, lines: list[str]) -> str:
    tail = lines[-1] if lines else ""
    return f"{command}|{exit_code}|{tail}"


def within_seconds(iso_ts: str | None, seconds: int) -> bool:
    if not iso_ts:
        return False
    try:
        then = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return False
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - then).total_seconds() < seconds


def record_failure(
    *,
    tool: str,
    command: str,
    exit_code: int | None,
    cwd: str,
    lines: list[str],
    debounce_seconds: int = DEBOUNCE_SECONDS,
) -> dict[str, Any] | None:
    signature = failure_signature(command, exit_code, lines)
    state = load_state()
    last = state.get("last_failure") if isinstance(state.get("last_failure"), dict) else {}
    if last.get("signature") == signature and within_seconds(last.get("ts"), debounce_seconds):
        last["repeat_count"] = int(last.get("repeat_count") or 1) + 1
        last["ts"] = now_iso()
        state["last_failure"] = last
        save_state(state)
        return last

    record = {
        "ts": now_iso(),
        "tool": tool,
        "command": redact(command),
        "exit_code": exit_code,
        "cwd": cwd,
        "lines": lines,
        "summary": None,
        "signature": signature,
        "repeat_count": 1,
    }
    state["last_failure"] = record
    save_state(state)
    return record


def get_last_failure() -> dict[str, Any] | None:
    state = load_state()
    last = state.get("last_failure")
    return last if isinstance(last, dict) and last.get("ts") else None


def set_failure_summary(summary: str) -> dict[str, Any] | None:
    state = load_state()
    last = state.get("last_failure")
    if not isinstance(last, dict):
        return None
    last["summary"] = summary.strip()
    state["last_failure"] = last
    save_state(state)
    return last


def find_git_root(start: Path) -> Path | None:
    try:
        cur = start.resolve()
    except OSError:
        return None
    if not cur.is_dir():
        return None
    for candidate in [cur, *cur.parents]:
        if (candidate / ".git").exists():
            return candidate
        if candidate.parent == candidate:
            break
    return None


def _git(repo: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    text = (proc.stdout or b"").decode("utf-8", "replace")
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()
        return proc.returncode, err or text
    return 0, text


def classify_subject(subject: str) -> str:
    match = _TYPE_RE.match(subject.strip())
    if match:
        return match.group(1).lower()
    lowered = subject.lower()
    if "wip" in lowered:
        return "wip"
    return "other"


def daily_git_report(cwd: str | Path | None) -> dict[str, Any]:
    if not cwd:
        return {"ok": False, "error": "No working directory given."}
    start = Path(str(cwd)).expanduser()
    root = find_git_root(start)
    if root is None:
        return {"ok": False, "error": f"Not a git repository: {start}"}

    code, branch_out = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_out.strip() if code == 0 else "unknown"

    code, subjects_out = _git(root, "log", "--since=midnight", "--pretty=format:%s")
    if code != 0:
        return {"ok": False, "error": subjects_out or "git log failed"}

    subjects = [ln.strip() for ln in subjects_out.splitlines() if ln.strip()]
    types: Counter[str] = Counter()
    for subject in subjects:
        types[classify_subject(subject)] += 1

    code, files_out = _git(root, "log", "--since=midnight", "--name-only", "--pretty=format:")
    files: list[str] = []
    if code == 0:
        seen: set[str] = set()
        for line in files_out.splitlines():
            name = line.strip().replace("\\", "/")
            if not name or name in seen:
                continue
            seen.add(name)
            files.append(name)
            if len(files) >= MAX_FILES:
                break

    return {
        "ok": True,
        "repo": str(root),
        "branch": branch,
        "since": "midnight (local)",
        "commit_count": len(subjects),
        "types": dict(types),
        "files": files,
        "subjects": subjects[:15],
    }


def failure_is_fresh(record: dict[str, Any] | None, seconds: int = FRESH_FAIL_SECONDS) -> bool:
    if not record:
        return False
    return within_seconds(record.get("ts"), seconds)
