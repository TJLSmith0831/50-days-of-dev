"""Stop hook: render the session audit report to stdout + a markdown file.

Reads the session JSONL, optionally augments with ccusage token/cost totals,
prints a formatted table, and writes a markdown copy. Never crashes the session.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import session_paths  # noqa: E402


def _read_entries(path: Path) -> list[dict]:
    entries: list[dict] = []
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return entries
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def _fmt_ms(v) -> str:
    return f"{v:.1f}" if isinstance(v, (int, float)) else "-"


def render_report(entries: list[dict], usage: dict | None = None) -> tuple[str, str]:
    """Pure: build (plain-text report, markdown report) from audit entries."""
    if not entries:
        msg = "No tool calls recorded for this session."
        return msg, f"# Audit Trail\n\n{msg}\n"

    session_id = entries[0].get("session_id", "unknown")
    rows = [
        (
            str(i + 1),
            e.get("tool_name", "?"),
            str(e.get("input_bytes", 0)),
            str(e.get("output_bytes", 0)),
            _fmt_ms(e.get("duration_ms")),
            e.get("status", "?"),
        )
        for i, e in enumerate(entries)
    ]
    headers = ("#", "tool", "in_bytes", "out_bytes", "ms", "status")
    widths = [max(len(headers[c]), *(len(r[c]) for r in rows)) for c in range(len(headers))]

    def line(cells) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells))

    total_in = sum(e.get("input_bytes", 0) for e in entries)
    total_out = sum(e.get("output_bytes", 0) for e in entries)
    errors = sum(1 for e in entries if e.get("status") == "error")

    text_lines = [
        f"Audit Trail — session {session_id}",
        f"{len(entries)} tool calls · {total_in} in / {total_out} out bytes · {errors} errors",
        "",
        line(headers),
        line(tuple("-" * w for w in widths)),
        *(line(r) for r in rows),
    ]
    md_lines = [
        f"# Audit Trail — session `{session_id}`",
        "",
        f"- **Tool calls:** {len(entries)}",
        f"- **Bytes:** {total_in} in / {total_out} out",
        f"- **Errors:** {errors}",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(r) + " |" for r in rows),
    ]

    if usage:
        summary = (
            f"tokens in {usage.get('input')} / out {usage.get('output')}"
            f" · cache {usage.get('cache_read')} read / {usage.get('cache_write')} write"
            f" · cost ${usage.get('cost')}"
        )
        text_lines += ["", f"Session usage (ccusage): {summary}"]
        md_lines += ["", "## Session usage (ccusage)", "", summary]

    return "\n".join(text_lines), "\n".join(md_lines) + "\n"


def fetch_usage(session_id: str) -> dict | None:
    """Best-effort ccusage totals for this session; None if unavailable."""
    try:
        out = subprocess.run(
            ["ccusage", "session", "--json"],
            capture_output=True, text=True, timeout=15, check=True,
        ).stdout
        data = json.loads(out)
    except Exception:
        return None  # ponytail: ccusage is optional; degrade to the tool trail only
    sessions = data.get("sessions", data) if isinstance(data, dict) else data
    if not isinstance(sessions, list):
        return None
    for s in sessions:
        if session_id and session_id in json.dumps(s, default=str):
            return {
                "input": s.get("inputTokens"),
                "output": s.get("outputTokens"),
                "cache_read": s.get("cacheReadTokens"),
                "cache_write": s.get("cacheCreationTokens"),
                "cost": s.get("totalCost"),
            }
    return None


def incomplete_entries(pending: dict, session_id: str) -> list[dict]:
    """Records for calls that started (PreToolUse) but never completed a
    PostToolUse — i.e. tools that failed or were interrupted. Claude Code fires
    no post event for a hard tool failure, so the leftover pending stubs are the
    only trace; surface them as status 'error' rather than silently dropping."""
    out = []
    for tid, info in pending.items():
        info = info if isinstance(info, dict) else {"start": info}
        out.append({
            "timestamp": info.get("timestamp", ""),
            "session_id": session_id,
            "tool_name": info.get("tool_name", ""),
            "tool_use_id": tid,
            "inputs": info.get("inputs", {}),
            "outputs": None,
            "input_bytes": info.get("input_bytes", 0),
            "output_bytes": 0,
            "duration_ms": None,  # we know the start, not when it failed
            "status": "error",
        })
    return out


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    session_id = payload.get("session_id", "")
    paths = session_paths(session_id)
    entries = _read_entries(paths["jsonl"])

    # Reconcile any in-flight calls that never got a PostToolUse (failed/interrupted).
    try:
        pending = json.loads(paths["pending"].read_text())
    except (OSError, ValueError):
        pending = {}
    dropped = incomplete_entries(pending, session_id)
    if dropped:
        try:
            with paths["jsonl"].open("a") as f:
                for e in dropped:
                    f.write(json.dumps(e) + "\n")
            paths["pending"].unlink()
        except OSError:
            pass
        entries += dropped

    usage = fetch_usage(session_id) if entries else None
    text, md = render_report(entries, usage)
    print(text)
    try:
        paths["report"].write_text(md)
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # ponytail: a broken report must not crash the session
    sys.exit(0)
