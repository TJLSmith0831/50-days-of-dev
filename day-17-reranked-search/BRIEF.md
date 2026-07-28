# Reranked Search — Demo Brief / Handoff Doc

**Hook:** Every RAG tutorial tells you to add a reranker. Almost none of them tell you what it costs, or what it can't do. This run measures both — and the most useful number on screen is the one that caps how good the reranker could ever have been.

> **Status: measured 2026-07-28**, MacBook CPU, warm cache. Every number below came off a real `uv run main.py` with the query ids pinned. Quality metrics are deterministic and reproduce exactly across runs. Latency does not: per-candidate cost is steady (~16-19 ms) but the dense baseline is only ~6 ms, so the *ratio* swings (50-66x at depth 20, 160-192x at depth 50). Quote ms per candidate, not the multiplier.

---

## What reranking is (20–30s research beat)

Dense retrieval uses a **bi-encoder**: the query and each document are embedded *separately*, into the same vector space, and matched by cosine similarity. That separation is what makes it fast — every document vector is precomputed once, and a query is one embed plus a matrix multiply. It's also the weakness: the model never sees the query and the document *together*, so it can't reason about how a specific query term relates to a specific passage.

A **cross-encoder** does the opposite. It feeds the `(query, document)` pair through a transformer *jointly*, so every query token can attend to every document token. Far more accurate, and impossible to precompute — you pay a full forward pass per candidate, at query time.

So nobody cross-encodes a whole corpus. The standard pattern is two-stage: let the cheap bi-encoder pull a candidate set, then spend the expensive model only on those candidates. **Retrieve wide, rerank narrow.**

The thing that pattern quietly implies is the point of this build.

---

## What this build proves

1. **A reranker reorders; it cannot retrieve.** Lane B only ever sees the candidates lane A pulled. Any gold document the bi-encoder missed is gone — no cross-encoder score can bring it back. The report prints lane A's `recall@depth` as an explicit **ceiling row**: lane B's `recall@10` is mathematically incapable of exceeding it. **At `--depth 20` this binds and is visible**: ceiling `0.900`, lane B `0.800`, and query 4's gold paper renders `-` in both lanes because it sits at dense rank 27 and never entered the candidate set. (At the default `--depth 50` the ceiling is `1.000` and never bites — record depth 20.)
2. **The quality delta, measured against real ground truth.** 10 BEIR SciFact queries, scored on BEIR's own published relevance judgments — nothing hand-labeled. nDCG@10 `0.604 → 0.702`, MRR@10 `0.532 → 0.664`, hit@1 `4/10 → 6/10`. Recall@10 `0.850 → 0.800` — it went *down*. Underpowered at n=10; see "What to claim, and what not to".
3. **The latency it costs.** Dense is `~6 ms/query`; the cross-encoder over 20 candidates makes it `350–380 ms` — **50–66× slower**, or `~18 ms` per candidate. Quote the per-candidate number, not the multiplier: the dense baseline is only ~6 ms, so the ratio swings run to run while `ms per candidate` stays put. That per-candidate number is also the one that generalizes to your own corpus.
4. **Depth has a knee.** Going from 20 candidates to 50 cost `2.1×` the query latency and moved **no @10 metric at all** — identical nDCG, recall, MRR and hit@1. Over-fetching is not free and is not automatically better.
5. **It's fully local.** Two ONNX models via fastembed, on CPU. No API key, and no Ollama — this is the one day in the run that works on a laptop with Ollama not even installed.

---

## Setup

```bash
cd day-17-reranked-search
uv sync
uv run main.py --self-check   # offline sanity: metric math, tie-breaking, table widths
uv run main.py --depth 20     # the real thing — record this one
```

First run downloads the SciFact dataset and ~150 MB of ONNX weights from HuggingFace, then spends ~40s embedding 5,183 abstracts. It caches the corpus vectors to `.cache/corpus.npz`, so every run after that skips straight to the queries.

**This cannot be run from the remote container** — `huggingface.co` is blocked there (`httpx.ProxyError: 403 Forbidden`), and fastembed's GCS mirror carries the bi-encoder but no cross-encoder, so there's no HF-free path. Run it on the laptop.

---

## What the measured run actually showed

