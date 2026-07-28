import numpy as np

from src.lanes import Timings, normalize, top_k

# Three orthogonal unit vectors plus a duplicate of the first, so ties are forced.
VECTORS = normalize(
    np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
        ],
        dtype=np.float32,
    )
)
DOC_IDS = ["d2", "d3", "d4", "d1"]


def test_top_k_orders_by_cosine_similarity():
    results = top_k(VECTORS, np.array([0.0, 1.0, 0.0], dtype=np.float32), DOC_IDS, 1)
    assert [doc_id for doc_id, _ in results] == ["d3"]


def test_top_k_breaks_ties_by_doc_id_not_matrix_order():
    # d2 and d1 both score 1.0; d1 must win on id despite sitting last in the matrix.
    results = top_k(VECTORS, np.array([1.0, 0.0, 0.0], dtype=np.float32), DOC_IDS, 2)
    assert [doc_id for doc_id, _ in results] == ["d1", "d2"]


def test_top_k_respects_the_cutoff():
    assert len(top_k(VECTORS, np.array([1.0, 1.0, 1.0], dtype=np.float32), DOC_IDS, 3)) == 3


def test_top_k_handles_an_unnormalized_query_vector():
    scaled = top_k(VECTORS, np.array([0.0, 7.0, 0.0], dtype=np.float32), DOC_IDS, 1)
    assert scaled[0][0] == "d3"
    assert scaled[0][1] == 1.0


def test_normalize_leaves_a_zero_row_finite():
    result = normalize(np.zeros((1, 3), dtype=np.float32))
    assert np.isfinite(result).all()


def test_timings_p90_uses_nearest_rank():
    timings = Timings("stage")
    for value in range(1, 11):
        timings.record(value / 1000)
    assert timings.p50 == 5.5
    assert timings.p90 == 9.0
    assert timings.mean == 5.5


def test_empty_timings_do_not_divide_by_zero():
    timings = Timings("stage")
    assert (timings.mean, timings.p50, timings.p90) == (0.0, 0.0, 0.0)
