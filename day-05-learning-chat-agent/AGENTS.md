# Day 05 — Learning Chat Agent — AGENTS.md
A conversational agent that adapts to user writing style across sessions using LangGraph memory and human-in-the-loop feedback.

## Stack
Python · LangGraph · LangChain · Ollama (qwen3:14b or llama3.2)

## Commands (verified 2026-07-16)
- `uv sync` — install dependencies
- `uv run main.py --model qwen3:14b` — start interactive chat session with memory
- `uv run main.py --model qwen3:14b --fresh` — start fresh session (clears memory)
- `uv run main.py --self-check` — verify Ollama connection and dependencies

## Concept
Self-improving agents = memory + feedback loop. This agent demonstrates the core pattern: learn preferences through human feedback, persist them across sessions via LangGraph checkpointer, and apply them automatically without re-teaching.

## Gotchas
- **Memory is persistent.** SqliteSaver stores checkpoints in a local SQLite database file (`checkpoints.db`), enabling persistence across process restarts. Memory is scoped to thread_id - use consistent thread_id to maintain memory, or different thread_ids for isolation.
- **Thread isolation.** Each `thread_id` represents a separate conversation/memory space. Use different thread_ids for different users or contexts to keep their preferences separate. For example, `--thread-id user-1` vs `--thread-id user-2` creates isolated memory spaces.
- **Learning vs responding is manual.** Unlike CrewAI's cognitive memory, this system must explicitly decide when to store preferences vs when to respond. The prompt must guide this distinction.
- **Ollama model must be running.** `ollama serve` must be active before starting the agent. The preflight checks this and exits with clear error message if not.
- **Temperature affects learning.** Higher temperature (0.7-0.8) for exploration when learning new preferences; lower (0.2-0.3) for applying learned patterns.
- **Sandbox is ephemeral.** Files written to the temp sandbox are not persisted between sessions. Use this for drafts, not for long-term storage.
- **Memory is not automatic.** The agent must be explicitly prompted to store feedback as preferences. Unlike Claude's auto-memory, this is manual for educational clarity.
- **Docstring format.** This project uses Google-style docstrings with `:param` and `:return` tags, not the more verbose Google docstring format with Args/Returns sections.
- **Tool calling with llama3.2.** The default llama3.2 model is known to be overly tool-happy, calling tools even for simple conversational queries. For better tool behavior, consider using `qwen3:14b` (91% tool success rate) or the custom model `ejschwar/llama3.2-better-prompts:llama3.1-tooling-prompt-customized` which has improved prompts for tool calling.
