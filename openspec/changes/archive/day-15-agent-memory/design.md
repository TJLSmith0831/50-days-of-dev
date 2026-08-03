## Context

Mem0/Letta/Cognee-style agent memory is one of the most-discussed agentic frameworks in the last 30 days (see `decisions.md` D2 for the trending-topic scan), and the actual value proposition — persistence *across* sessions, not just a long context window — is easy to state but easy to demo badly (a trivial "single long chat" comparison wouldn't prove anything a plain context window doesn't already do). This design exists to pin down a comparison that's actually fair: a stateless per-session baseline against a Mem0-backed agent, both running fully local against Ollama, isolated per test case so results are unambiguous.

## Goals / Non-Goals

**Goals:**
- Prove Mem0 recovers a fact across sessions that a stateless baseline genuinely cannot recover (not "recovers a fact that was still in context").
- Run fully local: Ollama (`mistral`) for both the demo agent and Mem0's internal fact-extraction LLM, `nomic-embed-text` for embeddings, Chroma as the local vector store. No API key, no cloud Mem0.
- Cover 3 independent fact/question pairs so the result isn't a single anecdotal run.
- Print a clear pass/fail table, no manual interpretation needed to see the result.

**Non-Goals:**
- Multi-user memory sharing, memory expiry/decay, or memory editing/deletion — out of scope, this is a recall-only demo.
- Disambiguating multiple unrelated facts under one shared identity — each pair gets its own isolated `user_id` (D10); testing Mem0's discrimination across a single user's growing memory store is a different, follow-on experiment.
- Replacing or redesigning Day 38 — Day 38 becomes TBD in the README tracker, re-planned separately later (D3).
- An LLM-judged grading rubric — deterministic keyword matching is sufficient and avoids an extra dependency (D12).
- A REPL or interactive mode — this is a single scripted run (`uv run main.py`) that executes all 3 pairs × 2 lanes and prints the report, matching this repo's day-13/day-14 CLI-report pattern.

## Decisions

### Session model: one Ollama chat call per "turn", no history threaded through
Each turn (seed, each filler, the final question) is its own independent call to Ollama's chat endpoint with a single-message list — no prior turns included. This is what "fresh session" means concretely: nothing about session N is visible when session N+1 runs, for either lane.

**Alternatives considered:**
- Threading the growing message list through every call within a pair (a real single conversation) — rejected per D7: this lets the no-memory baseline pass by reading plain context, which isn't the comparison this project needs to make.

### Memory backend: local Mem0 (`mem0.Memory`, not `MemoryClient`)
Configure `mem0.Memory` with an explicit config dict: `llm` → Ollama provider (`mistral`), `embedder` → Ollama provider (`nomic-embed-text`), `vector_store` → Chroma with a local on-disk path (e.g. `./chroma_db`, gitignored). `MemoryClient` (Mem0's hosted/cloud client) is never imported.

**Alternatives considered:**
- `mem0.MemoryClient` (Mem0 Cloud, API-key based) — rejected per D6: breaks the local-first default this repo uses unless a day's concept specifically requires hosted.
- Hand-rolled fastembed + vector store (day-14's pattern) — rejected per D5: the point of this day is hands-on use of the actual named trending framework, not re-proving the underlying concept.

### Isolation: one Mem0 `user_id` per fact/question pair
`pair-1`, `pair-2`, `pair-3` — each pair's seed + filler turns are added under its own `user_id`, and its recall question searches only that `user_id`'s memory space.

**Alternatives considered:**
- One shared `user_id` across all 3 pairs — rejected per D10: turns a clean persistence test into an unrelated semantic-discrimination test, and a wrong retrieval there would read as a Mem0 failure when it's actually an isolation gap in the test design.

### Memory-backed lane writes every turn, not just the seed
Before the recall question, the memory-backed lane has called `memory.add()` 4 times (seed + 3 fillers) under that pair's `user_id`. The no-memory lane never touches Mem0.

**Alternatives considered:**
- Only add the seeded fact to memory (skip storing filler turns) — rejected per D11: retrieving the one and only stored memory proves far less than retrieving the right one out of several.

### Retrieval: `memory.search()` before the final question, injected as context
Immediately before the recall-question call, run `memory.search(query=question, user_id=pair_id, limit=3)` and prepend the returned memories to the system prompt as a short "Relevant memories:" block. The no-memory lane's final call has no such block — just the bare question, fresh session.

### Grading: deterministic keyword substring match
Each pair defines `(seed_fact, filler_turns, question, expected_keyword)`. A lane's answer to the question is graded Pass if `expected_keyword.lower()` appears in the answer text, Fail otherwise (D12).

### Output: a pass/fail table across all 3 pairs × 2 lanes
Printed at the end of the run — pair name, no-memory result (Pass/Fail + truncated answer), memory-backed result (Pass/Fail + truncated answer), plus a totals row. No separate offline self-check script: per this repo's own convention (no CI, no test suite by design — the entrypoint run is the check) and Ollama being free/local (unlike day-13's billed OpenAI calls), `uv run main.py` end-to-end is the verification.

## Risks / Trade-offs

- **[Risk]** `mistral`'s fact-extraction quality (Mem0's internal LLM step that turns a raw turn into a stored memory) may not reliably extract the seeded fact, especially phrased casually → **Mitigation**: keep seed-fact phrasing direct and declarative ("My favorite programming language is Rust," not something oblique); if extraction misses under `mistral`, that's itself a reportable finding, not a bug to hide.
- **[Risk]** Local Ollama inference latency (3 pairs × 2 lanes × ~5 calls each = ~30 LLM calls, plus Mem0's own internal extraction/embedding calls) could make a full run slow → **Mitigation**: `mistral` (4.4GB) chosen specifically over the heavier `qwen3:14b` default for this reason (D9); acceptable if a full run takes a couple of minutes, matching day-13's ~2min precedent.
- **[Risk]** Chroma's local persistence directory could accumulate stale memories across repeated runs, causing a later run to "pass" on stale data even if retrieval is actually broken → **Mitigation**: `main.py` uses a fresh Chroma path (or clears it) at the start of each run, same pattern as day-13's `rm -rf data/` convention.
- **[Risk]** `mem0ai`'s Ollama-local configuration surface is less battle-tested than its default OpenAI path → **Mitigation**: confirmed via research that v2.0.7 (June 2026) supports a full local `{llm, embedder, vector_store}` config (D6); if setup friction appears, it becomes a documented Gotcha in `AGENTS.md`, same as day-13's semantic-router/Python-3.13 gotcha.
