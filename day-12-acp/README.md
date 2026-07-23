# Day 12 — ACP Agent

A CLI orchestrator that discovers and chains multiple ACP-compliant agents, demonstrating agent-to-agent interoperability through IBM's BeeAI framework and the Agent Communication Protocol.

## Stack
Python · BeeAI Framework (`beeai-framework[acp]`) · ACP SDK (`acp-sdk`) · OpenAI gpt-4.1-mini

## Commands (verified 2026-07-23)
```
uv sync
uv run server.py    # Start ACP server with agents (terminal 1)
uv run cli.py "research and write about quantum computing"  # CLI orchestrator (terminal 2)
uv run pytest -q    # pipeline-logic tests, no server/API key needed
```

## Concept
Build three real LLM-backed ACP agents (researcher, writer, critic) using BeeAI's ACPServer, then build a CLI that discovers them via ACP's REST endpoints, chains their outputs, and displays live agent-to-agent communication. Demonstrates framework-agnostic interoperability - agents built with BeeAI can be discovered and invoked by any ACP client.

## Build path
- **Step 1:** Scaffold BeeAI ACP server with three ReAct agents (researcher with DuckDuckGo, writer, critic)
- **Step 2:** Build CLI orchestrator using ACP SDK for discovery and agent chaining
- **Step 3:** Add streaming support to display live agent thoughts and communication flow

## Gotchas
- ACP is now part of A2A under Linux Foundation — the official `i-am-bee/acp` repo is archived but BeeAI's ACP integration still works
- BeeAI requires `pip install 'beeai-framework[acp]'` for ACP support
- Server runs on http://localhost:8000 by default, configurable via ACPServerConfig
- Requires `OPENAI_API_KEY` in `.env` file for gpt-4.1-mini
- Agents can be tested with curl without SDK: `curl http://localhost:8000/agents`
