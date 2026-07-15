# Day 04 — First-Principles Crew — AGENTS.md
Breaks a messy problem into N fundamental truths after challenging M assumptions, then reasons up to one recommendation — in T seconds, fully local.

## Stack
Python · CrewAI (crewai, Process.sequential) · LiteLLM → Ollama (ollama/llama3.2) · Pydantic (structured task outputs) · rich (CLI + final report) · python-dotenv

## Commands (verified 2026-07-15)
- `uv sync`
- `uv run main.py "<problem statement>"` — problem as CLI arg; zero-arg demo runs with a baked-in example

## Concept
CrewAI's declarative, role-based orchestration: specialized agents whose outputs chain forward via context=, run as a sequential Crew. Contrast with Day 2 (explicit LangGraph state graph) and Day 3 (SDK subagent spawn) — same "multiple cooperating agents" goal, a third distinct abstraction. The first-principles method is the payload that makes the role separation meaningful.

## Gotchas
- LiteLLM wiring: CrewAI reaches Ollama through LiteLLM — use LLM(model="ollama/llama3.2", base_url="http://localhost:11434"), not the langchain-ollama object Days 1–2 use.
- Structured output on small local models is flaky: llama3.2 may not reliably fill a schema. Mitigate with tiny/flat models, low temperature, terse prompts, and graceful fallback if parsing fails.
- 3 agents drift on small models — keep goals/backstories tight.
- Telemetry: set CREWAI_TELEMETRY_OPT_OUT=true to honor the repo's local-first/offline ethos.
- [tool.uv] package = false in pyproject.toml (root gotcha). First uv sync is heavy — crewai drags in litellm + a big tree.
