## Why

Day 15 was originally slotted as "context engineering" (raw prompt vs structured context), but that idea is duplicative of prior days' work (day-05, day-11, day-13, day-14 all already exercise context/prompt shaping). Agent memory (Mem0/Letta/Cognee-style long-term recall) is trending hard right now and, after checking against every prior built day's actual mechanics, is the one candidate that doesn't repeat something already shipped — see `decisions.md` D1-D2 for the full trending-topic comparison.

## What Changes

- New day folder `day-15-agent-memory/`: a CLI demo comparing a stateless agent against a Mem0-backed agent on a cross-session fact-recall test.
- Each of 3 fact/question pairs runs as: seed a fact in its own fresh session → 3 unrelated turns, each its own fresh session → a question requiring the seeded fact, in yet another fresh session. "Fresh session" means zero prior conversation history passed to the LLM call, simulating separate CLI invocations — the actual case Mem0 targets (persistence across sessions, not long-context recall within one).
- Two lanes per pair: **no-memory** (fresh session, no retrieval — expected to fail/hallucinate) and **memory-backed** (Mem0 stores the seeded fact and retrieves it before the final question). Prints a pass/fail table across all 3 pairs × 2 lanes.
- Fully local: Mem0 configured with Ollama (`mistral`, chosen over day-06's heavier `qwen3:14b` default to go easy on CPU) as both the demo agent's LLM and Mem0's internal fact-extraction LLM, `nomic-embed-text` as the embedder, and a local Chroma vector store — no API key, no cloud Mem0.
- Day 38 ("Remembering Agent"), previously the only reserved slot for a memory project, becomes TBD in the README tracker — not solved by this change.

## Capabilities

### New Capabilities
- `agent-memory-recall`: a cross-session fact-recall test harness — seeds facts, runs unrelated filler turns, asks a recall question, and grades pass/fail for a stateless baseline vs. a Mem0-backed agent, all against local Ollama models and a local vector store.

### Modified Capabilities
(none — new, self-contained day folder; no existing specs' requirements change)

## Impact

- New folder `day-15-agent-memory/` (own `pyproject.toml` with `[tool.uv] package = false`, `AGENTS.md`, `README.md`, `main.py`) added to the root uv workspace (`day-*` glob already covers it, no root `pyproject.toml` edit needed).
- New dependency: `mem0ai` (plus its `chromadb` local vector-store backend). New local Ollama model requirement: none beyond what's already pulled (`mistral:latest`, `nomic-embed-text` both present per `ollama list`).
- Root `README.md` progress table: Day 15 row updated from "Context engineering / Context Rebuild" to this project; Day 38 row's topic left as-is but flagged TBD in a follow-up note (not touched by this change directly — out of scope here per D3).
- No impact on existing 50-days-of-dev specs (`agent-loop`, `claude-code-handoff`, `context-management`, `grilling-integration`, `repl-interface`, `repo-doctor`, `session-management`, `tool-system`) or any other day folder.
