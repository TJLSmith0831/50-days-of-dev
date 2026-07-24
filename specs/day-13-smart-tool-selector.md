# Spec: Day-13 Smart Tool Selector

## Problem Statement

Agents with many tools bound (8+) waste calls on irrelevant tools before reaching the correct one — burning latency, tokens, and sometimes failing outright. This gets worse as a tool catalog grows: too many tools overwhelm the model and increase errors. Builders need a concrete, measured comparison of mitigation strategies rather than folklore about "keep your tool count low."

## Solution

Build a harness that runs the same 8 realistic, human-phrased queries against the same real 8-tool personal-assistant catalog through three tool-selection strategies — naive all-tools binding, a `semantic-router` embedding pre-filter, and OpenAI Agents SDK's native `ToolSearchTool` — and tabulates outcome (Precise/Acceptable/Incorrect/Failed), tool-call count, end-to-end latency, and OpenAI-billed token count per query per strategy into a single comparison report.

## User Stories

1. As a builder evaluating agent architectures, I want to see the naive all-tools baseline thrash (call several wrong tools before the right one, or fail outright), so that the problem is demonstrated, not just asserted.
2. As a builder, I want a `semantic-router` pre-filter lane that picks the relevant route(s) via embedding similarity before the agent sees any tools, so that only matched tool(s) get bound and no LLM call is spent on the routing decision itself.
3. As a builder, I want a native `ToolSearchTool` lane using OpenAI Agents SDK's built-in dynamic tool discovery, so that I have an "industry default" comparison point, not just my own DIY approach.
4. As a builder, I want each of the 8 test queries run through all 3 strategies against the identical 8-tool catalog, so that the comparison is apples-to-apples.
5. As a builder, I want the queries phrased the way an actual human would ask, including two that are genuinely ambiguous, so that the test reflects real usage instead of contrived clean-room prompts.
6. As a builder, I want outcome graded as Precise / Acceptable / Incorrect / Failed based on the *final* tool the agent actually used (not the first call), so that correctness measures task success, with tool-call count telling the efficiency story separately.
7. As a builder, I want a hard cap on tool calls per query (5), so that "failing outright" is an observable, reproducible outcome rather than something that only shows up if a strategy happens to error.
8. As a builder, I want the 8 tools to do real things against free, no-auth-required local/external resources, so that the benchmark exercises genuine tool execution, not theater.
9. As a builder, I want end-to-end wall-clock latency measured per query per strategy — including `semantic-router`'s local routing step — so that latency reflects what a user actually waits through, not a favorably-trimmed number.
10. As a builder, I want token count measured as OpenAI-billed tokens only (excluding the local routing step), so that cost numbers reflect actual spend.
11. As a builder, I want all three strategies run on the identical underlying model (`gpt-4.1-mini`), so that latency/token/outcome differences are attributable to the selection strategy, not the model.
12. As a builder, I want a final report table across all 8 queries × 3 strategies, so that the result is skimmable in one view.
13. As a builder, I want the `semantic-router` routing step to run locally with no extra API key, so that only the agent execution step incurs OpenAI cost.
14. As a repo maintainer, I want the day's own `AGENTS.md` to note the deviation from local-first defaults and why, so that the provider choice is traceable per repo convention.
15. As a future day author (Days 38-41 and beyond) binding several tools to one agent, I want this pre-filter approach to be reusable as a drop-in, so that I don't re-derive it from scratch.
16. As a builder deciding whether to add a new tool to an agent, I want the habit of writing 2-3 example utterances as a `semantic-router` `Route` established here, so that future agents don't inherit the same thrashing problem as their tool catalogs grow.

## Implementation Decisions

