"""MCP server exposing bounded advisor, researcher, and critiquer subagents backed by local Ollama models."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ddgs import DDGS
from mcp.server.fastmcp import FastMCP
from ollama import generate as ollama_client_generate

Generate = Callable[[str], str]
Search = Callable[[str], list[dict[str, str]]]


@dataclass
class Session:
    """In-memory record of a tracked coding session."""

    session_id: str
    goals: str
    started_at: float


class SessionStore:
    """In-memory dictionary of active sessions, keyed by session_id."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def start(self, session_id: str, goals: str, started_at: float) -> Session:
        """Create and store a new session, replacing any existing session with the same id.

        :param session_id: Unique identifier for the session.
        :param goals: Free-text description of what the session is trying to accomplish.
        :param started_at: Unix timestamp marking session start.
        :return: The newly created Session.
        """
        session = Session(session_id, goals, started_at)
        self._sessions[session_id] = session
        return session

    def pop(self, session_id: str) -> Session | None:
        """Remove and return a session by id.

        :param session_id: Identifier of the session to remove.
        :return: The removed Session, or None if no session existed for that id.
        """
        return self._sessions.pop(session_id, None)


def ollama_generate(prompt: str, model: str | None = None) -> str:
    """Run a single bounded generation call against a local Ollama model.

    :param prompt: The full prompt to send to the model.
    :param model: Ollama model name; defaults to the SUBAGENT_MCP_MODEL env var, then "mistral".
    :return: The model's response text.
    """
    response = ollama_client_generate(
        model=model or os.environ.get("SUBAGENT_MCP_MODEL", "mistral"),
        prompt=prompt,
        stream=False,
    )
    if isinstance(response, dict):
        return str(response.get("response", ""))
    return str(response.response)


def ddgs_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Run a DuckDuckGo text search with no API key required.

    :param query: Search query string.
    :param max_results: Maximum number of results to return.
    :return: List of result dicts with title/href/body keys.
    """
    return [dict(result) for result in DDGS().text(query, max_results=max_results)]


def advise_task(task: str, generate: Generate = ollama_generate) -> str:
    """Get upfront planning guidance for a task from the bounded advisor subagent.

    :param task: Description of the task the conducting agent is about to perform.
    :param generate: Bounded single-turn model call; defaults to ollama_generate.
    :return: Advisor guidance labeled Approach/Pitfalls/Efficiency.
    """
    prompt = f"""You are a bounded planning advisor. You have one turn.

Task:
{task}

Return concise guidance for the conducting coding agent with exactly these labels:
Approach: the smallest viable implementation plan.
Pitfalls: the important failure modes to avoid.
Efficiency: instructions that reduce the conductor's output tokens and unnecessary turns.
Do not write code. Keep the response under 250 words."""
    return generate(prompt)


def research_query(
    query: str,
    search: Search = ddgs_search,
    generate: Generate = ollama_generate,
) -> str:
    """Search the web and synthesize findings via the bounded researcher subagent.

    :param query: Research query to search and synthesize.
    :param search: Web search function; defaults to ddgs_search.
    :param generate: Bounded single-turn model call; defaults to ollama_generate.
    :return: Synthesized findings followed by a sources list.
    """
    results = search(query)
    source_lines = [
        f"- {item.get('title', 'Untitled')}: {item.get('href', item.get('url', ''))}"
        for item in results
    ]
    evidence = "\n".join(
        f"Title: {item.get('title', 'Untitled')}\nURL: {item.get('href', item.get('url', ''))}\nSummary: {item.get('body', item.get('snippet', ''))}"
        for item in results
    )
    prompt = f"""You are a bounded research synthesizer. You have one turn.

Query: {query}

Search results:
{evidence or 'No search results were returned.'}