Corpus embed took 146.5s cold; every run since is off `.cache/corpus.npz`. Resolved query ids `1, 3, 5, 13, 36, 42, 48, 49, 50, 51`, now pinned in `src/dataset.py`.

| Lane | nDCG@10 | Recall@10 | MRR@10 | Hit@1 | median ms/query |
|---|---|---|---|---|---|
| dense | 0.604 | 0.850 | 0.532 | 4/10 | 4.8 |
| dense + rerank (top-50) | **0.702** | 0.800 | **0.664** | **6/10** | 809.9 |
| ceiling (dense recall@50) | — | **1.000** | — | — | lane B cannot exceed this |

Three things to say out loud, in this order:

1. **The reranker won on ranking.** +0.098 nDCG@10, +0.132 MRR@10, two more queries with the right paper at rank 1. Two rows carry `*`.
2. **It lost on recall, and that is not a rounding error.** Recall@10 fell 0.850 → 0.800 because query 1's gold document sat at dense rank 6 and the cross-encoder shoved it to 49 — the `-43 !` row. A model that helps the average and wrecks one query is the normal case. Leave that row on screen.
3. **The ceiling was 1.000, so it never bound.** Every gold document was already inside the 50, which means this configuration never actually exercised the constraint the whole day is built on. Do not narrate the ceiling over this table — narrate it over the depth-20 one below, where it binds.

### `--depth 20` — record this one

```bash
uv run main.py --depth 20
```

| Lane | nDCG@10 | Recall@10 | MRR@10 | Hit@1 | median ms/query |
|---|---|---|---|---|---|
| dense | 0.604 | 0.850 | 0.532 | 4/10 | 5.8 |
| dense + rerank (top-20) | 0.702 | 0.800 | 0.664 | 6/10 | 380.2 |
| ceiling (dense recall@20) | — | **0.900** | — | — | lane B cannot exceed this |

**This is the better demo, for two reasons.**

**The ceiling binds, and one row proves it on camera.** Query 4's gold paper is at dense rank 27 — outside a 20-candidate set — so row 4 shows `-` in the dense column, `-` in the rerank column, `-` in delta. The reranker never saw that document. There is no score it could have assigned. Point at that row when you say *"it reorders, it cannot retrieve"* and the sentence is being demonstrated instead of asserted. Ceiling 0.900, lane B recall@10 0.800, sitting under it exactly as the math requires.

**Every @10 metric is identical to the depth-50 run — for less than half the latency.** Same 0.702 nDCG, same 0.800 recall, same 0.664 MRR, same 6/10 hit@1, at 380 ms instead of 810. Thirty extra candidates cost 2.1× the query time and moved nothing. That is a second, independent finding and it is genuinely useful: **depth is a cost knob with diminishing returns, and nobody tells you where the knee is on your corpus.**

The honest one-line version: **the reranker bought +2 hit@1 for ~18 ms per candidate, over-fetching past 20 bought nothing at all, and the ceiling row is how you'd know in advance whether either trade was available.**

### What to claim, and what not to

Say this on camera if quality numbers come up, or put it in the post:

- **The latency is solid.** Stable across repeated runs; the per-candidate cost (~16–19 ms) is the number that transfers to another corpus.
- **The ceiling is structural, not empirical.** Lane B ranks a subset of what lane A retrieved. That's true by construction — the depth-20 run *illustrates* it, it doesn't prove it, and it doesn't need to.
- **The quality delta is underpowered.** n=10, and four queries had gold at rank 1 in both lanes, so the whole hit@1 move is two queries flipping. Exact McNemar: two discordant pairs, both favoring the reranker, one-sided p = 0.25. Do not present 0.604 → 0.702 as a result about rerankers in general. It is a working pipeline reporting a directionally sensible number on ten queries.

Saying that out loud costs nothing and inoculates the whole post against the one comment that would otherwise land.

If the SciFact schema ever stops matching what `src/dataset.py` expects, the first run raises a `KeyError` naming the columns it actually found — `_pick()` handles the `_id`/`id` and `query-id`/`query_id` variants, anything else needs a one-line fix.

---

## Demo scenario

Single terminal, one non-interactive command:

```bash
uv run main.py --depth 20
```

