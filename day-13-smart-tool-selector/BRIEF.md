# Smart Tool Selector — Demo Brief

**Hook:** I built a benchmark to prove that giving an agent too many tools wrecks its accuracy. It doesn't. It wrecks your bill — and the vendor's official fix for it costs *more* than the problem.

---

## What it proves

1. **A local embedding pre-filter cuts billed tokens 54–61% at identical accuracy** — 3,445–3,803 vs 8,213–8,828 across four runs on the same 8 queries against the same 8-tool catalog. The routing step runs on a local ONNX encoder: no API key, no billable tokens, ~0.3s. The saving is structural, not lucky — you stop serializing 7 irrelevant tool schemas into every single call.
2. **OpenAI's native `ToolSearchTool` costs 1.3–1.6x the same-model baseline** on an 8-tool catalog — 12,021–13,429 tokens against a `naive-ts` control lane running the identical model. The tool-discovery round trip outweighs the smaller initial payload at this scale.
3. **`tool_search` is a gpt-5.2+ feature, and nothing tells you that until you get a 400.** Nine models probed; `gpt-4.1-mini`, `gpt-4.1`, `gpt-4o-mini`, `gpt-5`, `gpt-5.1`, and `gpt-5.4-nano` all reject it.

**Do not claim:** that the pre-filter makes the agent *more accurate*. It doesn't — every lane went 8/8 Precise, including the naive baseline. That's the finding, not a gap in it.

---

## Why this matters (the employer story)

This isn't "I know how to use an embedding model." It's "I build the measurement rig before I believe the folklore, and I report what it says."

- **Falsified my own premise.** The spec asserted that 8+ tools makes agents thrash. The harness said otherwise and I published that instead of tuning the test set until it agreed.
- **Caught a confound mid-build and controlled it.** `tool_search` isn't served on the pinned model, so the native lane had to move to `gpt-5.4-mini`. Rather than disclose that in a footnote, I added a fourth lane — the naive baseline re-run on that same model — so the comparison isolates the strategy from the model.
- **Separated the metrics that survive n=8 from the ones that don't.** The token gap held across four runs and is mechanically explicable. Accuracy and latency at this sample size are instrumentation, not results, and the writeup says so.
- **Found three undocumented API facts** that will save the next person building on this SDK an afternoon.

---

## Setup

```bash
cd day-13-smart-tool-selector
uv sync
rm -rf data                       # reset the local tool stores before a run you'll show
uv run main.py                    # all 4 lanes × 8 queries, ~2 min
```

Requires `OPENAI_API_KEY` and `DAY13_MODEL` in `day-13-smart-tool-selector/.env` (already configured).

---

## Pre-recording workflow

**Step 1 — Test without recording.**

1. `uv run demo.py` — offline grading self-check, no API. Must end with `self-check OK`.
2. `rm -rf data && uv run main.py` end to end.
3. Confirm: every `router` row shows a `pre-filter: 8 tools -> ...` line; the summary table has all four lanes with non-zero token counts; no `!` error lines.
4. If the `native` lane shows `Failed 0 calls 0 tokens` — **stop, do not record**. That's the `tool_search` 400, not a result. Check the model and `defer_loading`.
5. If `router` tokens aren't comfortably under half of `naive` — **stop**. The pre-filter isn't filtering.

**Step 2 — Record the terminal demo.**

Only once Step 1 passes on a clean dry run.

**Step 3 — Create the Remotion video.**

Composite the tool-bloat concept intro with the terminal recording.

---

## Demo scenario

Single terminal, full run:

```bash
rm -rf data && uv run main.py
```

Let it run live — the scrolling `pre-filter kept 2/8: ...` lines during execution are the visual proof that the routing step is real and happening per query, before any model call. Then hold on the summary table.

If 2 minutes is too long for the cut, `uv run main.py naive router` gives the token comparison in half the time — but you lose the native lane, which is where the counterintuitive result lives.

---

## Shot list (~50–60s)

### Remotion intro (10–15s)

