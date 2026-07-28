# Day 17 — Reranked Search — AGENTS.md

Before/after a cross-encoder reranker on 10 BEIR SciFact queries, scored against published qrels, with the latency it costs.

## Stack

Python · fastembed (local ONNX, no API key) · `BAAI/bge-small-en-v1.5` bi-encoder + `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder · BEIR SciFact via HuggingFace `datasets`

## Commands (verified 2026-07-28)

- `uv run main.py --self-check` — offline metric/ranking/render checks. Verified.
- `uv run --group dev pytest -q` — 41 unit tests. Verified.
- `uv run main.py` — the live two-lane report. Verified 2026-07-28: 146.5s cold embed, seconds off `.cache/corpus.npz` after. Needs HuggingFace reachable.

## Concept

A reranker reorders a candidate set; it cannot retrieve. The dense lane's `recall@depth` is therefore a hard ceiling on the reranked lane's `recall@k`, and the report prints it as its own row — the finding survives whether or not the cross-encoder shows a lift.

## Gotchas

- **Documents are deliberately not chunked.** SciFact's qrels label documents and its corpus units are already abstract-length, so a chunker would break the correspondence with ground truth. The retrieval unit is `title\ntext`.
- **The baseline is a plain bi-encoder.** fastembed does not auto-apply bge's optional query-instruction prefix — `query_embed` falls through to `embed` for `OnnxTextEmbedding`. That is the right baseline (the prefix is a ~1-point effect and would muddy what the before/after measures), but it is a choice, not an oversight.
- **The 10 queries are picked by a rule fixed before any scores are seen** — first 10 by id with a positive judgment. Do not re-pick them after seeing a disappointing delta; probe with `--depth` or `DAY17_RERANKER` instead.
- **`PINNED_QUERY_IDS` is now filled**, so `select_query_ids` returns it and ignores the corpus it was handed. That is the point of pinning, and it is also a footgun for tests: any stub corpus is silently overridden and `run()` then dies on `query ids [...] are not in the SciFact query set`. `tests/conftest.py` resets the pin to `()` for every test via an autouse fixture; a test that wants a pin sets `dataset.PINNED_QUERY_IDS` itself. `main.py` reads it as `dataset.PINNED_QUERY_IDS` rather than importing the value, so there is exactly one place to patch.
- **At the default `--depth 50` the ceiling reads 1.000 and never binds** — dense recall@50 is perfect on these 10 queries, so that configuration cannot demonstrate the claim the day rests on. **`--depth 20` is the one to record**: ceiling drops to 0.900, query 4's gold sits at dense rank 27 and renders `-` in both lanes, and lane B's 0.800 visibly sits under the ceiling. Both runs are honest; only one shows the constraint. Do not manufacture a binding ceiling by re-picking queries — changing `--depth` is the sanctioned knob.
- **Depth 20 and depth 50 produce identical @10 metrics** (nDCG 0.702, recall 0.800, MRR 0.664, hit@1 6/10) for 380 ms vs 810 ms. The extra 30 candidates buy nothing at k=10 on this query set. Useful second finding, but n=10 — do not report the knee location as settled.
- **The quality delta is underpowered and the docs say so.** Four of the 10 queries have gold at rank 1 in both lanes, so the entire hit@1 move is 2 queries; exact McNemar gives one-sided p = 0.25. Keep that caveat in `README.md` and `BRIEF.md` if you touch them — it is what keeps the day honest. The latency numbers and the structural ceiling argument are the parts that hold.
- **Ties must break by document id.** ONNX CPU inference is deterministic, but equal cosine scores otherwise reorder run-to-run and make the table jitter. `top_k` sorts on `(-score, doc_id)` and a test pins it.
- **The corpus cache hashes every document id, not a sample of them.** Row `i` of `.cache/corpus.npz` is only meaningful beside `doc_ids[i]`. A corpus that kept its length but changed its order would otherwise pass a first/last-id check and return silently misaligned vectors — confident nonsense rather than an error. `tests/test_cache.py` pins the reordering case.
- **The cross-encoder loads before the corpus embed.** Constructed the other way round, a missing or unreachable reranker failed only after the ~40s embed, which the user then had to sit through again.
- **`src/lanes.py` imports fastembed inside its functions**, not at module top, so `--self-check` stays instant and cannot be broken by an onnxruntime import problem on a machine with no weights.
- **First live run downloads ~150 MB** from `huggingface.co` (+ `cdn-lfs.huggingface.co`). fastembed's GCS mirror at `storage.googleapis.com/qdrant-fastembed` carries the bi-encoder but **no cross-encoder**, so there is no HF-free path for this day. Corpus vectors cache to `.cache/corpus.npz`, keyed by model name and corpus size.
- **Deliberately not built:** an LLM-as-reranker third lane. That is Day 23's topic, it costs 500 local generations per run, and it would make this day about judging rather than reranking.
