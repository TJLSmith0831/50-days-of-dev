# Day 05 — Learning Chat Agent

A conversational agent that adapts to user writing style across sessions using LangGraph memory and human-in-the-loop feedback.

## Concept

Self-improving agents = memory + feedback loop. This agent demonstrates the core pattern: learn preferences through human feedback, persist them across sessions via LangGraph checkpointer, and apply them automatically without re-teaching.

## Stack

Python · LangGraph · LangChain · Ollama (qwen3:14b recommended)

## Usage

```bash
# Install dependencies
uv sync

# Start interactive chat session with memory
uv run main.py --model qwen3:14b

# Start fresh session (clears memory)
uv run main.py --model qwen3:14b --fresh

# Verify Ollama connection
uv run main.py --self-check
```

## Demo Arc

**Session 1:** Teach the agent your preferences
- You: "Write a cover letter for a software engineering job"
- Agent: [writes formal cover letter]
- You: "That's too formal. I prefer casual language and shorter paragraphs"
- Agent: ✓ Preference learned: I prefer casual language and shorter paragraphs

**Session 2:** Agent applies learned preferences automatically
- You: "Write a cover letter for a software engineering job"
- Agent: [writes casual, concise cover letter without being told]

**Session 3:** Preferences persist across days
- You: "Write a cover letter for a software engineering job"
- Agent: [still writes in your preferred style]

## Features

- **Memory persistence** across sessions via LangGraph checkpointer
- **Human-in-the-loop feedback** for learning preferences
- **Tool usage** for file writing to temporary sandbox
- **Learning vs responding** distinction (manual for educational clarity)
- **Local-only operation** via Ollama (no API costs)

## Commands

- `--model`: Ollama model to use (default: `qwen3:14b`)
- `--thread-id`: Thread ID for memory persistence (default: default-user)
- `--fresh`: Start with fresh memory (clears previous learning)
- `--self-check`: Run preflight checks only

## Prerequisites

- Ollama running: `ollama serve`
- Model pulled: `ollama pull qwen3:14b` (or your preferred model)
- Python 3.10+

## Architecture

The agent uses LangGraph's StateGraph with:
- **Agent node**: Calls LLM with learned preferences in system prompt
- **Tools node**: Handles file writing operations
- **Preference extraction node**: Detects feedback and stores as preferences
- **SqliteSaver checkpointer**: Persists state to `checkpoints.db` across sessions

## Key Differences from Day 04

- Framework-based (LangGraph) vs bare-metal
- Focus on agentic patterns vs metrics
- Chat interface vs coding tasks
- Human feedback vs automated grading
- Session persistence vs single-run optimization
