"""Argument and fixture guards that must fail loudly rather than report nonsense."""

import pytest

import main
import src.dataset as dataset
from src.dataset import Corpus, Doc
from tests.test_run_smoke import StubIndex, StubReranker

DOCS = [Doc(doc_id=f"d{i}", title=f"t{i}", text=f"x{i}") for i in range(1, 21)]


@pytest.fixture
def stub(monkeypatch):
    corpus = Corpus(docs=DOCS, queries={"1": "q"}, qrels={"1": {"d3": 1}})
    monkeypatch.setattr(main, "load_scifact", lambda: corpus)
    monkeypatch.setattr(main, "DenseIndex", StubIndex)
    monkeypatch.setattr(main, "Reranker", StubReranker)
    return corpus


def test_pinned_ids_win_over_the_selection_rule(monkeypatch):
    """Once pinned, the query set is frozen — the rule must not re-resolve it.

    This is the whole point of pinning: a corpus whose qrels shift must not
    quietly change which 10 queries the experiment reports on.
    """
    monkeypatch.setattr(dataset, "PINNED_QUERY_IDS", ("7", "2"))
    corpus = Corpus(docs=DOCS, queries={"1": "q"}, qrels={"1": {"d3": 1}})
    assert dataset.select_query_ids(corpus, count=10) == ["7", "2"]


def test_top_k_above_depth_is_rejected(stub):
    # Otherwise the report claims a top-20 cut over a 5-candidate set and the
    # two lanes stop being comparable.
    with pytest.raises(SystemExit, match="exceeds --depth"):
        main.run(top_n=20, depth=5)


def test_top_k_equal_to_depth_is_allowed(stub, capsys):
    main.run(top_n=5, depth=5)
    assert "LANE SUMMARY" in capsys.readouterr().out


def test_no_positive_judgments_explains_itself(monkeypatch):
    """The likeliest first-run failure: a wrong qrels split parses to all-zero scores.

    Left unguarded this surfaced as a bare ZeroDivisionError from the ceiling
    calculation, which says nothing about the actual cause.
    """
    corpus = Corpus(docs=DOCS, queries={"1": "q"}, qrels={"1": {"d3": 0}})
    monkeypatch.setattr(main, "load_scifact", lambda: corpus)
    monkeypatch.setattr(main, "DenseIndex", StubIndex)
    monkeypatch.setattr(main, "Reranker", StubReranker)

    with pytest.raises(SystemExit, match="qrels"):
        main.run(top_n=3, depth=5)


def test_a_pinned_id_outside_the_query_set_is_named(monkeypatch, capsys):
    corpus = Corpus(docs=DOCS, queries={"1": "q"}, qrels={"1": {"d3": 1}, "999": {"d1": 1}})
    monkeypatch.setattr(main, "load_scifact", lambda: corpus)
    monkeypatch.setattr(main, "DenseIndex", StubIndex)
    monkeypatch.setattr(main, "Reranker", StubReranker)
    monkeypatch.setattr(dataset, "PINNED_QUERY_IDS", ("999", "1"))

    with pytest.raises(SystemExit, match="999"):
        main.run(top_n=3, depth=5)


def test_the_reranker_is_built_before_the_corpus_embed(monkeypatch, capsys):
    """A missing cross-encoder should fail in seconds, not after a ~40s embed."""
    order: list[str] = []

    class TracingIndex(StubIndex):
        @classmethod
        def build(cls, doc_ids, texts, *args, **kwargs):
            order.append("embed")
            return super().build(doc_ids, texts)

    class ExplodingReranker:
        def __init__(self):
            order.append("reranker")
            raise RuntimeError("no cross-encoder weights")

    corpus = Corpus(docs=DOCS, queries={"1": "q"}, qrels={"1": {"d3": 1}})
    monkeypatch.setattr(main, "load_scifact", lambda: corpus)
    monkeypatch.setattr(main, "DenseIndex", TracingIndex)
    monkeypatch.setattr(main, "Reranker", ExplodingReranker)

    with pytest.raises(RuntimeError, match="no cross-encoder"):
        main.run(top_n=3, depth=5)
    assert order == ["reranker"], "the embed must not run before the reranker loads"
