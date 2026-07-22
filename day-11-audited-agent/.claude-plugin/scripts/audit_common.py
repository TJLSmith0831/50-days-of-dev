"""Shared helpers for the audit-plugin hooks: path resolution + byte/truncate."""

from __future__ import annotations

import json
import os
from pathlib import Path

MAX_FIELD_CHARS = 2000  # ponytail: cap stored inputs/outputs for readable JSONL; bytes measured on the full value


def plugin_root() -> Path:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT")
    if root:
        return Path(root)
    return Path(__file__).resolve().parent.parent  # scripts/ -> plugin root


def data_dir() -> Path:
    override = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("PLUGIN_DATA")
    path = Path(override) if override else plugin_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def session_paths(session_id: str, base: Path | None = None) -> dict[str, Path]:
    base = base or data_dir()
    sid = session_id or "unknown-session"
    return {
        "jsonl": base / f"{sid}.jsonl",
        "pending": base / f"{sid}.pending.json",
        "report": base / f"{sid}.report.md",
    }


def sizeof(value) -> int:
    """Byte size of a value's JSON form — an honest per-tool data-volume proxy."""
    return len(json.dumps(value, default=str, ensure_ascii=False).encode("utf-8"))


def truncate(value, limit: int = MAX_FIELD_CHARS):
    """Cap a value's stored string form so a single JSONL line stays readable."""
    s = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    if len(s) <= limit:
        return value
    return s[:limit] + f"... [truncated {len(s) - limit} chars]"
