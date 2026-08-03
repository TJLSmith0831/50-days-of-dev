# Day 15 replan

## D1: Drop "context engineering" as Day 15's topic?
- **Decision**: Yes. Day 15 will not be "Context Rebuild" (raw prompt vs structured context).
- **Why**: User feels it's duplicative of prior days' work (day-05 learning-chat-agent, day-11 audited-agent, day-13 smart-tool-selector, day-14 toolsieve all already exercise context/prompt shaping).
- **Source**: user

## D2: New Day 15 topic
- **Decision**: Agent memory (long-term recall across turns/sessions), inspired by the Mem0/Letta/Cognee wave trending hard in July 2026.
- **Why**: Checked against all 14 built days' actual mechanics (not just labels). The other 3 web-search candidates all repeat something already shipped: reflection/evaluator-optimizer duplicates the critic subagent in day-10 (subagent-mcp) and day-12 (ACP); agent security/guardrails duplicates day-03 (Repo Doctor guardrails) + day-11 (audit trail) + planned day-40; A2A protocol duplicates day-12's agent-to-agent handoff over a protocol. Agent memory is the only one where none of days 1-14 do vector-based recall across turns (day-05's "lessons" are text heuristics injected into prompts, not a memory store).
- **Source**: recommended-accepted

## D3: Day 38 conflict ("Remembering Agent" already reserved for memory)
- **Decision**: Take the memory topic now for Day 15. Day 38 becomes TBD/placeholder, to be re-planned later — not solved today.
- **Why**: 3+ weeks of runway before Day 38 matters; no need to design its replacement now.
- **Source**: recommended-accepted

## D4: Concrete measurable outcome
- **Decision**: Recall test — seed a fact early in a session, run several unrelated turns, then ask a question that requires the seeded fact. Compare a no-memory agent (fails/hallucinates) vs a memory-backed agent (retrieves correctly).
- **Why**: Clean pass/fail metric, directly matches the roadmap's original framing for this idea ("recall a fact from 3 turns ago"), simplest correctness story for a 1-2hr scope.
- **Source**: recommended-accepted

## D5: Memory implementation — real framework vs hand-rolled
- **Decision**: Use Mem0 (mem0ai package), not a hand-rolled fastembed+vector-store setup.
- **Why**: The point of chasing a trending topic is hands-on exposure to the actual named tool people are discussing, not just proving the underlying concept (which day-14's fastembed pattern already demonstrates).
- **Source**: recommended-accepted

## D6: Mem0 hosting — local vs hosted
- **Decision**: Fully local Mem0: Ollama for both LLM (fact extraction) and embedder, Chroma as the local vector store. No API key, no Mem0 cloud (`is_cloud=False` alone is not enough — must also swap the default OpenAI-backed LLM/embedder to Ollama).
- **Why**: Matches repo default (local models via Ollama; hosted API only when the day's concept specifically requires it) — verified Mem0 v2.0.7 supports a full local config via {llm, embedder, vector_store} dict.
- **Source**: recommended-accepted (per CLAUDE.md gotcha: local-first default)

## D7: "No-memory" baseline definition
- **Decision**: Fresh session per turn, zero prior context (each turn is an independent LLM call — simulates separate CLI invocations). Memory-backed side: also fresh session per turn, but Mem0 stores/retrieves across those sessions.
- **Why**: Tests the real thing Mem0 targets (persistence across sessions), not just long-context recall. A single continuous chat with a few turns between seed and question would let the no-memory baseline pass trivially via plain context, making the comparison unconvincing.
- **Source**: recommended-accepted

## D8: Test scenario shape
- **Decision**: 3 fact/question pairs, each with 3 unrelated turns in between (e.g. seed "my favorite language is Rust" → weather/joke/math turns → ask "what's my favorite language?").
- **Why**: n=1 reads as a lucky/unlucky single run (mirrors day-13's lesson about not resting a finding on one sample); 3 pairs is proportionate to a 1-2hr scope.
- **Source**: recommended-accepted

## D9: Local model choice
- **Decision**: Ollama `mistral:latest` as the chat/extraction LLM (mem0's internal fact-extraction LLM and the demo's own agent), `nomic-embed-text` as the embedder.
- **Why**: `mistral` (4.4GB) is lighter on CPU than day-06's default `qwen3:14b` (9.3GB) — user chose to avoid the heavier model's load for this day's demo. Both already pulled locally (`ollama list` confirmed).
- **Source**: user (overrides day-06's default; codebase confirms `mistral:latest` and `nomic-embed-text` already pulled)

## D10: Cross-pair memory isolation
- **Decision**: Each of the 3 fact/question pairs gets its own Mem0 `user_id` (e.g. `pair-1`, `pair-2`, `pair-3`).
- **Why**: Guarantees clean isolation so pair 2's retrieval can't accidentally surface pair 1's fact. The test is about cross-session persistence, not about Mem0's ability to disambiguate multiple unrelated facts for one user — that's a different (also interesting, but out of scope) test.
- **Source**: recommended-accepted

## D11: Do filler turns get added to memory?
- **Decision**: Yes — in the memory-backed lane, the seed turn AND all 3 filler turns are added to Mem0 (`memory.add`) before the recall question. The no-memory lane never calls Mem0 at all (plain fresh-session LLM calls only).
- **Why**: Makes the memory-backed lane retrieve the right fact out of 4 stored memories, not the only one — a stronger, more realistic demonstration of retrieval than storing just the single seeded fact.
- **Source**: recommended-accepted

## D12: Grading rule
- **Decision**: Deterministic keyword match — each fact/question pair has a fixed expected keyword (e.g. "Rust" for "my favorite language is Rust"); pass = case-insensitive substring match in the final answer, fail otherwise.
- **Why**: The fact and keyword are authored by the test itself, so a substring check is exact and free — no need for an LLM-judge dependency for something this unambiguous.
- **Source**: recommended-accepted

