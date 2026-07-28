# Reranked Search — Demo Brief / Handoff Doc

**Hook:** Every RAG tutorial tells you to add a reranker. Almost none of them tell you what it costs, or what it can't do. This run measures both — and the most useful number on screen is the one that caps how good the reranker could ever have been.

> **Status: numbers pending the live run.** Every `___` below is a slot to fill from a real `uv run main.py`. Do not record, and do not post, until they are filled from an actual run. See "Filling in the numbers".

---

## What reranking is (20–30s research beat)

Dense retrieval uses a **bi-encoder**: the query and each document are embedded *separately*, into the same vector space, and matched by cosine similarity. That separation is what makes it fast — every document vector is precomputed once, and a query is one embed plus a matrix multiply. It's also the weakness: the model never sees the query and the document *together*, so it can't reason about how a specific query term relates to a specific passage.

A **cross-encoder** does the opposite. It feeds the `(query, document)` pair through a transformer *jointly*, so every query token can attend to every document token. Far more accurate, and impossible to precompute — you pay a full forward pass per candidate, at query time.

So nobody cross-encodes a whole corpus. The standard pattern is two-stage: let the cheap bi-encoder pull a candidate set, then spend the expensive model only on those candidates. **Retrieve wide, rerank narrow.**

The thing that pattern quietly implies is the point of this build.

---

## What this build proves

1. **A reranker reorders; it cannot retrieve.** Lane B only ever sees the 50 candidates lane A pulled. Any gold document the bi-encoder missed is gone — no cross-encoder score can bring it back. The report prints lane A's `recall@50` as an explicit **ceiling row**: lane B's `recall@10` is mathematically incapable of exceeding it. This is true regardless of how the reranker scores, which is why it's the claim the day rests on.
2. **The quality delta, measured against real ground truth.** 10 BEIR SciFact queries, scored on BEIR's own published relevance judgments — nothing hand-labeled. nDCG@10 `___ → ___`, MRR@10 `___ → ___`, hit@1 `___/10 → ___/10`.
3. **The latency it costs.** Dense is `___ ms/query`; adding the cross-encoder over 50 candidates makes it `___ ms` — `___×` slower, or `___ ms` per candidate. That per-candidate number is the one that generalizes to your own corpus.
4. **It's fully local.** Two ONNX models via fastembed, on CPU. No API key, and no Ollama — this is the one day in the run that works on a laptop with Ollama not even installed.

---

## Setup

```bash
cd day-17-reranked-search
uv sync
uv run main.py --self-check   # offline sanity: metric math, tie-breaking, table widths
uv run main.py                # the real thing
```

First run downloads the SciFact dataset and ~150 MB of ONNX weights from HuggingFace, then spends ~40s embedding 5,183 abstracts. It caches the corpus vectors to `.cache/corpus.npz`, so every run after that skips straight to the queries.

**This cannot be run from the remote container** — `huggingface.co` is blocked there (`httpx.ProxyError: 403 Forbidden`), and fastembed's GCS mirror carries the bi-encoder but no cross-encoder, so there's no HF-free path. Run it on the laptop.

---

## Filling in the numbers

Do this once, before any recording:

1. **First run** — `uv run main.py`. Downloads, embeds, prints the report. It also prints `resolved query ids (pin these in src/dataset.py): [...]`.
2. **Pin the ids** — paste that list into `PINNED_QUERY_IDS` in `src/dataset.py`. From now on the query set is frozen and can't drift.
3. **Second run** — `uv run main.py` again. Should be seconds off the cache. *This* is the run you record.
4. **Fill in** every `___` in this file, plus the **Result** section of `README.md`, plus the tracker row in the root `README.md` (line 40: `planned` → `done`).

If the SciFact schema doesn't match what `src/dataset.py` expects, the first run raises a `KeyError` naming the columns it actually found — `_pick()` handles the `_id`/`id` and `query-id`/`query_id` variants, anything else needs a one-line fix.

---

## Demo scenario

Single terminal, one non-interactive command:

