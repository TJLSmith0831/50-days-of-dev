# Reranked Search

Does a cross-encoder reranker earn its latency on top of plain dense retrieval? Ten BEIR SciFact queries, two lanes, one table.

## Run

```bash
uv run main.py --self-check   # offline: metric math, tie-breaking, table widths
uv run main.py                # the live two-lane report
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

Not yet measured — the live run needs HuggingFace access. `--self-check` and the unit tests pass offline.