1. **The setup (10–15s):** animated diagram — one agent, 8 tool schemas fanning into the prompt on *every* call, with only one of them ever used. Caption: *8 tools bound. One tool needed. You pay for all 8, every time.*

### Terminal demo (35–45s)

2. **The rig starts (5s):** header line — model, native-lane model, call cap — then the first query's four lanes firing. Caption: *same query, same catalog, four lanes.*
3. **The pre-filter working live (10s):** the scrolling `pre-filter kept 2/8: set_reminder, create_calendar_event` lines. Caption: *a local embedding step narrows the catalog before the model sees anything — no API call, no tokens.*
4. **Per-query detail (10s):** scroll to a query block showing all four lanes stacked — same `Precise` outcome, wildly different token counts, with the `pre-filter:` line visible under the router row. Caption: *identical answer. 1/3 the cost.*
5. **The summary table (10–15s):** hold on all four rows. Cursor/highlight on the Tokens column. Caption reads the numbers off *that* run rather than a remembered pair — they move ~10% run to run.
6. **The punchline (5s):** highlight the `native` row against `naive-ts`. Caption: *the vendor's built-in fix cost more than the problem — at 8 tools.*

---

## What NOT to demo

- **The accuracy columns as a result.** All four lanes go 8/8 Precise. Framing that as "my router is more accurate" is a claim the data doesn't support, and one sharp question kills it. The Outcome column is there to prove accuracy *didn't regress* — that's its whole job.
- **The latency column.** n=1 per cell against live APIs including DuckDuckGo. It's noise. Don't put a caption on it.
- **The run-1 `naive-ts` Incorrect.** It didn't reproduce in run 2. Showing it invites a story about model quality that one observation cannot carry.
- **A stale `data/` directory.** Repeated runs accumulate calendar events and the `search_calendar` output gets noisy on camera.
- **`demo.py`.** It proves the grading function is correct, not that the benchmark found anything. Mention it in prose if asked how the harness is verified.
- **The model-probe script**, unless you want a separate 10-second cut for it. It's a strong standalone fact but it's a different story from the token result.

---

## Frame

- Terminal fullscreen, dark theme. The tables are 90 columns — set the font size so the Tokens column is readable without zooming.
- The `pre-filter kept N/8` lines during the live run are the differentiator. Don't speed-ramp through them.
- End held on the summary table for 2s. The four-row block is the whole argument.

---

## LinkedIn post draft

> I built a benchmark to prove that giving an agent too many tools wrecks its accuracy.
>
> It doesn't. At 8 tools, every strategy I tested got 8/8 right — including the naive baseline that binds all of them to every call. The "too many tools confuses the model" thing didn't reproduce.
>
> What it wrecks is your bill. A local embedding pre-filter — no API key, no billable tokens — matched that accuracy on ~55-60% fewer tokens, because it stops serializing 7 irrelevant tool schemas into every request.
>
> The part I didn't expect: OpenAI's own built-in fix, the native ToolSearchTool, cost 1.3–1.6x *more* than the naive baseline on the same model. The tool-discovery round trip outweighs the smaller payload at this catalog size. It presumably pays off on a bigger catalog — finding that crossover is the next run.
>
> Bonus finding, undocumented anywhere I could see: `tool_search` isn't available on gpt-4.1-mini, gpt-4.1, gpt-4o-mini, gpt-5, or gpt-5.1. It's a gpt-5.2+ feature. You find out via a 400.
>
> Day 13 of 50 — tool selection. #AIEngineering #LLMOps #AgentArchitecture

---

## Checks before recording

1. `uv run demo.py` — ends with `self-check OK`
2. `rm -rf data` — stores reset, so `search_calendar` returns the 3 seeded events, not 30
3. `uv run main.py` dry run — 4 lanes × 8 queries, no `!` error lines
4. Every `router` row shows a `pre-filter: 8 tools -> ...` line
5. `native` lane has non-zero tokens (zero means the `tool_search` 400, not a result)
6. Router tokens land under half of naive — if not, the pre-filter is binding the whole catalog
7. Terminal width ≥ 95 columns, or the tables wrap and the demo is unreadable
