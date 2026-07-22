"""Tests for the audit-plugin hook logic — real sample payloads, no mocks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from log_tool_use import build_entry, _derive_status  # noqa: E402
from report import render_report, incomplete_entries  # noqa: E402


def test_build_entry_measures_duration_and_sizes():
    payload = {
        "session_id": "s1",
        "tool_name": "Read",
        "tool_use_id": "u1",
        "tool_input": {"file_path": "a.py"},
        "tool_response": {"content": "x" * 100},
    }
    entry = build_entry(payload, pending={"u1": 1000.0}, now=1000.5)
    assert entry["tool_name"] == "Read"
    assert entry["duration_ms"] == 500.0
    assert entry["input_bytes"] > 0 and entry["output_bytes"] > 0
    assert entry["status"] == "success"
    assert entry["session_id"] == "s1"


def test_build_entry_null_duration_when_unpaired():
    payload = {"tool_use_id": "u2", "tool_name": "Bash", "tool_response": {}}
    entry = build_entry(payload, pending={}, now=10.0)
    assert entry["duration_ms"] is None


def test_build_entry_reads_start_from_dict_pending():
    payload = {"tool_use_id": "u1", "tool_name": "Read", "tool_response": {}}
    entry = build_entry(payload, pending={"u1": {"start": 2.0}}, now=2.25)
    assert entry["duration_ms"] == 250.0


def test_incomplete_entries_marks_dropped_calls_as_error():
    pending = {
        "u9": {
            "start": 5.0,
            "timestamp": "2026-07-22T00:00:00+00:00",
            "tool_name": "Bash",
            "inputs": {"command": "boom"},
            "input_bytes": 20,
        }
    }
    out = incomplete_entries(pending, "s1")
    assert len(out) == 1
    assert out[0]["status"] == "error"
    assert out[0]["tool_name"] == "Bash"
    assert out[0]["duration_ms"] is None
    assert out[0]["session_id"] == "s1"


def test_error_status_from_response():
    assert _derive_status({"is_error": True}) == "error"
    assert _derive_status({"error": "boom"}) == "error"
    assert _derive_status("Error: nope") == "error"
    assert _derive_status({"content": "ok"}) == "success"


def test_render_report_table_and_totals():
    entries = [
        {"session_id": "s1", "tool_name": "Glob", "input_bytes": 10, "output_bytes": 20, "duration_ms": 1.2, "status": "success"},
        {"session_id": "s1", "tool_name": "Bash", "input_bytes": 5, "output_bytes": 8, "duration_ms": 3.4, "status": "error"},
    ]
    text, md = render_report(entries)
    assert "Glob" in text and "Bash" in text
    assert "2 tool calls" in text
    assert "1 errors" in text
    assert md.startswith("# Audit Trail")
    assert "| Bash |" in md


def test_render_report_empty_is_graceful():
    text, md = render_report([])
    assert "No tool calls" in text
    assert "No tool calls" in md
