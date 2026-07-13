# Day 2 — Gift Scout — AGENTS.md
LangGraph shopping intern: `brainstorm` → HITL `interrupt()` gate → `agent ⇄ ToolNode` loop (`web_search`, `add_to_shortlist`) → `rank`. Durable via `SqliteSaver`.

## Stack
Python · LangGraph (`langgraph`, `langgraph-checkpoint-sqlite`) · `langchain-ollama` (local `llama3.2`) · `ddgs` · `rich`

## Commands (unverified — run after Step 1 lands)
`uv sync && uv run main.py`

## Concept
Flat `TypedDict` state threaded through a `StateGraph`. Three foundational concepts in one graph: stateful graph, durable resume (`SqliteSaver` + `thread_id`), tool-calling (`bind_tools` + `ToolNode` + conditional loop edge — ReAct). Plus HITL via `interrupt()`/`Command(resume=...)` at the approval gate.

## Status
Scaffolding only — all node bodies are stubs (see `TODO(step2)` / `TODO(step3)` markers in `main.py`). Graph shape, state schema, and `SqliteSaver` wiring are real; `brainstorm`/`agent`/`rank` logic and the two tool bodies are not.

## Gotchas
- `interrupt()`/`Command(resume=...)` signature is unverified against the installed `langgraph` version — check before extending `approval_gate`.
- `route_after_agent` currently loops on a fixed call counter, not `tools_condition` — swap once `agent` emits real tool calls in Step 2.
- `web_search`/`add_to_shortlist` both `raise NotImplementedError` — expected until Step 2.
