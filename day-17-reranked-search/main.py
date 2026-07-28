"""Reranked Search — does a cross-encoder earn its latency on top of dense retrieval?

Ten BEIR SciFact queries run through two lanes: dense top-k, and the same dense
retrieval over-fetched to `--depth` then reordered by a cross-encoder. The report
also prints the dense lane's recall@depth, which is the hard ceiling on what the
reranker could ever achieve — it reorders, it cannot retrieve.
"""

from __future__ import annotations

import argparse
import math
import sys

import numpy as np

from src import dataset, report
from src.dataset import load_scifact, select_query_ids
from src.lanes import BI_ENCODER, CROSS_ENCODER, DenseIndex, Reranker, Timings, top_k
from src.metrics import first_gold_rank, ndcg_at_k, recall_at_k, summarize


def say(line: str) -> None:
    """Emit a line unbuffered so a terminal capture stays live."""
    print(line, flush=True)


def _check(label: str, detail: str) -> None:
    say(f"  {label:<12}{detail:<62}OK")


def self_check() -> None:
    """Deterministic, offline. No dataset, no model weights, no network."""
    say("self-check — no dataset download, no model weights, no network")

    gold = {"d7": 1}
    assert ndcg_at_k(["d7", "d1"], gold, 10) == 1.0
    assert math.isclose(ndcg_at_k(["d1", "d7"], gold, 10), 1 / math.log2(3))
    assert ndcg_at_k(["d1", "d2"], gold, 10) == 0.0
    assert ndcg_at_k(["d7"], {}, 10) == 0.0
    _check("metrics", "nDCG 1.0 / 0.63093 / 0.0, and 0.0 with no judgments")

    two = {"d7": 1, "d9": 1}
    ranking = ["d7", "d1", "d2", "d3", "d9"]
    assert recall_at_k(ranking, two, 1) == 0.5
    assert first_gold_rank(["d1", "d7"], gold) == 2
    assert first_gold_rank(["d1", "d2"], gold) is None
    assert summarize([ranking], [two], k=5).hits == 1
    _check("aggregate", "recall / first-gold-rank / summarize agree on fixtures")

    values = [recall_at_k(ranking, two, k) for k in range(1, 6)]
    assert values == sorted(values)
    _check("monotonic", "recall@k is non-decreasing in k")

    vectors = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    tied = top_k(vectors, np.array([1.0, 0.0], dtype=np.float32), ["d2", "d3", "d1"], 2)
    assert [doc_id for doc_id, _ in tied] == ["d1", "d2"], "ties must break by doc id"
    _check("ranking", "cosine top-k orders correctly and breaks ties by id")

    long_text = "x" * 400
    assert len(report.truncate(long_text, report.QUERY_WIDTH)) == report.QUERY_WIDTH
    rows = [report.QueryRow("1", long_text, 999, 50, 1)]
    for line in report.render_per_query(rows, depth=50):
        assert len(line) <= report.WIDTH
    _check("render", f"worst-case row stays inside {report.WIDTH} columns")

    pinned = dataset.PINNED_QUERY_IDS
    if pinned:
        assert len(set(pinned)) == len(pinned) == 10
        assert list(pinned) == sorted(pinned, key=dataset._sort_key), "pin in selection order"
        _check("pinned", "10 distinct query ids pinned, in selection order")
    else:
        _check("pinned", "no ids pinned yet — selection rule resolves them at run time")

    say("self-check OK")


def run(top_n: int, depth: int) -> None:
    if top_n > depth:
        raise SystemExit(
            f"--top-k {top_n} exceeds --depth {depth}: the reranker only ever sees "
            f"{depth} candidates, so a top-{top_n} cut would compare unequal lanes."
        )

    say("loading BEIR SciFact (first run downloads the dataset and ~150 MB of weights)...")
    corpus = load_scifact()
    query_ids = select_query_ids(corpus, count=10)
    if not dataset.PINNED_QUERY_IDS:
        say(f"resolved query ids (pin these in src/dataset.py): {query_ids}")
    if not query_ids:
        raise SystemExit(
            f"no queries with a positive judgment in {len(corpus.qrels)} qrels rows — "
            "the qrels split or column names in src/dataset.py are probably wrong"
        )
    missing = [query_id for query_id in query_ids if query_id not in corpus.queries]
    if missing:
        raise SystemExit(
            f"query ids {missing} are not in the SciFact query set — "
            "check PINNED_QUERY_IDS in src/dataset.py"
        )

    # Built before the corpus embed so a missing cross-encoder fails in seconds
    # rather than after a ~40s embed the user then has to sit through again.
    reranker = Reranker()
    index, embed_seconds, cached = DenseIndex.build(
        corpus.doc_ids, [doc.indexed_text for doc in corpus.docs]
    )
    text_by_id = {doc.doc_id: doc.indexed_text for doc in corpus.docs}

    query_embed = Timings("query embed")
    vector_search = Timings("vector search")
    cross_encode = Timings("cross-encode")

    rows: list[report.QueryRow] = []
    dense_rankings: list[list[str]] = []
    rerank_rankings: list[list[str]] = []
    judgments: list[dict[str, int]] = []

    for query_id in query_ids:
        query = corpus.queries[query_id]
        qrels = corpus.qrels.get(query_id, {})

        candidates, embed_s, search_s = index.search(query, depth)
        query_embed.record(embed_s)
        vector_search.record(search_s)

        reranked, rerank_s = reranker.rerank(
            query, [(doc_id, text_by_id[doc_id]) for doc_id, _ in candidates], depth
        )
        cross_encode.record(rerank_s)

        dense_ranking = [doc_id for doc_id, _ in candidates]
        rerank_ranking = [doc_id for doc_id, _ in reranked]
        dense_rankings.append(dense_ranking)
        rerank_rankings.append(rerank_ranking)
        judgments.append(qrels)
        rows.append(
            report.QueryRow(
                query_id=query_id,
                text=query,
                gold_count=sum(1 for grade in qrels.values() if grade > 0),
                dense_rank=first_gold_rank(dense_ranking, qrels),
                rerank_rank=first_gold_rank(rerank_ranking, qrels),
            )
        )

    dense_summary = summarize(dense_rankings, judgments, k=top_n)
    rerank_summary = summarize(rerank_rankings, judgments, k=top_n)
    ceiling = sum(
        recall_at_k(ranking, qrels, depth) for ranking, qrels in zip(dense_rankings, judgments)
    ) / len(dense_rankings)

    dense_ms = query_embed.p50 + vector_search.p50
    rerank_ms = dense_ms + cross_encode.p50

    say("")
    for line in (
        report.render_header(
            len(corpus.docs), len(query_ids), BI_ENCODER, CROSS_ENCODER,
            top_n, depth, embed_seconds, cached,
        )
        + [""]
        + report.render_per_query(rows, depth)
        + [""]
        + report.render_summary(
            dense_summary, rerank_summary, ceiling, dense_ms, rerank_ms, top_n, depth
        )
        + [""]
        + report.render_latency(
            query_embed, vector_search, cross_encode, depth,
            dense_ms, rerank_ms, rerank_summary.hits - dense_summary.hits,
        )
    ):
        say(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="offline checks, no downloads")
    parser.add_argument("--top-k", type=int, default=10, help="documents each lane returns")
    parser.add_argument("--depth", type=int, default=50, help="candidates the reranker sees")
    args = parser.parse_args()

    if args.self_check:
        self_check()
    else:
        run(args.top_k, args.depth)


if __name__ == "__main__":
    sys.exit(main())
