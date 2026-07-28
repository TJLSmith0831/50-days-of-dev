"""BEIR SciFact loading and the fixed 10-query selection rule.

SciFact ships 5,183 scientific abstracts, 300 test queries, and real relevance
judgments. The qrels label *documents*, so documents are the retrieval unit and
nothing here chunks them — see AGENTS.md.

Requires network on first call; `datasets` caches under HF_HOME afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass

DATASET = "BeIR/scifact"
QRELS_DATASET = "BeIR/scifact-qrels"
QRELS_SPLIT = "test"

# Pinned after the first live run so the experiment stops depending on the
# selection rule below. Empty means "resolve from qrels and print the result".
PINNED_QUERY_IDS: tuple[str, ...] = ()


@dataclass(frozen=True)
class Doc:
    doc_id: str
    title: str
    text: str

    @property
    def indexed_text(self) -> str:
        """What actually gets embedded. Title carries real signal in SciFact."""
        return f"{self.title}\n{self.text}".strip()


@dataclass(frozen=True)
class Corpus:
    docs: list[Doc]
    queries: dict[str, str]
    qrels: dict[str, dict[str, int]]

    @property
    def doc_ids(self) -> list[str]:
        return [doc.doc_id for doc in self.docs]


def _pick(row: dict, *names: str) -> object:
    """Read the first column that exists. BEIR configs disagree on `_id` vs `id`."""
    for name in names:
        if name in row:
            return row[name]
    raise KeyError(f"none of {names} in columns {sorted(row)}")


def load_scifact() -> Corpus:
    """Download (or read from cache) the SciFact corpus, queries, and test qrels."""
    from datasets import load_dataset

    corpus_rows = load_dataset(DATASET, "corpus")["corpus"]
    query_rows = load_dataset(DATASET, "queries")["queries"]
    qrel_rows = load_dataset(QRELS_DATASET)[QRELS_SPLIT]

    docs = [
        Doc(
            doc_id=str(_pick(row, "_id", "id")),
            title=str(row.get("title") or ""),
            text=str(row.get("text") or ""),
        )
        for row in corpus_rows
    ]
    queries = {str(_pick(row, "_id", "id")): str(row["text"]) for row in query_rows}

    qrels: dict[str, dict[str, int]] = {}
    for row in qrel_rows:
        query_id = str(_pick(row, "query-id", "query_id"))
        doc_id = str(_pick(row, "corpus-id", "corpus_id"))
        qrels.setdefault(query_id, {})[doc_id] = int(row["score"])

    return Corpus(docs=docs, queries=queries, qrels=qrels)


def _sort_key(query_id: str) -> tuple[int, str]:
    """Numeric where possible so `9` sorts before `10`, lexical as a fallback."""
    return (int(query_id), "") if query_id.isdigit() else (10**9, query_id)


def select_query_ids(corpus: Corpus, count: int = 10) -> list[str]:
    """The fixed selection rule: first `count` query ids by id order, positives only.

    Deliberately blind to retrieval difficulty — the set is chosen before any
    scores are seen so it cannot be tuned toward a flattering delta.
    """
    if PINNED_QUERY_IDS:
        return list(PINNED_QUERY_IDS)
    eligible = [
        query_id
        for query_id, judgments in corpus.qrels.items()
        if query_id in corpus.queries and any(g > 0 for g in judgments.values())
    ]
    return sorted(eligible, key=_sort_key)[:count]
