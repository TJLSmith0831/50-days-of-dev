# Day 12 — ACP Agent — AGENTS.md
CLI orchestrator for ACP agents: BeeAI ACPServer hosts 3 ReAct agents, CLI discovers/chains them via ACP SDK, displays live communication

## Stack
Python · BeeAI Framework (`beeai-framework[acp]`) · ACP SDK (`acp-sdk`) · OpenAI gpt-4.1-mini

## Commands (verified 2026-07-23)
`uv sync && uv run server.py` (start ACP server) then, in a second terminal, `uv run cli.py "research and write about quantum computing"` (CLI orchestrator). `uv run pytest -q` runs the pipeline-logic tests (no server/API key needed).

## Concept
ACP (Agent Communication Protocol) is IBM's open standard for agent-to-agent communication via RESTful HTTP. This day builds three real LLM-backed agents using BeeAI (researcher with web search, writer, critic), exposes them via BeeAI's ACPServer, then builds a CLI that discovers them via ACP, chains their outputs, and shows live agent-to-agent communication.

## Gotchas
- BeeAI's ACP integration requires `beeai-framework[acp]` extra
- Server defaults to port 8000, configurable via ACPServerConfig
- CLI uses ACP SDK for HTTP client operations, agents use BeeAI for LLM/tools/memory
- Requires `OPENAI_API_KEY` in `.env` for gpt-4.1-mini
