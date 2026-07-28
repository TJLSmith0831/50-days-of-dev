"""Exercise the whole `run()` path with stubbed models.

The live run costs a dataset download and a ~40s corpus embed before it reaches
any of this wiring, so a crash there is expensive to discover. These stubs cost
nothing and touch no network.
"""

import main
from src.dataset import Corpus, Doc

DOCS = [Doc(doc_id=f"d{i}", title=f"title {i}", text=f"text {i}") for i in range(1, 21)]
CORPUS = Corpus(
    docs=DOCS,
    queries={"1": "first query", "3": "second query"},
    # d3 is gold for query 1; query 3's gold sits outside the candidate depth below.
    qrels={"1": {"d3": 1}, "3": {"d19": 1}},
)


class StubIndex:
    def __init__(self, doc_ids):
        self.doc_ids = list(doc_ids)

    @classmethod
    def build(cls, doc_ids, texts, *args, **kwargs):
        return cls(doc_ids), 0.5, False

    def search(self, query, k):
        return [(doc_id, 1.0 - i / 100) for i, doc_id in enumerate(self.doc_ids[:k])], 0.003, 0.0004


class StubReranker:
    model_name = "stub-cross-encoder"

    def rerank(self, query, candidates, k):
        # Reverse the candidate order so gold demonstrably moves.
        reordered = [(doc_id, float(i)) for i, (doc_id, _) in enumerate(reversed(candidates))]
        return reordered[:k], 0.2


def test_run_completes_and_prints_every_section(monkeypatch, capsys):
    monkeypatch.setattr(main, "load_scifact", lambda: CORPUS)
    monkeypatch.setattr(main, "DenseIndex", StubIndex)
    monkeypatch.setattr(main, "Reranker", StubReranker)

    main.run(top_n=3, depth=5)

    out = capsys.readouterr().out
    assert "PER-QUERY" in out
    assert "LANE SUMMARY" in out
    assert "ceiling" in out
    assert "LATENCY" in out
    for line in out.splitlines():
        assert len(line) <= main.report.WIDTH, f"{len(line)} chars: {line!r}"


def test_run_tolerates_a_query_whose_gold_is_outside_the_candidates(monkeypatch, capsys):
    # Query 3's gold is d19, which never enters a depth-5 candidate set.
    monkeypatch.setattr(main, "load_scifact", lambda: CORPUS)
    monkeypatch.setattr(main, "DenseIndex", StubIndex)
    monkeypatch.setattr(main, "Reranker", StubReranker)

    main.run(top_n=3, depth=5)

    out = capsys.readouterr().out
    assert " - " in out, "an unreachable gold document must render as '-', not crash"
