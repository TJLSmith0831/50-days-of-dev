"""Offline self-check: drive the real hook scripts with sample events, no IDE.

Pipes PreToolUse + PostToolUse (success and error) then a Stop payload through
the actual hook scripts in a temp data dir, asserts the JSONL + report, and
prints the rendered report. Run: `uv run demo.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "scripts" / "log_tool_use.py"
REPORT = ROOT / "scripts" / "report.py"
SESSION = "demo-session"


def run(script: Path, payload: dict, env: dict) -> str:
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True, text=True, env=env,
    ).stdout


def event(name, tool, tid, tool_input=None, tool_response=None) -> dict:
    return {
        "hook_event_name": name,
        "session_id": SESSION,
        "tool_name": tool,
        "tool_use_id": tid,
        "tool_input": tool_input or {},
        "tool_response": tool_response or {},
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "PLUGIN_DATA": tmp}
        completed = [
            ("Glob", "t1", {"pattern": "*.py"}, {"files": ["a.py", "b.py"]}),
            ("Read", "t2", {"file_path": "a.py"}, {"content": "print('hi')\n" * 20}),
            ("Bash", "t3", {"command": "grep foo a.py"}, {"is_error": True, "error": "grep: no match"}),
        ]
        for tool, tid, tin, tout in completed:
            run(LOG, event("PreToolUse", tool, tid, tin), env)
            run(LOG, event("PostToolUse", tool, tid, tin, tout), env)
        # A tool that starts but never completes — a hard failure fires no
        # PostToolUse in Claude Code; the Stop hook must reconcile it as an error.
        run(LOG, event("PreToolUse", "Bash", "t4", {"command": "does_not_exist_xyz"}), env)

        report_out = run(REPORT, {"hook_event_name": "Stop", "session_id": SESSION}, env)
        entries = {
            json.loads(line)["tool_use_id"]: json.loads(line)
            for line in (Path(tmp) / f"{SESSION}.jsonl").read_text().splitlines()
        }
        assert len(entries) == 4, f"expected 4 entries, got {len(entries)}"
        assert all(entries[t]["duration_ms"] is not None for t in ("t1", "t2", "t3")), "duration not measured"
        assert entries["t3"]["status"] == "error", "response-flagged failure not caught"
        assert entries["t4"]["status"] == "error", "dropped (no-PostToolUse) failure not reconciled"
        assert entries["t2"]["output_bytes"] > 0, "output bytes not measured"

        assert "Audit Trail" in report_out, "report did not render"
        assert (Path(tmp) / f"{SESSION}.report.md").exists(), "markdown report not written"

        print(report_out)
        print("\n[demo] OK — 4 calls logged (incl. 1 reconciled failure), duration measured, errors flagged, report written.")


if __name__ == "__main__":
    main()