**Record the `--depth 20` run, not the bare default.** Both are honest; only this one makes the ceiling bind on screen (0.900, with query 4 showing `-` in both lanes) and it finishes in half the time. If you want the depth-50 run as a second beat, use it for the "over-fetching bought nothing" comparison — same @10 metrics, 2.1× the latency.

Off a warm cache this finishes in seconds and prints four blocks: the header (corpus + models + lane definitions), the per-query table, the lane summary with the ceiling row, and the latency breakdown. There is no REPL and nothing to type — the whole terminal segment is a scroll and three holds.

That's a constraint worth designing around rather than fighting: the run is short, so the concept intro carries the explanation and the terminal carries the proof.

---

## Recording notes specific to this day

- **Record the second run, not the first.** The first run is a download plus a 40s embed — dead air, and it leaks a progress bar that has nothing to do with the point.
- **Do not delete `.cache/` before recording.** Same reason.
- **Terminal width ≥ 100 columns.** The report renders to exactly 100; at 99 every table wraps and the demo is ruined. `tput cols` before you hit record.
- **The per-query table is the money shot.** The `*` flags mark gold documents the reranker promoted to rank 1. If several rows carry `*`, that column tells the whole story without narration.
- **A `!` row is not a failure to hide.** It marks a query the reranker made *worse*. Leave it on screen — a reranker that helps on average and regresses individual queries is the honest picture, and hiding it is the kind of thing that gets caught in comments.

---

## Shot list (~50–70s)

### Research / concept intro (15–20s)

1. **Bi-encoder vs cross-encoder (8–10s):** split diagram. Left: query and document embedded down separate paths into two vectors, joined by a cosine arrow — label *precomputable, fast, never sees the pair together*. Right: query and document entering one transformer block jointly, arrows crossing between them — label *sees every pair, can't precompute*. Caption: *cheap and shallow, or expensive and deep.*
2. **The two-stage pattern (5–7s):** a corpus bar of 5,183 narrowing to 20, then 20 narrowing to 10, with a cost tag on each stage. Caption: *retrieve wide, rerank narrow.*
3. **The catch (3–5s):** grey out everything outside the 20 and hold. Caption: *whatever stage one missed is already gone.*

### Terminal demo (35–50s)

4. **The command (3–5s):** `uv run main.py --depth 20`, header prints — corpus size, both model names, the two lane definitions. Caption: *5,183 abstracts. two local ONNX models. no API key.*
5. **Per-query table (12–15s):** scroll through the 10 rows, let the `dense → rerank` columns and the `*` flags land. Caption: *rank of the correct paper, before and after.*
6. **Row 4 (5–7s) — the new hero shot.** Hold on the one row that reads `-  -  -`. Its gold paper is at dense rank 27, outside the 20 candidates, so the cross-encoder never saw it. Caption: *this one never made the shortlist. no reranker can fix that.*
7. **Lane summary (10–12s):** hold on the three rows. Highlight the metric deltas, then drop to the **ceiling row** — `0.900`, with lane B's `0.800` underneath it — and hold. This is the beat the whole video is built toward, and after shot 6 it lands as arithmetic rather than assertion. Caption: *the reranker reorders. it never retrieves.*
8. **Latency table (8–10s):** hold on the per-candidate cost and the `Nx slower` line — read whatever your take prints, it lands between 50× and 66×. Caption: *~18 ms per candidate. that's the bill.*
9. **Optional — the depth knee (5–8s):** cut to the depth-50 summary beside the depth-20 one. Identical nDCG, recall, MRR, hit@1; 810 ms vs 380. Caption: *30 more candidates. 2× the latency. zero difference.*
10. **The stack (3–5s):** final frame overlay — `bge-small` + `ms-marco-MiniLM`, ONNX, CPU. Caption: *no API key. no Ollama. runs on a laptop.*

---

## What NOT to demo

