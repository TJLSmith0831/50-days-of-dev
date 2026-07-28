from src.lanes import Timings
from src.metrics import LaneSummary
from src.report import (
    QueryRow,
    WIDTH,
    render_header,
    render_latency,
    render_per_query,
    render_summary,
    truncate,
)

LONG = "x" * 400
SUMMARY = LaneSummary(queries=10, ndcg=0.8123, recall=0.9, mrr=0.85, hits=8)


def test_truncate_never_exceeds_its_width():
    assert len(truncate(LONG, 48)) == 48
    assert truncate(LONG, 48).endswith("...")
    assert truncate("short", 48) == "short"


def test_truncate_flattens_newlines():
    assert "\n" not in truncate("two\nlines", 48)


def _worst_case_rows() -> list[QueryRow]:
    return [
        QueryRow(query_id="1", text=LONG, gold_count=999, dense_rank=50, rerank_rank=1),
        QueryRow(query_id="2", text=LONG, gold_count=1, dense_rank=None, rerank_rank=None),
        QueryRow(query_id="3", text="ok", gold_count=1, dense_rank=1, rerank_rank=7),
    ]


def test_no_rendered_line_shears_the_table():
    lines = (
        render_header(5183, 10, "BAAI/bge-small-en-v1.5", "Xenova/ms-marco-MiniLM-L-6-v2", 10, 50, 41.3, False)
        + render_per_query(_worst_case_rows(), depth=50)
        + render_summary(SUMMARY, SUMMARY, 0.9, 3.6, 204.1, top_k=10, depth=50)
        + render_latency(Timings("a"), Timings("b"), Timings("c"), 50, 3.6, 204.1, 2)
    )
    assert lines, "the report must render something"
    for line in lines:
        assert len(line) <= WIDTH, f"{len(line)} chars: {line!r}"


def test_delta_is_none_when_a_rank_is_missing():
    row = QueryRow(query_id="2", text="q", gold_count=1, dense_rank=None, rerank_rank=3)
    assert row.delta is None
    assert row.flag == " "


def test_flag_marks_promotion_to_top_one():
    assert QueryRow("1", "q", 1, dense_rank=7, rerank_rank=1).flag == "*"


def test_flag_does_not_celebrate_a_doc_that_was_already_first():
    assert QueryRow("1", "q", 1, dense_rank=1, rerank_rank=1).flag == " "


def test_flag_marks_a_regression():
    assert QueryRow("1", "q", 1, dense_rank=2, rerank_rank=9).flag == "!"


def test_delta_sign_reads_as_improvement_when_rank_drops():
    assert QueryRow("1", "q", 1, dense_rank=7, rerank_rank=1).delta == 6


def test_latency_row_survives_a_zero_baseline():
    lines = render_latency(Timings("a"), Timings("b"), Timings("c"), 50, 0.0, 0.0, 0)
    assert any("0x slower" in line for line in lines)