- **Comparison harness**: plain Python script that runs all 8 queries through all 3 strategies and tabulates results. No LangGraph — this is a single-call comparison per strategy per query, not a multi-step workflow.
- **Tool catalog** (personal-assistant domain, 8 tools, real logic / free / no-auth backing):
  - `send_email` — writes to a local outbox file (no live SMTP send during benchmark runs)
  - `search_calendar`, `create_calendar_event` — read/write against a local ICS or JSON file acting as the calendar
  - `search_contacts` — queries a local JSON contacts file
  - `set_reminder` — writes to a local reminders store
  - `search_web` — real DuckDuckGo search, no key (same approach as Day 12's researcher agent)
  - `get_weather` — real Open-Meteo call, no key
  - `convert_currency` — real free FX-rate API call, no key
- **Test set**: 8 fixed, human-phrased queries against the fixed catalog, each hand-labeled with a primary tool and an acceptable-tool set. 6 of 8 are unambiguous (single-tool acceptable set); 2 are genuinely ambiguous by realistic phrasing:
  - "Remind me to call the dentist tomorrow morning" → primary `set_reminder`, acceptable {`set_reminder`, `create_calendar_event`}
  - "Let the team know the meeting moved to 3pm" → primary `send_email`, acceptable {`send_email`, `create_calendar_event`}
- **Strategy 1 (naive baseline)**: all 8 tools bound to every agent call, no filtering.
- **Strategy 2 (semantic-router pre-filter)**: `semantic-router` picks the relevant route(s) via embedding similarity before the agent call; only the matched tool(s) are bound. Local encoder (`HuggingFaceEncoder` or `FastEmbedEncoder`).
- **Strategy 3 (native ToolSearchTool)**: OpenAI Agents SDK's built-in dynamic tool discovery, vendor default configuration.
- **Outcome grading** (per query per strategy, based on the final tool the agent actually used to answer, not the first call):
  - **Precise** — final tool = primary
  - **Acceptable** — final tool in the acceptable set, not primary
  - **Incorrect** — final tool called, not in the acceptable set
  - **Failed** — no acceptable tool landed within a 5-tool-call cap per query
  - Argument correctness is not graded — outcome is selection-only, since argument extraction is identical downstream of tool choice across all three strategies.
- **Latency**: end-to-end wall-clock per query per strategy, from receiving the query to the final answer — includes `semantic-router`'s local routing step for that strategy.
- **Token count**: OpenAI-billed tokens only; the local routing step burns no billable tokens and is excluded.
- **Model**: `gpt-4.1-mini` pinned across all three strategies. `ToolSearchTool` model-compatibility is verified at implementation time; if it forces a different model for that lane, the deviation is documented in the report as a confound, not hidden.
- **Provider**: OpenAI, hosted, for the agent execution layer and native `ToolSearchTool` lane — required because `ToolSearchTool` is OpenAI Agents SDK-specific. `OPENAI_API_KEY` already validated/wired from Day 12, so no new secret onboarding. This deviates from the repo's local-first default; the day's own `AGENTS.md` records the justification per root `AGENTS.md` convention.
- **Dependencies**: OpenAI Agents SDK, `semantic-router[local]`.

## Testing Decisions

- **What makes a good test**: verify external behavior — that a strategy, given a query and the fixed tool catalog, produces the expected outcome tier (Precise/Acceptable/Incorrect/Failed) and call count — not internal implementation details of any SDK.
- **Test seams** (highest, fewest seams preferred):
  1. **Primary seam**: the per-strategy "select and call" function — given a query, return the sequence of tools called and the final tool used. All three strategies expose this same shape so one test harness can drive all three and one grading function can score all three against the hand-labeled ground truth (primary/acceptable sets above).
  2. The grading function itself (tool-call sequence → outcome tier) is pure and testable in isolation with fixture inputs, no live API calls.
  3. The comparison/tabulation step (aggregating 8 queries × 3 strategies into the report) is tested independently with fixture per-query results.
- **Prior art**: Day 10/11's pattern of an offline, no-live-dependency self-check (`demo.py` style) as the primary verification path for the grading/tabulation logic, since this repo has no CI and the entrypoint run is the check. Live strategy execution against real tools/APIs is verified by running the actual harness, not mocked in tests.
- **Manual verification**: run the harness against the live catalog and all 8 queries, confirm the report table renders all 3 strategies × 8 queries with outcome, call count, latency, and token count populated, and spot-check that the two ambiguous queries land in their documented acceptable sets at least for the router/native-search lanes.

## Out of Scope

- More than 8 tools or 8 queries — fixed small catalog for a legible comparison, not a stress test at scale.
- Comparison lanes for other SDKs' native tool-search features (Claude Agent SDK, Google ADK) — noted as future reuse, not built here.
- A general-purpose reusable routing library extracted from this day's code — the habit/pattern is documented for reuse; extraction into a shared package is a separate future effort.
- Fine-tuning or training a custom router/classifier — routing is off-the-shelf `semantic-router` embedding similarity only.
- Argument-correctness grading — outcome is selection-only (see Implementation Decisions).
- Live outbound email sending — `send_email` writes to a local outbox file rather than a real SMTP send, to keep benchmark runs repeatable and side-effect-free toward real people.
- Production-grade error handling/retries for the OpenAI API calls — this is a benchmark script, not a shipped service.

## Further Notes

- This day intentionally deviates from the repo's local-first provider default; the justification (native `ToolSearchTool` requires OpenAI's SDK, `OPENAI_API_KEY` already wired from Day 12) is recorded in `day-13-smart-tool-selector/AGENTS.md` per root `AGENTS.md` convention.
- Interview-ready framing: benchmarking a DIY embedding-router against a vendor's native tool-search feature, with real latency/token numbers, is the intended takeaway artifact beyond the day's code.
- `ToolSearchTool`'s model compatibility is an implementation-time verification item, not resolved in this spec (see Implementation Decisions).
- Domain vocabulary and the two hard-to-reverse decisions this spec makes (outcome tiering + failure cap, and real-vs-mocked tools) are recorded in `day-13-smart-tool-selector/CONTEXT.md` and `day-13-smart-tool-selector/docs/adr/`.