Synthesize practical findings in under 300 words. Distinguish facts from recommendations and do not invent sources."""
    synthesis = generate(prompt)
    sources = "\n".join(source_lines) or "- No sources returned"
    return f"{synthesis.strip()}\n\nSources:\n{sources}"


def start_session(
    session_id: str,
    goals: str,
    *,
    store: SessionStore,
    now: Callable[[], float] = time.time,
) -> str:
    """Open critique tracking for a coding session.

    :param session_id: Unique identifier for the session.
    :param goals: Free-text description of what the session is trying to accomplish.
    :param store: SessionStore to record the session in.
    :param now: Clock function; defaults to time.time.
    :return: Confirmation message naming the session and its goals.
    """
    if not session_id.strip():
        raise ValueError("session_id is required")
    if not goals.strip():
        raise ValueError("goals is required")
    session = store.start(session_id.strip(), goals.strip(), now())
    return f"Session {session.session_id} started for: {session.goals}"


def estimate_tokens(text: str) -> int:
    """Estimate token count from word count since Ollama does not report exact counts.

    :param text: Text to estimate.
    :return: Estimated token count, at least 1.
    """
    return max(1, len(text.split()) * 4 // 3)


def _extract_section(text: str, label: str) -> str:
    """Pull a single labeled section (e.g. "Continue:") out of the critiquer's response.

    :param text: Raw critiquer response text.
    :param label: Section label to extract ("Continue" or "Avoid").
    :return: The section's text with whitespace collapsed, or a fallback message.
    """
    match = re.search(
        rf"(?im)^\s*{label}\s*:\s*(.+?)(?=^\s*(?:Continue|Avoid)\s*:|\Z)",
        text,
        re.DOTALL,
    )
    return " ".join(match.group(1).split()) if match else "No guidance generated."


def _ensure_guidance_reference(path: Path) -> None:
    """Append a pointer to the critiques directory to a project guidance file, once.

    :param path: Path to the guidance file (e.g. AGENTS.md or CLAUDE.md).
    """
    reference = "The conducting agent should look at session notes in `critiques/` before future work."
    existing = path.read_text() if path.exists() else ""
    if reference not in existing:
        prefix = "\n" if existing and not existing.endswith("\n") else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"{existing}{prefix}\n## Session critique notes\n\n{reference}\n"
        )


async def end_session(
    session_id: str,
    history: str,
    *,
    store: SessionStore,
    notes_dir: Path,
    generate: Generate = ollama_generate,
    guidance_files: list[Path] | None = None,
    now: Callable[[], float] = time.time,
) -> str:
    """Close a session and have the bounded critiquer analyze its token efficiency.

    :param session_id: Identifier of the session to end.
    :param history: Conversation/action history to analyze.
    :param store: SessionStore holding the session.
    :param notes_dir: Directory to write the critique note markdown file into.
    :param generate: Bounded single-turn model call; defaults to ollama_generate.
    :param guidance_files: Project files (e.g. AGENTS.md, CLAUDE.md) to append a critiques/ pointer to.
    :param now: Clock function; defaults to time.time.
    :return: Confirmation message with the path the critique note was written to.
    """
    session = store.pop(session_id)
    if session is None:
        raise ValueError(f"Unknown session: {session_id}")

    elapsed_seconds = max(0.0, now() - session.started_at)
    actual_tokens = estimate_tokens(history)
    ideal_tokens = max(80, len(session.goals.split()) * 12)
    prompt = f"""You are a bounded coding-session critiquer. You have one turn.

Goals: {session.goals}
Elapsed seconds: {elapsed_seconds:.0f}
Estimated output tokens: {actual_tokens}
Ideal baseline tokens: {ideal_tokens}
Conversation history:
{history}

Return exactly two labeled lines:
Continue: one behavior that improved token efficiency or quality.
Avoid: one behavior that wasted tokens or turns.
Keep each recommendation actionable and under 40 words."""
    critique = generate(prompt)
    continue_note = _extract_section(critique, "Continue")
    avoid_note = _extract_section(critique, "Avoid")
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{session.session_id}.md"
    note_path.write_text(
        f"# Session critique: {session.session_id}\n\n"
        f"## Continue\n\n{continue_note}\n\n"
        f"## Avoid\n\n{avoid_note}\n"
    )
    for guidance_file in guidance_files or []:
        _ensure_guidance_reference(guidance_file)
    return f"Session {session.session_id} ended. Critique written to {note_path}"


def create_server(
    *,
    store: SessionStore | None = None,
    notes_dir: Path | None = None,
    generate: Generate = ollama_generate,
    search: Search = ddgs_search,
    guidance_files: list[Path] | None = None,
) -> FastMCP:
    """Build the FastMCP server and register the research/advise/start_session/end_session tools.

    :param store: SessionStore to use; a fresh one is created if omitted.
    :param notes_dir: Directory for critique notes; defaults to this day's critiques/ folder.
    :param generate: Bounded single-turn model call shared by all tools; defaults to ollama_generate.
    :param search: Web search function used by the research tool; defaults to ddgs_search.
    :param guidance_files: Project files to append a critiques/ pointer to; defaults to the monorepo's AGENTS.md and CLAUDE.md.
    :return: A configured FastMCP server instance, not yet run.
    """
    session_store = store or SessionStore()
    day_root = Path(__file__).resolve().parents[1]
    monorepo_root = day_root.parent
    critique_dir = notes_dir or day_root / "critiques"
    guidance = guidance_files or [monorepo_root / "AGENTS.md", monorepo_root / "CLAUDE.md"]
    server = FastMCP("subagent-mcp")

    @server.tool(name="research")
    def research(query: str) -> str:
        """Search the web with DDGS and synthesize findings with sources."""
        return research_query(query, search=search, generate=generate)

    @server.tool(name="advise")
    def advise(task: str) -> str:
        """Get upfront planning guidance (approach, pitfalls, efficiency) for a task."""
        return advise_task(task, generate=generate)

    @server.tool(name="start_session")
    def start(session_id: str, goals: str) -> str:
        """Open critique tracking for a coding session."""
        return start_session(session_id, goals, store=session_store)

    @server.tool(name="end_session")
    async def end(session_id: str, history: str) -> str:
        """Close a session and write a Continue/Avoid token-efficiency critique note."""
        return await end_session(
            session_id,
            history,
            store=session_store,
            notes_dir=critique_dir,
            generate=generate,
            guidance_files=guidance,
        )

    return server


mcp = create_server()


if __name__ == "__main__":
    mcp.run(transport="stdio")
