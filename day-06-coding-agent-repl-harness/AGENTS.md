# Day 06 — Coding Agent REPL Harness — AGENTS.md
Spec Driven Design (SDD) writer harness. The model grills the user for requirements before drafting a spec, then hands off to Claude Code headless for implementation.

## Stack
Python · LangGraph · Rich · Ollama (qwen3:14b) · DuckDuckGo Search (ddgs)

## Commands (verified 2026-07-17)
- `uv sync` — install dependencies
- `uv run main.py --model qwen3:14b` — start REPL session with default model
- `uv run main.py --model qwen3:14b --thread-id my-session` — start REPL with specific session
- `uv run main.py --model qwen3:14b --fresh` — start fresh session (clears memory)
- `uv run main.py --self-check` — verify Ollama connection and dependencies

## Concept
SDD workflow = research (local model) + spec planning (grilling built into system prompt) + implementation (Claude Code). Qwen3:14b via Ollama drives cost-effective research and grilling: it interviews the user one question at a time, recommending an answer for each, and only drafts a spec once the design tree is resolved. Handoff to Claude Code via opsx:apply.

## Gotchas
- **Ollama must be running.** `ollama serve` must be active before starting the harness. The preflight checks this and exits with clear error message if not.
- **Model must be pulled.** Run `ollama pull qwen3:14b` before first use. Fallback to llama3.2 if qwen3:14b unavailable.
- **Session persistence is automatic.** SQLite database at `~/.coding-agent-harness/sessions.db` stores sessions. Use /sessions to list, /save to persist manually.
- **Context truncation runs inside the agent node.** When history exceeds ~24000 tokens (tiktoken cl100k_base — leaves headroom in qwen3:14b's 32k window for the response), oldest messages are dropped via `langchain_core.messages.trim_messages`. SystemMessage always kept; trim starts on a `HumanMessage` so tool-call/response pairs stay intact.
- **Grilling is the default flow.** The system prompt makes the model interview the user before drafting any spec — one question at a time, with a recommended answer, exploring the codebase before asking when possible. No separate skill install needed.
- **Claude Code handoff is optional.** /handoff requires Claude Code installation and ANTHROPIC_API_KEY. Preflight warns at startup if missing; handoff falls back to manual opsx:apply instructions.
- **Handoff permission modes.** `/handoff` defaults to `acceptEdits` (file writes flow; Bash still prompts and headless denies it). `/handoff yolo` opts into `bypassPermissions` for that single call — full autonomy, largest blast radius, prompts for confirmation first.
- **Tool set is read-only.** v1 includes only Read, Glob, Grep, Web Search, and openspec CLI. Write/Edit/Bash are excluded per SDD workflow (Claude Code handles implementation).
- **@file mentions expand to absolute paths.** Use @filename to reference files in the current directory. The harness resolves to absolute paths before tool calls.
- **Slash commands are /help, /save, /sessions, /exit, /handoff.** Type /help in the REPL for command reference.
