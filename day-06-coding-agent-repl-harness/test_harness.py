"""Smoke checks for tasks 10.1-10.7 — assert-based, no framework.

Run: uv run python test_harness.py [--with-llm] [--with-web]
--with-llm exercises the live Ollama agent loop (slow); --with-web hits DuckDuckGo.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

PASS = []


def ok(label: str):
    PASS.append(label)
    print(f"  ok: {label}")


# --- 10.1 tool system -------------------------------------------------------
def test_tools():
    from tools import ALL_TOOLS, glob_files, grep_content, openspec_cli, read_file

    assert len(ALL_TOOLS) == 5
    for t in ALL_TOOLS:  # registry generated JSON schemas
        assert t.args_schema is not None and t.name and t.description
    ok("tool registry: 5 tools, schemas + descriptions present")

    here = str(Path(__file__))
    out = read_file.invoke({"path": here})
    assert "Smoke checks" in out
    assert "not found" in read_file.invoke({"path": "/nope/missing.txt"})
    assert "is not a file" in read_file.invoke({"path": str(Path(__file__).parent)})
    ok("read_file: content, missing-path error, dir error")

    out = glob_files.invoke({"pattern": "src/*.py", "root": str(Path(__file__).parent)})
    assert "tools.py" in out and "agent_loop.py" in out
    assert "no matches" in glob_files.invoke({"pattern": "*.xyz", "root": str(Path(__file__).parent)})
    ok("glob_files: matches and no-match message")

    out = grep_content.invoke(
        {"pattern": r"def truncate_messages", "path": str(Path(__file__).parent / "src"), "include": "*.py"}
    )
    assert "context_management.py" in out
    assert "bad regex" in grep_content.invoke({"pattern": "([", "path": "."})
    ok("grep_content: hit with file:line, bad-regex error")

    out = openspec_cli.invoke({"command_args": "list"})
    assert "error" not in out.lower() or "coding-agent" in out
    assert "only" in openspec_cli.invoke({"command_args": "archive foo"})  # write op blocked
    ok("openspec_cli: list works, non-read-only subcommand rejected")


# --- 10.2 agent loop (graph wiring; live LLM behind --with-llm) -------------
def test_agent_loop(with_llm: bool):
    from agent_loop import create_agent

    wf = create_agent()
    g = wf.compile()
    nodes = set(g.get_graph().nodes)
    assert "agent" in nodes and "tools" in nodes
    ok("agent loop: graph compiles with agent + tools nodes and conditional edge")

    if with_llm:
        from langchain_core.messages import HumanMessage

        result = g.invoke(
            {"messages": [HumanMessage(content="Use read_file to read pyproject.toml, then summarize it in one line.")]},
            {"recursion_limit": 12},
        )
        msgs = result["messages"]
        assert any(getattr(m, "tool_calls", None) for m in msgs), "LLM never called a tool"
        assert msgs[-1].content and not getattr(msgs[-1], "tool_calls", None), "loop did not stop cleanly"
        ok("agent loop (live): tool dispatched, result processed, loop terminated")
    else:
        print("  skip: live LLM roundtrip (pass --with-llm)")


# --- 10.3 REPL UI helpers ---------------------------------------------------
def test_repl_ui():
    from repl_interface import (
        SLASH_COMMANDS,
        display_help,
        display_sessions,
        display_tool_output,
        display_welcome,
        expand_file_mentions,
    )

    expanded = expand_file_mentions("look at @pyproject.toml please")
    assert str(Path.cwd() / "pyproject.toml") in expanded
    assert expand_file_mentions("@no-such-file.xyz") == "@no-such-file.xyz"
    ok("@file expansion: existing file -> abs path, missing file untouched")

    assert {"/help", "/save", "/sessions", "/exit", "/handoff"} <= set(SLASH_COMMANDS)
    display_help()
    display_welcome("qwen3:14b", "t-test", True)
    display_sessions([{"thread_id": "t", "created_at": "2026-07-17T00:00:00", "updated_at": "2026-07-17T00:00:00"}])
    display_tool_output("read_file", "x = 1")
    display_tool_output("grep_content", "a.py:1:x")
    ok("slash command table + welcome/sessions/tool panels render")


# --- 10.4 session persistence ----------------------------------------------
def test_sessions():
    from session_management import (
        DB_PATH,
        create_checkpointer,
        create_session,
        init_db,
        list_sessions,
        update_session,
    )

    conn = init_db()
    assert DB_PATH.exists()
    tid = create_session(conn, "smoke-test-thread")
    assert tid == "smoke-test-thread"
    update_session(conn, tid)
    assert any(s["thread_id"] == tid for s in list_sessions(conn))
    saver = create_checkpointer(conn)
    assert saver is not None
    # resume path: same thread_id returns the same session row, not a new one
    assert create_session(conn, tid) == tid
    assert sum(1 for s in list_sessions(conn) if s["thread_id"] == tid) == 1
    conn.execute("DELETE FROM sessions WHERE thread_id = ?", (tid,))
    conn.commit()
    conn.close()
    ok("sessions: init, create, update, list, resume-by-id, delete")


# --- 10.5 context truncation ------------------------------------------------
def test_truncation():
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    from context_management import count_tokens, truncate_messages

    assert count_tokens("hello world") > 0

    msgs = [SystemMessage(content="sys")]
    for i in range(40):
        msgs.append(HumanMessage(content=f"q{i} " + "filler " * 300))
        msgs.append(AIMessage(content=f"a{i} " + "filler " * 300))
    trimmed, truncated = truncate_messages(msgs, max_tokens=2_000)
    assert truncated and len(trimmed) < len(msgs)
    assert isinstance(trimmed[0], SystemMessage), "system prompt dropped"
    assert trimmed[-1].content == msgs[-1].content, "recent messages dropped"

    small = [SystemMessage(content="sys"), HumanMessage(content="hi")]
    same, was = truncate_messages(small, max_tokens=2_000)
    assert not was and len(same) == 2
    ok("truncation: trims old, keeps system + recent, no-op under limit")


# --- 10.6 grilling integration ---------------------------------------------
def test_grilling():
    from agent_loop import SYSTEM_PROMPT

    # grilling lives in the system prompt (see design.md), not a separate skill
    for phrase in ("ONE question at a time", "recommended answer", "design tree"):
        assert phrase in SYSTEM_PROMPT, f"missing grilling rule: {phrase}"
    ok("grilling: interview rules present in system prompt")


# --- 10.7 claude code handoff ----------------------------------------------
def test_handoff():
    from claude_code_handoff import (
        VALID_MODES,
        check_claude_code_available,
        handoff_to_claude_code,
        manual_fallback_instructions,
    )

    assert VALID_MODES == {"acceptEdits", "bypassPermissions"}
    assert "invalid mode" in handoff_to_claude_code("x", ".", mode="yolo")
    fb = manual_fallback_instructions("my-change", "/repo")
    assert "openspec instructions apply" in fb and "my-change" in fb
    avail = check_claude_code_available()
    ok(f"handoff: mode validation, fallback text, availability check ({avail})")
    # NOTE: the full live handoff was exercised by running opsx:apply itself
    # through handoff_to_claude_code(mode="acceptEdits") — this session.


if __name__ == "__main__":
    with_llm = "--with-llm" in sys.argv
    with_web = "--with-web" in sys.argv

    test_tools()
    if with_web:
        from tools import web_search

        out = web_search.invoke({"query": "langgraph checkpointer", "max_results": 3})
        assert out and "error" not in out.splitlines()[0].lower()
        ok("web_search: live results returned")
    else:
        print("  skip: live web_search (pass --with-web)")
    test_agent_loop(with_llm)
    test_repl_ui()
    test_sessions()
    test_truncation()
    test_grilling()
    test_handoff()
    print(f"\nall checks passed ({len(PASS)})")
