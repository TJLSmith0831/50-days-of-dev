## 1. Scaffold

- [x] 1.1 Create `day-15-agent-memory/` with `pyproject.toml` (`requires-python = ">=3.13"`, `[tool.uv] package = false`, deps: `mem0ai`, `chromadb`, `ollama`)
- [x] 1.2 Add `.gitignore` entry for the local Chroma persistence path (e.g. `chroma_db/`)

## 2. Local Mem0 spike (riskiest first)

- [x] 2.1 Confirm `mistral:latest` and `nomic-embed-text` are pulled (`ollama list`); pull if missing
- [x] 2.2 Build the local Mem0 config dict (`llm` → Ollama `mistral`, `embedder` → Ollama `nomic-embed-text`, `vector_store` → Chroma at a local path) and instantiate `mem0.Memory` (not `MemoryClient`)
- [x] 2.3 Smoke-test one `memory.add()` + `memory.search()` round trip under a throwaway `user_id`; confirm no network call to Mem0 Cloud and no API key required
- [x] 2.4 If extraction/retrieval doesn't work as expected, capture the fix as an `AGENTS.md` Gotcha before continuing (per design.md risk on Mem0's less-battle-tested local config path)

## 3. Fresh-session call helper

- [x] 3.1 Implement a single-turn Ollama chat call helper that takes only a system prompt + one user message — no threaded history, no dependency on prior calls
- [x] 3.2 Implement the no-memory lane: seed turn, 3 filler turns, recall-question turn, all fresh-session calls, no Mem0 involvement at all

## 4. Memory-backed lane

- [x] 4.1 Define 3 fact/question pairs as data: `(seed_fact, filler_turns[3], question, expected_keyword)`, each with a distinct `user_id` (`pair-1`/`pair-2`/`pair-3`)
- [x] 4.2 Implement the memory-backed lane: seed + 3 filler turns each fresh-session-called AND added to Mem0 under that pair's `user_id`
- [x] 4.3 Before the recall-question call, run `memory.search()` scoped to that pair's `user_id` and prepend retrieved memories to the question's system prompt
- [x] 4.4 Verify pair isolation: pair B's search never returns a memory stored under pair A's `user_id`

## 5. Grading and reporting

- [x] 5.1 Implement the pass/fail grader: case-insensitive substring match of `expected_keyword` in a lane's final answer
- [x] 5.2 Implement the end-of-run report: one row per pair (no-memory Pass/Fail + truncated answer, memory-backed Pass/Fail + truncated answer), plus a totals row summing Pass counts per lane

## 6. Wire up and verify

- [x] 6.1 `main.py`: reset/create the local Chroma path at run start, run all 3 pairs through both lanes, print the report
- [x] 6.2 `uv run main.py` end to end — confirm no-memory lane fails/hallucinates and memory-backed lane passes across the 3 pairs (or document what actually happened if a pair doesn't behave as expected — the point is a real measurement, not a guaranteed outcome)

## 7. Docs

- [x] 7.1 Write `day-15-agent-memory/AGENTS.md` (stack, commands, concept, any gotchas hit during the Mem0 local-config spike)
- [x] 7.2 Update root `README.md`: Day 15 row (topic + outcome + status), and flag Day 38's topic as TBD per D3 (not redesigned, just flagged)
