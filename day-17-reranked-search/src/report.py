"""Terminal report. The printed tables are this day's deliverable, so the
column widths are load-bearing: nothing may wrap past 100 characters.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.lanes import Timings
from src.metrics import LaneSummary

WIDTH = 100
QUERY_WIDTH = 48
RULE = "=" * WIDTH


def truncate(text: str, max_len: int) -> str:
    """Fit text to a column. An over-wide value would shear the table."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _rank(value: int | None) -> str:
    return "-" if value is None else str(value)


@dataclass(frozen=True)
class QueryRow:
    """One query's movement of its first gold document within the candidate set."""

    query_id: str
    text: str
    gold_count: int
    dense_rank: int | None
    rerank_rank: int | None

    @property
    def delta(self) -> int | None:
        if self.dense_rank is None or self.rerank_rank is None:
            return None
        return self.dense_rank - self.rerank_rank

    @property
    def flag(self) -> str:
        if self.rerank_rank == 1 and self.dense_rank not in (None, 1):
            return "*"
        if (self.delta or 0) < 0:
            return "!"
        return " "


def render_header(
    doc_count: int,
    query_count: int,
    bi_encoder: str,
    cross_encoder: str,
    top_k: int,
    depth: int,
    embed_seconds: float,
    cached: bool,
) -> list[str]:
    corpus_note = (
        "loaded from .cache/corpus.npz"
        if cached
        else f"embedded in {embed_seconds:.1f}s, cached to .cache/corpus.npz"
    )
    return [
        f"Reranked Search — {query_count} SciFact queries x 2 lanes   "
        "(local ONNX, no API key, no Ollama)",
        f"corpus      BEIR SciFact, {doc_count:,} abstracts   ({corpus_note})",
        f"bi-encoder  {bi_encoder}",
        f"reranker    {cross_encoder}",
        f"lanes       A: dense top-{top_k}   |   "
        f"B: dense top-{depth} -> cross-encode -> top-{top_k}",
    ]


def render_per_query(rows: list[QueryRow], depth: int) -> list[str]:
    lines = [
        RULE,
        f"PER-QUERY — rank of the first gold document within the {depth} candidates",
        "",
        f"  {'#':<3} {'Query':<{QUERY_WIDTH}} {'gold':>4} {'dense':>6} "
        f"{'rerank':>8} {'delta':>6}",
    ]
    for index, row in enumerate(rows, start=1):
        delta = "-" if row.delta is None else ("0" if row.delta == 0 else f"{row.delta:+d}")
        lines.append(
            f"  {index:<3} {truncate(row.text, QUERY_WIDTH):<{QUERY_WIDTH}} "
            f"{row.gold_count:>4} {_rank(row.dense_rank):>6} "
            f"{_rank(row.rerank_rank):>8} {delta:>6} {row.flag}"
        )
    lines.append(f"{'* moved into top-1     ! regressed':>{WIDTH}}")
    return lines


def render_summary(
    dense: LaneSummary,
    reranked: LaneSummary,
    ceiling_recall: float,
    dense_ms: float,
    rerank_ms: float,
    top_k: int,
    depth: int,
) -> list[str]:
    def row(label: str, summary: LaneSummary, ms: float) -> str:
        return (
            f"  {label:<26} {summary.ndcg:>8.3f} {summary.recall:>10.3f} "
            f"{summary.mrr:>8.3f} {f'{summary.hits}/{summary.queries}':>7} {ms:>14.1f}"
        )

    return [
        RULE,
        "LANE SUMMARY",
        "",
        f"  {'Lane':<26} {f'nDCG@{top_k}':>8} {f'Recall@{top_k}':>10} "
        f"{f'MRR@{top_k}':>8} {'Hit@1':>7} {'median ms/query':>14}",
        row("dense", dense, dense_ms),
        row(f"dense + rerank (top-{depth})", reranked, rerank_ms),
        f"  {f'ceiling (dense recall@{depth})':<26} {'-':>8} {ceiling_recall:>10.3f} "
        f"{'-':>8} {'-':>7}   lane B cannot exceed this",
    ]


def render_latency(
    query_embed: Timings,
    vector_search: Timings,
    cross_encode: Timings,
    depth: int,
    dense_total_ms: float,
    rerank_total_ms: float,
    hit_delta: int,
) -> list[str]:
    slowdown = rerank_total_ms / dense_total_ms if dense_total_ms else 0.0
    per_candidate = cross_encode.mean / depth if depth else 0.0

    def row(label: str, timings: Timings, suffix: str = "") -> str:
        return (
            f"  {label:<28} {timings.mean:>9.1f} {timings.p50:>9.1f} "
            f"{timings.p90:>9.1f}{suffix}"
        )

    return [
        RULE,
        "LATENCY (ms per query)",
        "",
        f"  {'Stage':<28} {'mean':>9} {'p50':>9} {'p90':>9}",
        row("query embed", query_embed),
        row("vector search", vector_search),
        row(f"cross-encode {depth} candidates", cross_encode, f"   = {per_candidate:.1f} each"),
        "  " + "-" * 58,
        f"  {'dense total':<28} {dense_total_ms:>9.1f}",
        f"  {'dense + rerank total':<28} {rerank_total_ms:>9.1f}"
        f"      {slowdown:.0f}x slower, {hit_delta:+d} hit@1",
    ]
