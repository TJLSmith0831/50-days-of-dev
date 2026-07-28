# Reranked Search

Does a cross-encoder reranker earn its latency on top of plain dense retrieval? Ten BEIR SciFact queries, two lanes, one table.

## Run

```bash
uv run main.py --self-check   # offline: metric math, tie-breaking, table widths
uv run main.py --depth 20     # the live two-lane report, ceiling binding
uv run main.py                # same, at the default depth 50
uv run --group dev pytest -q  # unit tests
```

No API key and no Ollama — both models are local ONNX via fastembed. The first live run downloads the SciFact dataset and ~150 MB of weights from HuggingFace; corpus embeddings are then cached to `.cache/corpus.npz`, so later runs skip the ~40s embed.

## The two lanes

- **A — dense**: embed all 5,183 SciFact abstracts with `BAAI/bge-small-en-v1.5`, cosine top-10.
- **B — dense + rerank**: the *same* retrieval over-fetched to top-50, then all 50 `(query, document)` pairs scored by the `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder and cut back to top-10.

Same k out, wider net in, so the reranker is the only variable.

## The point

A reranker **reorders; it cannot retrieve.** The report prints the dense lane's `recall@50` as a **ceiling row**: whatever gold documents the bi-encoder failed to pull into the candidate set are gone, and no reranker can recover them. That bound holds regardless of how well the cross-encoder scores, which is why it sits next to the two lanes rather than in a footnote.

## How the queries were chosen

The first 10 distinct query ids in the SciFact `test` qrels, by id order, keeping only ids with at least one positive judgment. The rule is fixed before any scores are seen so the set cannot be tuned toward a flattering delta. Ground truth is BEIR's published relevance judgments — nothing here is hand-labeled.

Documents are **not chunked**: SciFact corpus units are already abstract-length and the qrels label documents, so chunking would break the correspondence with the ground truth. The retrieval unit is `title\ntext`.

## Result

Measured 2026-07-28, MacBook CPU, warm cache. Query ids `1, 3, 5, 13, 36, 42, 48, 49, 50, 51` — now pinned in `src/dataset.py`.

| Lane | nDCG@10 | Recall@10 | MRR@10 | Hit@1 | median ms/query |
|---|---|---|---|---|---|
| dense | 0.604 | 0.850 | 0.532 | 4/10 | 4.8 |
| dense + rerank (top-50) | **0.702** | 0.800 | **0.664** | **6/10** | 809.9 |
| ceiling (dense recall@50) | — | **1.000** | — | — | lane B cannot exceed this |

The reranker earned its keep on ranking: **+0.098 nDCG@10, +0.132 MRR@10, hit@1 4/10 → 6/10**. It cost **~167× the query latency** — 4.8 ms → 810 ms, about **16.3 ms per candidate scored**. That per-candidate number is the one that transfers to another corpus.

Two things the table says that the headline doesn't:

- **Recall@10 went *down*, 0.850 → 0.800.** Query 1 had its gold document at dense rank 6 and the cross-encoder pushed it to 49. A reranker that improves the average still regresses individual queries; the `!` rows are the honest picture, not noise to hide.
- **The ceiling was 1.000, so it never bound.** Dense recall@50 was perfect — every gold document was already in the candidate set, so this configuration never actually exercised the constraint the day is built on. `--depth 20` does.

### `--depth 20` — where the ceiling actually binds

```bash
uv run main.py --depth 20
```

| Lane | nDCG@10 | Recall@10 | MRR@10 | Hit@1 | median ms/query |
|---|---|---|---|---|---|
| dense | 0.604 | 0.850 | 0.532 | 4/10 | 5.8 |
| dense + rerank (top-20) | 0.702 | 0.800 | 0.664 | 6/10 | 380.2 |
| ceiling (dense recall@20) | — | **0.900** | — | — | lane B cannot exceed this |

Query 4's gold document sits at dense rank 27, outside a 20-candidate set, so it renders `-` in **both** lanes. That single row is the claim made visible: the reranker never saw the document, and no score it could have assigned would have brought it back. The ceiling drops to 0.900 and lane B's recall@10 of 0.800 sits under it, as it must.

The second finding is the one worth the latency budget: **every @10 metric is identical to the depth-50 run** — same nDCG, same recall, same MRR, same hit@1 — for **380 ms instead of 810**. Over-fetching 30 extra candidates cost 2.1× the query time and moved nothing. Depth is a knob with a real cost and, past a point, no return; the only way to know where that point is on your corpus is to measure it. (n=10, so treat the exact crossover as indicative, not settled.)

### What this does and doesn't establish

The latency numbers are solid — stable across repeated runs, and the per-candidate cost generalizes. The ceiling is a structural fact (lane B ranks a subset of what lane A retrieved), true independent of any measurement; the `--depth 20` run illustrates it rather than proving it.

The quality delta is **underpowered and should not be quoted as a result about rerankers in general**. n=10, and four of those queries had gold at rank 1 in both lanes, so the entire hit@1 move is two queries flipping. An exact McNemar on hit@1 has two discordant pairs, both favoring the reranker: one-sided p = 0.25. The recall regression is a single query. Directionally consistent with what cross-encoders are known to do, not evidence for it.
