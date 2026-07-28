# Day 17 — Reranked Search — AGENTS.md

Before/after a cross-encoder reranker on 10 BEIR SciFact queries, scored against published qrels, with the latency it costs.

## Stack

Python · fastembed (local ONNX, no API key) · `BAAI/bge-small-en-v1.5` bi-encoder + `Xenova/ms-marco-MiniLM-L-6-v2` cross-encoder · BEIR SciFact via HuggingFace `datasets`

## Commands (verified 2026-07-28)

- `uv run main.py --self-check` — offline metric/ranking/render checks. Verified.
- `uv run --group dev pytest -q` — 27 unit tests. Verified.
- `uv run main.py` — the live two-lane report. **Not yet run**; needs HuggingFace reachable.

## Concept

A reranker reorders a candidate set; it cannot retrieve. The dense lane's `recall@depth` is therefore a hard ceiling on the reranked lane's `recall@k`, and the report prints it as its own row — the finding survives whether or not the cross-encoder shows a lift.

## Gotchas

- **Documents are deliberately not chunked.** SciFact's qrels label documents and its corpus units are already abstract-length, so a chunker would break the correspondence with ground truth. The retrieval unit is `title\ntext`.
- **The baseline is a plain bi-encoder.** fastembed does not auto-apply bge's optional query-instruction prefix — `query_embed` falls through to `embed` for `OnnxTextEmbedding`. That is the right baseline (the prefix is a ~1-point effect and would muddy what the before/after measures), but it is a choice, not an oversight.
- **The 10 queries are picked by a rule fixed before any scores are seen** — first 10 by id with a positive judgment. Do not re-pick them after seeing a disappointing delta; probe with `--depth` or `DAY17_RERANKER` instead.
- **Ties must break by document id.** ONNX CPU inference is deterministic, but equal cosine scores otherwise reorder run-to-run and make the table jitter. `top_k` sorts on `(-score, doc_id)` and a test pins it.
- **`src/lanes.py` imports fastembed inside its functions**, not at module top, so `--self-check` stays instant and cannot be broken by an onnxruntime import problem on a machine with no weights.
- **First live run downloads ~150 MB** from `huggingface.co` (+ `cdn-lfs.huggingface.co`). fastembed's GCS mirror at `storage.googleapis.com/qdrant-fastembed` carries the bi-encoder but **no cross-encoder**, so there is no HF-free path for this day. Corpus vectors cache to `.cache/corpus.npz`, keyed by model name and corpus size.
- **Deliberately not built:** an LLM-as-reranker third lane. That is Day 23's topic, it costs 500 local generations per run, and it would make this day about judging rather than reranking.