```bash
uv run main.py
```

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
2. **The two-stage pattern (5–7s):** a corpus bar of 5,183 narrowing to 50, then 50 narrowing to 10, with a cost tag on each stage. Caption: *retrieve wide, rerank narrow.*
3. **The catch (3–5s):** grey out everything outside the 50 and hold. Caption: *whatever stage one missed is already gone.*

### Terminal demo (35–50s)

4. **The command (3–5s):** `uv run main.py`, header prints — corpus size, both model names, the two lane definitions. Caption: *5,183 abstracts. two local ONNX models. no API key.*
5. **Per-query table (12–15s):** scroll through the 10 rows, let the `dense → rerank` columns and the `*` flags land. Caption: *rank of the correct paper, before and after.*
6. **Lane summary (10–12s):** hold on the three rows. Highlight the metric deltas, then drop to the **ceiling row** and hold there — this is the beat the whole video is built toward. Caption: *the reranker reorders. it never retrieves.*
7. **Latency table (8–10s):** hold on the per-candidate cost and the `___× slower` line. Caption: *`___ ms` per candidate. that's the bill.*
8. **The stack (3–5s):** final frame overlay — `bge-small` + `ms-marco-MiniLM`, ONNX, CPU. Caption: *no API key. no Ollama. runs on a laptop.*

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

Pick the variant that matches what actually ran. **Do not post the other one.**

**If the reranker showed a clear lift:**

> Every RAG guide says "add a reranker." Fewer mention what it costs, and almost none mention what it can't do.
>
> I ran 10 BEIR SciFact queries two ways: dense retrieval top-10 with `bge-small`, then the same search over-fetched to 50 and reordered by an `ms-marco-MiniLM` cross-encoder. Scored against BEIR's published relevance judgments — nothing hand-labeled.
>
> Reranking moved hit@1 from `___/10` to `___/10` and nDCG@10 from `___` to `___`. It also took the query from `___ ms` to `___ ms` — about `___ ms` per candidate scored.
>
> The number I keep coming back to isn't either of those. It's the dense lane's recall@50: `___`. That's a hard ceiling. A reranker reorders the candidate set; it can't add to it. Every relevant document stage one missed is gone before the cross-encoder ever runs — so past a point, a better reranker buys you nothing and a better retriever buys you everything.
>
> Both models are local ONNX on CPU. No API key, no Ollama.
>
> Day 17 of 50 — reranking. #AIEngineering #RAG #InformationRetrieval

**If the reranker showed little or no lift:**

> Every RAG guide says "add a reranker." I measured one, and on this corpus it barely mattered.
>
> 10 BEIR SciFact queries, scored against published relevance judgments. Dense retrieval with `bge-small` got hit@1 `___/10`. Adding an `ms-marco-MiniLM` cross-encoder over 50 candidates moved it to `___/10` — for `___×` the query latency.
>
> The reason is visible in the same table. The dense lane's recall@50 was `___`, and its recall@10 was already `___`. The correct paper was usually in the top 10 to begin with, so there was almost nothing left for a reranker to fix. It reorders the candidate set; it can't add to it.
>
> Which is the actual lesson: a reranker is worth its latency when your first stage retrieves well but ranks badly. Measure that gap before you buy the second model.
>
> Local ONNX on CPU, no API key, no Ollama.
>
> Day 17 of 50 — reranking. #AIEngineering #RAG #InformationRetrieval

---

## Checks before recording / handoff

1. `uv run main.py --self-check` ends with `self-check OK`.
2. `uv run --group dev pytest -q` — 40 passed.
3. A full `uv run main.py` has completed at least once, so `.cache/corpus.npz` exists and the recorded run is fast.
4. `PINNED_QUERY_IDS` in `src/dataset.py` is filled with the 10 resolved ids.
5. Every `___` in this file is replaced with a real measured number.
6. `README.md` **Result** section filled; root `README.md` line 40 flipped `planned` → `done` with a number-dense outcome cell.
7. `tput cols` ≥ 100.
8. `.cache/` is gitignored and stays out of the commit.