- **The first run's download and embed.** ~40s of progress bar that proves nothing. Record off the warm cache.
- **`--self-check`.** It's the fresh-clone gate and it's genuinely useful, but on camera it's a list of `OK`s about metric arithmetic — it explains nothing about reranking.
- **The unit tests.** Same reason. They belong in the README, not the video.
- **Any claim that the reranker "found" a document.** It cannot. If the narration drifts into *found* or *retrieved* instead of *promoted* or *reordered*, the video is arguing against its own ceiling row.
- **Nudging `--depth` or `DAY17_RERANKER` mid-demo to get a prettier table.** If you explored those, say so in the post; don't quietly record the best-looking configuration as if it were the default.
- **Re-picking the 10 queries.** The selection rule is fixed before any scores are seen — that's what makes the result meaningful. Tuning it after seeing a weak delta would be exactly the thing this repo keeps calling out.

---

## Frame

- Terminal fullscreen, dark theme, ≥ 100 columns, font large enough to read a 100-column table without zooming.
- Three deliberate holds: per-query table, ceiling row, latency line. Everything else can scroll.
- End held on the lane summary with the ceiling row visible for a full 2s.

---

## LinkedIn post draft

Written against the run above. The two speculative variants that used to live here are deleted — the reranker showed a clear ranking lift *and* a recall regression, which neither of them anticipated.

> Every RAG guide says "add a reranker." Fewer mention what it costs, and almost none mention what it can't do.
>
> I ran 10 BEIR SciFact queries two ways: dense retrieval top-10 with `bge-small`, then the same search over-fetched to 50 and reordered by an `ms-marco-MiniLM` cross-encoder. Scored against BEIR's published relevance judgments — nothing hand-labeled.
>
> Reranking moved hit@1 from 4/10 to 6/10 and nDCG@10 from 0.604 to 0.702. It also took the query from ~6 ms to ~370 ms — about 18 ms per candidate scored.
>
> It also made recall@10 *worse*, 0.850 → 0.800. One query had its correct paper at rank 6 and the cross-encoder pushed it to 19. A reranker that wins on average still loses individual queries, and the table shows both.
>
> But the row I keep coming back to is the one that's just three dashes. Query 4's correct paper sits at rank 27 in the dense lane — outside the 20 candidates — so the cross-encoder never saw it. Not scored badly. Never scored at all. That's why the report prints the dense lane's recall@20 as a ceiling row: 0.900, with the reranked lane's 0.800 sitting underneath it. A reranker reorders the candidate set. It cannot add to it.
>
> So the question isn't "should I add a reranker," it's "is my problem ranking or retrieval." If your stage-one recall at depth is already high, a cross-encoder buys you ordering and you pay per candidate for it. If it isn't, no reranker on the market can recover what stage one missed, and you're buying the wrong model.
>
> One more thing I didn't expect: going from 20 candidates to 50 cost 2.1× the latency and moved *no* metric — same nDCG, same recall, same MRR, same hit@1. Over-fetching isn't free and isn't automatically better.
>
> Caveat I'd rather state than have someone find: this is 10 queries. Four of them had the right paper at rank 1 in both lanes, so the hit@1 move is two queries flipping — an exact McNemar puts that at p = 0.25. Treat it as a working pipeline reporting a directionally sensible number, not as a result about rerankers in general.
>
> Both models are local ONNX on CPU. No API key, no Ollama.
>
> Day 17 of 50 — reranking. #AIEngineering #RAG #InformationRetrieval

---

## Checks before recording / handoff

1. ✅ `uv run main.py --self-check` ends with `self-check OK`.
2. ✅ `uv run --group dev pytest -q` — 41 passed.
3. ✅ A full `uv run main.py` has completed, so `.cache/corpus.npz` exists and the recorded run is fast.
4. ✅ `PINNED_QUERY_IDS` in `src/dataset.py` holds the 10 resolved ids.
5. ✅ Every `___` in this file is replaced with a real measured number.
6. ✅ `README.md` **Result** section filled; root `README.md` day-17 row flipped `planned` → `done`.
7. `tput cols` ≥ 100 — check at record time.
8. ✅ `.cache/` is gitignored and stays out of the commit.
9. **Record `uv run main.py --depth 20`, not the bare default.** The default's ceiling is 1.000 and never binds; depth 20 binds at 0.900 and puts the proof on screen as row 4's `-  -  -`.
10. **Don't quote the latency multiplier as a fixed number** — it swings 50–66× at depth 20 because the dense baseline is ~6 ms. Quote `~18 ms per candidate`, which holds.
