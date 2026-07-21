# Day 10 — Subagent MCP — AGENTS.md
Exposes bounded research, planning, and coding-session critique subagents through a local Ollama-backed MCP server.

## Stack
Python · MCP Python SDK · DDGS · Ollama (`mistral`)

## Commands
- `PYTHONPATH=. uv run --no-project --with pytest --with pytest-asyncio --with mcp --with ollama --with ddgs pytest tests/test_server.py -q`
- `PYTHONPATH=src uv run --no-project --with mcp --with ollama --with ddgs python src/index.py` (server, stdio transport)
- `PYTHONPATH=src uv run --no-project --with mcp --with ollama --with ddgs python src/demo.py` (full workflow demo)

## Concept
Claude Code remains the conductor while bounded local subagents handle research, upfront planning, and session critique. Session critiques are written to `critiques/<session_id>.md` with `Continue` and `Avoid` sections.

## Gotchas
- Ollama must be running locally with the configured model available; set `SUBAGENT_MCP_MODEL` to override `mistral` in a future adapter.
- The server communicates over stdio. Keep logs off stdout so MCP messages remain valid.
- Session state is in-memory and disappears when the server restarts.
