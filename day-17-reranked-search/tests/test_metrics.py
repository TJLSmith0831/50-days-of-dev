import math

import pytest

from src.metrics import (
    first_gold_rank,
    hit_at_1,
    mrr_at_k,
    ndcg_at_k,
    summarize,
)

# One gold document, placed at a different rank in each fixture.
GOLD = {"d7": 1}
GOLD_FIRST = ["d7", "d1", "d2", "d3", "d4"]
GOLD_SECOND = ["d1", "d7", "d2", "d3", "d4"]
GOLD_FIFTH = ["d1", "d2", "d3", "d4", "d7"]
GOLD_ABSENT = ["d1", "d2", "d3", "d4", "d5"]

# Two gold documents, so recall has room to be partial.
TWO_GOLD = {"d7": 1, "d9": 1}
ONE_OF_TWO = ["d7", "d1", "d2", "d3", "d9"]


def test_ndcg_is_one_when_the_only_gold_doc_is_first():
    assert ndcg_at_k(GOLD_FIRST, GOLD, 10) == pytest.approx(1.0)


def test_ndcg_at_rank_two_is_the_log_discount():
    # DCG = 1/log2(3), IDCG = 1/log2(2) = 1.
    assert ndcg_at_k(GOLD_SECOND, GOLD, 10) == pytest.approx(1 / math.log2(3))
    assert ndcg_at_k(GOLD_SECOND, GOLD, 10) == pytest.approx(0.63093, abs=1e-5)


def test_ndcg_is_zero_when_gold_is_missing():
    assert ndcg_at_k(GOLD_ABSENT, GOLD, 10) == 0.0


def test_ndcg_ignores_gold_below_the_cutoff():
    assert ndcg_at_k(GOLD_FIFTH, GOLD, 3) == 0.0
    assert ndcg_at_k(GOLD_FIFTH, GOLD, 5) > 0.0


def test_ndcg_is_zero_when_the_query_has_no_judgments():
    # Guards the IDCG == 0 division.
    assert ndcg_at_k(GOLD_FIRST, {}, 10) == 0.0


def test_recall_counts_gold_inside_the_cutoff():
    from src.metrics import recall_at_k

    assert recall_at_k(ONE_OF_TWO, TWO_GOLD, 1) == pytest.approx(0.5)
    assert recall_at_k(ONE_OF_TWO, TWO_GOLD, 5) == pytest.approx(1.0)
    assert recall_at_k(GOLD_ABSENT, GOLD, 5) == 0.0


def test_recall_is_non_decreasing_in_k():
    from src.metrics import recall_at_k

    values = [recall_at_k(ONE_OF_TWO, TWO_GOLD, k) for k in range(1, 6)]
    assert values == sorted(values)


def test_mrr_uses_the_first_gold_hit_only():
    assert mrr_at_k(GOLD_FIRST, GOLD, 10) == pytest.approx(1.0)
    assert mrr_at_k(GOLD_SECOND, GOLD, 10) == pytest.approx(0.5)
    assert mrr_at_k(GOLD_FIFTH, GOLD, 10) == pytest.approx(0.2)
    assert mrr_at_k(GOLD_FIFTH, GOLD, 4) == 0.0
    assert mrr_at_k(ONE_OF_TWO, TWO_GOLD, 10) == pytest.approx(1.0)


def test_hit_at_1_reads_only_the_top_slot():
    assert hit_at_1(GOLD_FIRST, GOLD) == 1
    assert hit_at_1(GOLD_SECOND, GOLD) == 0
    assert hit_at_1([], GOLD) == 0


def test_first_gold_rank_is_one_based_and_none_when_absent():
    assert first_gold_rank(GOLD_FIRST, GOLD) == 1
    assert first_gold_rank(GOLD_SECOND, GOLD) == 2
    assert first_gold_rank(GOLD_FIFTH, GOLD) == 5
    assert first_gold_rank(GOLD_ABSENT, GOLD) is None


def test_summarize_averages_over_queries():
    rankings = [GOLD_FIRST, GOLD_SECOND]
    qrels = [GOLD, GOLD]
    summary = summarize(rankings, qrels, k=10)
    assert summary.hits == 1
    assert summary.queries == 2
    assert summary.mrr == pytest.approx(0.75)
    assert summary.ndcg == pytest.approx((1.0 + 1 / math.log2(3)) / 2)
    assert summary.recall == pytest.approx(1.0)
