# Day 13 — Smart Tool Selector

A 3-way benchmark of tool-selection strategies for agents with large tool catalogs: naive
all-tools binding, a `semantic-router` embedding pre-filter, and OpenAI Agents SDK's native
`ToolSearchTool` — run against a real 8-tool personal-assistant catalog and 8 human-phrased
queries.

```
uv sync && uv run main.py        # full run, all lanes
uv run main.py naive router      # a subset
uv run demo.py                   # offline self-check, no OpenAI, no network
```

## Pain point

Agents with 8+ tools bound are said to waste calls on irrelevant ones before reaching the
correct tool — burning latency, tokens, and sometimes failing outright. This day measures
that instead of repeating it.

## What was run

Same 8 queries, same real 8-tool catalog, three strategies plus one control:

1. **`naive`** — all 8 tools bound to every call, no filtering. `gpt-4.1-mini`.
2. **`router`** — `semantic-router` embedding similarity (local FastEmbed encoder, no API
   key) picks the top-2 routes before the agent sees any tools; only those get bound.
   `gpt-4.1-mini`.
3. **`native`** — OpenAI's hosted `tool_search` discovers tools from a namespace.
   `gpt-5.4-mini`, because the API refuses `tool_search` on `gpt-4.1-mini` (see below).
4. **`naive-ts`** — *control, not a strategy*: the naive baseline re-run on `gpt-5.4-mini`
   so the native lane has a same-model comparison point.

Tools are real (local JSON stores for email/calendar/contacts/reminders; Open-Meteo,
Frankfurter, and DuckDuckGo for weather/currency/web). Outcome is graded on the *final*
tool used, capped at 5 calls per query.

## Results

Two full runs, both reported — no cherry-picking:

```
run 1                                                  run 2
Strategy  Prec  Inc  AvgCalls  Tokens          Strategy  Prec  Inc  AvgCalls  Tokens
------------------------------------          ------------------------------------
naive        8    0      1.00    8213          naive        8    0      1.12    8828
router       8    0      1.00    3445          router       8    0      1.00    3458
native       8    0      1.12   13429          native       8    0      1.00   12021
naive-ts     7    1      1.12    8529          naive-ts     8    0      1.12    9032
```

Zero Acceptable and zero Failed in both runs — every lane landed on the *primary* tool on
every query it answered.

**The premise did not reproduce.** At 8 tools, nothing thrashes. Every strategy went 8/8
Precise at ~1.0 tool calls, including the naive baseline it was supposed to embarrass.
`gpt-4.1-mini` picked the right tool first try on all 8 queries, including both
deliberately ambiguous ones — it chose the *primary* tool on both, never needing the
acceptable-set fallback. Whatever the tool-count threshold for confusion is, 8 is under it.

**The pre-filter's real win is cost, not accuracy.** `router` matched naive's accuracy on
**54–61% fewer billed tokens** — 3,445–3,803 across four runs against naive's 8,213–8,828 —
because it never sends the 7 irrelevant tool schemas. This is the most stable number here:
the difference is mostly input tokens, and input tokens are a function of how many schemas
you serialize, not of what the model decides. (The spread within the router lane is
entirely extra tool *calls* on the odd run, not routing variance.) Latency was a wash — the
local encoder step costs ~0.3s, roughly cancelling the smaller payload's savings.

**Native `ToolSearchTool` cost more than the problem it solves.** 12,021–13,429 tokens: 1.3–1.6x
the *same-model* `naive-ts` control, and ~3.5x the pre-filter. The discovery round trip
outweighs the smaller initial tool payload at this catalog size. It would presumably invert
somewhere north of 8 tools; that crossover is not measured here.

**One Incorrect appeared in run 1 and did not reproduce.** `naive-ts` (`gpt-5.4-mini`) called
`search_contacts` then `search_calendar` on "Put a 1:1 with Priya on my calendar for Monday
at 10am" and stopped without creating the event; run 2 got it in one call. n=1, unexplained,
not a finding — noted because it's the only non-Precise outcome the harness has ever
produced.

### What this does not show

n=8 queries × 1 run per cell per pass, temperature unpinned. The accuracy and latency columns
are not powered to show anything — 8/8 with zero failures bounds the failure rate at roughly
[0, 31%], which is a weak bound. The catalog is also 8 semantically disjoint tools against
clean single-intent queries, which is close to a best case for tool selection. Treat the
token column as the result and the rest as instrumentation.

## The `tool_search` confound

`ToolSearchTool` is not available on `gpt-4.1-mini`. Probed and rejected: `gpt-4.1-mini`,
`gpt-4.1`, `gpt-4o-mini`, `gpt-5`, `gpt-5.1`, `gpt-5.4-nano`. Supported from `gpt-5.2` up.
The native lane runs on `gpt-5.4-mini` and the `naive-ts` control lane exists so that lane's
numbers mean something. See `docs/adr/0003`.

Also undocumented-by-surprise: `tool_namespace()` alone isn't enough — the API additionally
requires at least one tool flagged `defer_loading`, or it 400s with "requires at least one
deferred tool."

## Stack

- **OpenAI Agents SDK** — agent execution, tool binding, native `ToolSearchTool` lane
- **semantic-router** + **fastembed** — embedding pre-filter, local ONNX encoder, no extra
  API key. Note: `semantic-router[local]` and `[fastembed]` are gated to `python<3.13` in
  package metadata, so on this repo's 3.13 they install nothing — depend on `fastembed`
  directly.
- Plain Python harness — no LangGraph, single-call comparison per strategy per query

## Provider

OpenAI, hosted — deviates from this repo's local-first default because comparing against
OpenAI's native `ToolSearchTool` requires their SDK. `OPENAI_API_KEY` and `DAY13_MODEL` come
from `.env` (gitignored). The `semantic-router` pre-filter step itself stays local and free.

## Forward application

- The pre-filter is a drop-in for any future day binding 4-5+ tools — but on this evidence
  bind it for the **token bill**, not for accuracy, until a catalog is big enough to
  actually confuse the model.
- Habit worth keeping: every new tool ships with 2-3 example utterances as a
  `semantic-router` `Route`, not just a docstring.
- Routing layer is provider-agnostic — drops in front of Claude Agent SDK or Google ADK
  without a rewrite.
- The obvious follow-up this day doesn't answer: **where is the crossover?** Rerun at 15,
  30, 60 tools and find the catalog size where naive starts to thrash and native
  `tool_search` starts to pay for itself.

## Files

- `tools.py` — the 8-tool catalog, all real work (`docs/adr/0002`)
- `bench.py` — ground truth, grading, tabulation. Pure and offline.
- `strategies.py` — the three lanes plus the control, behind one `run(query) -> Result` shape
- `main.py` — harness entrypoint
- `demo.py` — offline self-check for grading + tabulation
- `data/` — local stores the tools read and write (seeded on first run, gitignored)
- `BRIEF.md` — demo/recording brief: what's filmable, what to keep off camera, and why

See `specs/day-13-smart-tool-selector.md` for the spec, `CONTEXT.md` for vocabulary, and
`docs/adr/` for the hard-to-reverse decisions.
