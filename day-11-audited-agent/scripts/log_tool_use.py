"""PreToolUse/PostToolUse hook: stamp a start time, then append one audit record.

Reads the hook payload as JSON on stdin and dispatches on `hook_event_name`.
PreToolUse records a wall-clock start per tool_use_id; PostToolUse writes the
JSONL entry (with duration + status). Never raises — a logging hook must not
break the agent session.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import session_paths, sizeof, truncate  # noqa: E402


def _load_pending(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _derive_status(tool_response) -> str:
    # ponytail: heuristic — Claude Code has no failure event, so infer from the
    # response shape. Upgrade path: match specific tools' error schemas if a
    # false positive/negative ever matters.
    if isinstance(tool_response, dict) and (tool_response.get("error") or tool_response.get("is_error")):
        return "error"
    if isinstance(tool_response, str) and tool_response.lower().startswith("error"):
        return "error"
    return "success"


def build_entry(payload: dict, pending: dict, now: float | None = None) -> dict:
    """Pure: build one audit record from a PostToolUse payload + pending starts."""
    now = time.time() if now is None else now
    tool_use_id = payload.get("tool_use_id", "")
    inputs = payload.get("tool_input", {})
    outputs = payload.get("tool_response", {})
    start = pending.get(tool_use_id)
    if isinstance(start, dict):  # PreToolUse stores a richer stub; older/test form is a bare float
        start = start.get("start")
    duration_ms = round((now - start) * 1000, 1) if isinstance(start, (int, float)) else None
    return {
        "timestamp": datetime.fromtimestamp(now, timezone.utc).isoformat(),
        "session_id": payload.get("session_id", ""),
        "tool_name": payload.get("tool_name", ""),
        "tool_use_id": tool_use_id,
        "inputs": truncate(inputs),
        "outputs": truncate(outputs),
        "input_bytes": sizeof(inputs),
        "output_bytes": sizeof(outputs),
        "duration_ms": duration_ms,
        "status": _derive_status(outputs),
    }


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return
    paths = session_paths(payload.get("session_id", ""))
    pending = _load_pending(paths["pending"])
    tool_use_id = payload.get("tool_use_id", "")

    if payload.get("hook_event_name") == "PreToolUse":
        # Store enough to reconstruct the call if no PostToolUse ever fires
        # (Claude Code emits no post event on a hard tool failure — the Stop hook
        # reconciles these leftovers into the trail as errors).
        # ponytail: pending.json is last-writer-wins; parallel tool calls could
        # drop a start stamp. Upgrade to per-call files only if that matters.
        inputs = payload.get("tool_input", {})
        pending[tool_use_id] = {
            "start": time.time(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": payload.get("tool_name", ""),
            "inputs": truncate(inputs),
            "input_bytes": sizeof(inputs),
        }
        paths["pending"].write_text(json.dumps(pending))
        return

    entry = build_entry(payload, pending)
    with paths["jsonl"].open("a") as f:
        f.write(json.dumps(entry) + "\n")
    pending.pop(tool_use_id, None)
    paths["pending"].write_text(json.dumps(pending))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # ponytail: never break the session on a logging failure
    sys.exit(0)
