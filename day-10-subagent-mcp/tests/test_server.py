"""Tests for the subagent MCP server's advisor, researcher, and critiquer tools."""

from pathlib import Path

import pytest

from src.server import (
    SessionStore,
    advise_task,
    end_session,
    research_query,
    start_session,
)


@pytest.mark.asyncio
async def test_mcp_registers_four_tools_and_advisor_call() -> None:
    from src.server import create_server

    server = create_server(
        generate=lambda prompt: "Approach: plan first.\nPitfalls: avoid scope creep.\nEfficiency: be concise."
    )

    tools = await server.list_tools()
    result = await server.call_tool("advise", {"task": "Build a greeting CLI"})

    assert {tool.name for tool in tools} == {
        "research",
        "advise",
        "start_session",
        "end_session",
    }
    assert "Efficiency:" in result[0][0].text


def test_advisor_returns_guidance_from_bounded_model_call() -> None:
    prompts: list[str] = []

    def generate(prompt: str) -> str:
        prompts.append(prompt)
        return "Approach: use a small command parser.\nPitfall: validate empty input.\nEfficiency: keep the response concise."

    result = advise_task("Build a CLI that greets the user", generate=generate)

    assert "Approach:" in result
    assert "Efficiency:" in result
    assert "Build a CLI that greets the user" in prompts[0]


def test_researcher_synthesizes_search_results_with_sources() -> None:
    def search(query: str) -> list[dict[str, str]]:
        assert query == "Python argparse greeting CLI"
        return [
            {"title": "argparse docs", "href": "https://docs.python.org/3/library/argparse.html", "body": "CLI parsing"}
        ]

    def generate(prompt: str) -> str:
        assert "argparse docs" in prompt
        return "Use argparse for a small, standard-library CLI."

    result = research_query(
        "Python argparse greeting CLI",
        search=search,
        generate=generate,
    )

    assert "Use argparse" in result
    assert "https://docs.python.org/3/library/argparse.html" in result


@pytest.mark.asyncio
async def test_session_end_writes_only_continue_and_avoid_notes(tmp_path: Path) -> None:
    store = SessionStore()
    start_session("demo-session", "Build a greeting CLI", store=store, now=lambda: 100.0)

    result = await end_session(
        "demo-session",
        "Turn 1: read the same file twice.\nTurn 2: implemented the parser.",
        store=store,
        notes_dir=tmp_path / "critiques",
        generate=lambda prompt: "Continue: keep upfront plans concise.\nAvoid: rereading unchanged files.",
        guidance_files=[tmp_path / "AGENTS.md", tmp_path / "CLAUDE.md"],
        now=lambda: 112.0,
    )

    note = (tmp_path / "critiques" / "demo-session.md").read_text()
    assert "# Session critique: demo-session" in note
    assert "## Continue" in note
    assert "## Avoid" in note
    assert note.count("## ") == 2
    assert "critiques/" in (tmp_path / "AGENTS.md").read_text()
    assert "session notes" in (tmp_path / "CLAUDE.md").read_text().lower()
    assert "demo-session" in result
