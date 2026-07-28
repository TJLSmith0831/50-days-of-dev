"""Retrieval metrics. Pure functions over a ranking and its relevance judgments.

A *ranking* is a list of document ids, best first (rank 1 is index 0).
*qrels* maps document id -> relevance grade; any id absent from it scores 0.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


def _dcg(gains: Iterable[float]) -> float:
    return sum(gain / math.log2(rank + 2) for rank, gain in enumerate(gains))


def ndcg_at_k(ranking: Sequence[str], qrels: Mapping[str, int], k: int) -> float:
    """Normalized discounted cumulative gain over the top k."""
    ideal = sorted((g for g in qrels.values() if g > 0), reverse=True)[:k]
    idcg = _dcg(ideal)
    if idcg == 0:
        # No positive judgment exists, so there is nothing to normalize against.
        return 0.0
    return _dcg(qrels.get(doc_id, 0) for doc_id in ranking[:k]) / idcg


def recall_at_k(ranking: Sequence[str], qrels: Mapping[str, int], k: int) -> float:
    """Fraction of the query's gold documents that appear in the top k."""
    gold = {doc_id for doc_id, grade in qrels.items() if grade > 0}
    if not gold:
        return 0.0
    return len(gold.intersection(ranking[:k])) / len(gold)


def first_gold_rank(ranking: Sequence[str], qrels: Mapping[str, int]) -> int | None:
    """1-based rank of the first gold document, or None if the ranking misses it."""
    for index, doc_id in enumerate(ranking):
        if qrels.get(doc_id, 0) > 0:
            return index + 1
    return None


def mrr_at_k(ranking: Sequence[str], qrels: Mapping[str, int], k: int) -> float:
    """Reciprocal rank of the first gold document, 0 if it falls outside the top k."""
    rank = first_gold_rank(ranking[:k], qrels)
    return 0.0 if rank is None else 1 / rank


def hit_at_1(ranking: Sequence[str], qrels: Mapping[str, int]) -> int:
    """1 if the top slot is gold. Counted rather than averaged so it prints as `n/10`."""
    return 1 if ranking and qrels.get(ranking[0], 0) > 0 else 0


@dataclass(frozen=True)
class LaneSummary:
    """Aggregate scores for one lane over the whole query set."""

    queries: int
    ndcg: float
    recall: float
    mrr: float
    hits: int

    @property
    def hit_rate(self) -> float:
        return self.hits / self.queries if self.queries else 0.0


def summarize(
    rankings: Sequence[Sequence[str]],
    qrels: Sequence[Mapping[str, int]],
    k: int,
) -> LaneSummary:
    """Average the per-query metrics. `rankings` and `qrels` are index-aligned."""
    assert len(rankings) == len(qrels), "each ranking needs its own judgments"
    count = len(rankings)
    if count == 0:
        return LaneSummary(queries=0, ndcg=0.0, recall=0.0, mrr=0.0, hits=0)
    return LaneSummary(
        queries=count,
        ndcg=sum(ndcg_at_k(r, q, k) for r, q in zip(rankings, qrels)) / count,
        recall=sum(recall_at_k(r, q, k) for r, q in zip(rankings, qrels)) / count,
        mrr=sum(mrr_at_k(r, q, k) for r, q in zip(rankings, qrels)) / count,
        hits=sum(hit_at_1(r, q) for r, q in zip(rankings, qrels)),
    )
