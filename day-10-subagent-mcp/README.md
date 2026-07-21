# Day 10 — Subagent MCP

A Python MCP server that lets Claude Code delegate bounded work to local Ollama subagents:

- `research(query)` searches with DDGS and synthesizes findings with sources.
- `advise(task)` gives concise upfront implementation guidance.
- `start_session(session_id, goals)` opens in-memory critique tracking.
- `end_session(session_id, history)` writes `critiques/<session_id>.md` with `Continue` and `Avoid` sections.

## Claude Code

From this directory, add the server with:

```bash
claude mcp add --transport stdio subagent-mcp -- uv run --no-project --with mcp --with ollama --with ddgs python "$(pwd)/src/index.py"
```

Use an absolute path for `index.py` — a relative `src/index.py` only resolves if Claude Code's working directory happens to be this folder when it launches the server. The server expects Ollama to be running locally with the `mistral` model available. New MCP servers only load their tool schemas at session start, so start a fresh Claude Code session after adding it.

## Demo

Runs the full workflow — advise, research, start a session, then end it and print the critique note:

```bash
PYTHONPATH=src uv run --no-project --with mcp --with ollama --with ddgs python src/demo.py
```

## Tests

```bash
PYTHONPATH=. uv run --no-project --with pytest --with pytest-asyncio --with mcp --with ollama --with ddgs pytest tests/test_server.py -q
```
