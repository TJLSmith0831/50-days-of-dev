# Day 14 — toolsieve (Ship Day)

**This folder is a pointer.** All code lives in the separate [toolsieve repository](https://github.com/TJLSmith0831/toolsieve).

## What is toolsieve?

**Semantic tool routing for MCP.** Point it at the MCP servers you already run. It aggregates every tool they publish, then exposes exactly **three** tools to your client — and tells you how many tokens that saved.

### Key Features

- **Semantic matching**: Embeds each tool's own name and description, matches queries by cosine similarity — no keyword overlap required
- **Real aggregation**: Connects to real downstream stdio MCP servers, not a fabricated catalog
- **Token savings receipt**: Every `find_tools` call reports `tokens_if_naive`, `tokens_actual`, and `saved_pct`
- **Three-tool interface**: `find_tools(query, k=3)`, `call_tool(server, tool_name, args)`, `get_savings_report()`
- **Failure isolation**: One server going down doesn't take toolsieve with it
- **Live reload**: Edit the config while running and it re-aggregates automatically
- **Claude Code plugin**: One-command install via `/plugin marketplace add TJLSmith0831/toolsieve`

### Demo Results

Live demo in Claude Code (Sonnet) against 4 real MCP servers:
- **15 tools aggregated, 3 exposed**
- **82.4% of tool-schema tokens saved** across the session
- Routes "search my notes" and "read library docs" to the right tools
- Calls the weather tool for real data

### Why This Matters

Existing MCP gateways (`mcpproxy-go`, `toolfunnel`, `mcp-gateway`, `mcp-orchestrator`) filter **lexically** (BM25 keyword matching) or **structurally** (manual allow-lists). toolsieve matches **semantically** by embedding similarity and reports live savings — a combination the competitive scan found nobody else does.

### Stack

Python · fastmcp (server + proxy machinery) · fastembed (local ONNX encoder, no API key) · MCP SDK

### Ship Day Status

This is Week 2's portfolio-grade build. See the standalone [toolsieve README](https://github.com/TJLSmith0831/toolsieve#readme) for full installation, configuration, and usage instructions.

### Repository

[github.com/TJLSmith0831/toolsieve](https://github.com/TJLSmith0831/toolsieve)
