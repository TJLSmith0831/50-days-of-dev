# Day 13 — Smart Tool Selector — AGENTS.md
3-way comparison of tool-selection strategies (naive all-tools, semantic-router pre-filter, native ToolSearchTool) across 8 real, human-phrased queries against a real 8-tool personal-assistant catalog

## Stack
Python · OpenAI Agents SDK (agent execution + native `ToolSearchTool`) · semantic-router + fastembed (local ONNX encoder) · hosted (OpenAI, because the `ToolSearchTool` comparison lane requires their SDK; `OPENAI_API_KEY` + `DAY13_MODEL` from `.env`, already validated from Day 12)

## Commands (verified 2026-07-24)
- `uv run main.py` — all 4 lanes × 8 queries, prints the comparison report (~2 min, live API)
- `uv run main.py naive router` — subset of lanes
- `uv run demo.py` — offline self-check of grading + tabulation, no OpenAI, no network

## Concept
Agents with many tools bound are said to waste calls on irrelevant ones before reaching the correct tool. This day measures it: outcome (Precise/Acceptable/Incorrect/Failed — graded on the final tool used, capped at 5 calls), tool-call count, end-to-end latency, and OpenAI-billed tokens per query per strategy. **Headline result: at 8 tools nothing thrashes** — all lanes 8/8 Precise at ~1.0 calls. The pre-filter's win is a 58% token reduction at equal accuracy; native `ToolSearchTool` costs 63% *more* than naive. See `README.md`.

## Tool catalog
`send_email` (local outbox), `search_calendar` / `create_calendar_event` (local JSON), `search_contacts` (local JSON), `set_reminder` (local store), `search_web` (DuckDuckGo via `ddgs`, no key), `get_weather` (Open-Meteo, no key), `convert_currency` (Frankfurter, no key). All real logic, free/no-auth — no mocks, no live email sends.

## Gotchas
- `semantic-router`'s `[local]` and `[fastembed]` extras are gated to `python_version < "3.13"` in its metadata — on this repo's 3.13 they silently install **nothing** and `HuggingFaceEncoder()` raises ImportError. Depend on `fastembed` directly and use `FastEmbedEncoder`.
- `ToolSearchTool` is **not supported on `gpt-4.1-mini`** (nor `gpt-4.1`, `gpt-4o-mini`, `gpt-5`, `gpt-5.1`, `gpt-5.4-nano`). Served from `gpt-5.2` up. The native lane runs `gpt-5.4-mini`; the `naive-ts` lane is a same-model control so that confound is measured, not hidden. See `docs/adr/0003`.
- `tool_namespace()` alone 400s with "requires at least one deferred tool" — you must also set `defer_loading = True` on the returned copies.
- `DAY13_MODEL` carries an `openai:` provider prefix; the Agents SDK wants the bare id (`strategies.MODEL` strips it).
- `SemanticRouter.__call__(limit=N)` returns a bare `RouteChoice`, not a list, when only one route clears the threshold. Normalize before iterating.
- The call cap is enforced by a `RunHooks` subclass (`Recorder`) that raises on the 6th catalog-tool call, not by `max_turns` — this keeps the recorded call sequence and token tally available on the capped path.
- System prompt is deliberately neutral (no "use exactly one tool"). Adding that nudge prompts the naive baseline out of the thrashing the benchmark exists to measure.
- `data/` is gitignored and mutated by every run — `rm -rf data/` before a run you intend to report.
- Routing is local/free; only agent execution bills tokens. Latency is measured end-to-end including the routing step; token counts are OpenAI-only.
