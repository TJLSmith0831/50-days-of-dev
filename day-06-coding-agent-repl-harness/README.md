# Coding Agent REPL Harness

Spec Driven Design (SDD) writer harness. The model grills the user for requirements before drafting a spec, then hands off to Claude Code headless for implementation.

## Overview

This harness uses smaller local models (Qwen3:14b via Ollama) for research and spec planning, then hands off to Claude Code for implementation via opsx:apply. Grilling is baked into the system prompt — the model interviews the user one question at a time, recommending an answer for each, and only drafts a spec once the design tree is resolved.

## Features

- Rich-based terminal REPL with streaming token display
- Tool system: Read, Glob, Grep, Web Search, openspec CLI
- SQLite-based session persistence with mid-turn checkpointing
- Context truncation applied inside the agent node (token-based, preserves system + last 10)
- Grilling as the default flow (built into the system prompt)
- Claude Code headless integration for opsx:apply handoff
- @file mention expansion and slash commands

## Commands (verified 2026-07-17)

```bash
# Install dependencies
uv sync

# Start REPL session
uv run main.py --model qwen3:14b

# Start with specific session
uv run main.py --model qwen3:14b --thread-id my-session

# Start fresh session
uv run main.py --model qwen3:14b --fresh

# Preflight checks
uv run main.py --self-check

# Smoke checks (tools, agent graph, REPL helpers, sessions, truncation, handoff)
uv run python test_harness.py            # offline checks
uv run python test_harness.py --with-llm --with-web  # + live Ollama + DuckDuckGo
```

## Requirements

- Python 3.10+
- Ollama running (`ollama serve`)
- Qwen3:14b model pulled (`ollama pull qwen3:14b`)
- Claude Code (optional, for handoff)
- ANTHROPIC_API_KEY (optional, for handoff)

## Slash Commands

- `/help` - Show available commands
- `/save` - Persist current session
- `/sessions` - List available sessions
- `/exit` - Exit the REPL
- `/handoff` - Handoff to Claude Code for implementation (acceptEdits mode; `/handoff yolo` for bypassPermissions)

## Session Persistence

Sessions are stored in `~/.coding-agent-harness/sessions.db`. Use `/sessions` to list and `/save` to persist manually.
