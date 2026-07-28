"""The two retrieval lanes. This is the only module that imports fastembed.

fastembed is imported *inside* the functions so `--self-check` stays instant and
cannot be broken by an onnxruntime import problem on a machine with no weights.
"""

from __future__ import annotations

import hashlib
import math
import os
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

BI_ENCODER = "BAAI/bge-small-en-v1.5"
CROSS_ENCODER = os.environ.get("DAY17_RERANKER", "Xenova/ms-marco-MiniLM-L-6-v2")
CACHE_PATH = Path(".cache/corpus.npz")


def normalize(matrix: np.ndarray) -> np.ndarray:
    """Unit-length rows, so cosine similarity is a plain dot product."""
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def top_k(
    vectors: np.ndarray,
    query_vector: np.ndarray,
    doc_ids: Sequence[str],
    k: int,
) -> list[tuple[str, float]]:
    """Cosine top-k over pre-normalized vectors, ties broken by document id.

    The explicit secondary key matters: equal scores would otherwise reorder
    run-to-run and make the report table jitter for no reason.
    """
    scores = vectors @ normalize(query_vector)
    ordered = sorted(zip(doc_ids, scores.tolist()), key=lambda pair: (-pair[1], pair[0]))
    return ordered[:k]


@dataclass
class Timings:
    """Per-query wall time, in milliseconds, for one pipeline stage."""

    name: str
    samples: list[float] = field(default_factory=list)

    def record(self, seconds: float) -> None:
        self.samples.append(seconds * 1000)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.samples) if self.samples else 0.0

    @property
    def p50(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def p90(self) -> float:
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        # Nearest-rank p90; with 10 samples this is the 9th, which is what we want.
        index = max(0, math.ceil(0.9 * len(ordered)) - 1)
        return ordered[index]


class DenseIndex:
    """Bi-encoder index over the corpus, with the embedding matrix cached on disk."""

    def __init__(self, doc_ids: Sequence[str], vectors: np.ndarray, model) -> None:
        self.doc_ids = list(doc_ids)
        self.vectors = vectors
        self._model = model

    @classmethod
    def build(
        cls,
        doc_ids: Sequence[str],
        texts: Sequence[str],
        cache_path: Path = CACHE_PATH,
    ) -> tuple["DenseIndex", float, bool]:
        """Return the index, the corpus-embed wall time in seconds, and a cache-hit flag."""
        from fastembed import TextEmbedding

        model = TextEmbedding(model_name=BI_ENCODER)
        cached = _load_cache(cache_path, doc_ids)
        if cached is not None:
            return cls(doc_ids, cached, model), 0.0, True

        started = time.perf_counter()
        vectors = normalize(np.asarray(list(model.embed(list(texts))), dtype=np.float32))
        elapsed = time.perf_counter() - started
        _save_cache(cache_path, doc_ids, vectors)
        return cls(doc_ids, vectors, model), elapsed, False

    def search(self, query: str, k: int) -> tuple[list[tuple[str, float]], float, float]:
        """Return top-k, the query-embed seconds, and the vector-search seconds."""
        started = time.perf_counter()
        query_vector = np.asarray(next(iter(self._model.embed([query]))), dtype=np.float32)
        embed_seconds = time.perf_counter() - started

        started = time.perf_counter()
        results = top_k(self.vectors, query_vector, self.doc_ids, k)
        search_seconds = time.perf_counter() - started
        return results, embed_seconds, search_seconds


class Reranker:
    """Cross-encoder that rescores (query, document) pairs the dense lane retrieved."""

    def __init__(self) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model_name = CROSS_ENCODER
        self._model = TextCrossEncoder(model_name=CROSS_ENCODER)

    def rerank(
        self, query: str, candidates: Sequence[tuple[str, str]], k: int
    ) -> tuple[list[tuple[str, float]], float]:
        """Rescore `(doc_id, text)` candidates, return the top k and the seconds spent."""
        doc_ids = [doc_id for doc_id, _ in candidates]
        texts = [text for _, text in candidates]
        started = time.perf_counter()
        scores = list(self._model.rerank(query, texts))
        elapsed = time.perf_counter() - started
        ordered = sorted(zip(doc_ids, scores), key=lambda pair: (-pair[1], pair[0]))
        return ordered[:k], elapsed


def _cache_signature(doc_ids: Sequence[str]) -> str:
    """Weights and corpus both invalidate the cache; identity of the ids is the guard.

    Every id is hashed, not just a sample. Row i of the cached matrix is only
    meaningful next to `doc_ids[i]`, so a corpus that kept its length but changed
    its order would otherwise reuse silently misaligned vectors — which produces
    plausible-looking nonsense rather than an error.
    """
    digest = hashlib.sha256("\n".join(doc_ids).encode()).hexdigest()[:16]
    return f"{BI_ENCODER}|{len(doc_ids)}|{digest}"


def _load_cache(cache_path: Path, doc_ids: Sequence[str]) -> np.ndarray | None:
    if not cache_path.exists():
        return None
    with np.load(cache_path, allow_pickle=False) as data:
        if str(data["signature"]) != _cache_signature(doc_ids):
            return None
        return data["vectors"]


def _save_cache(cache_path: Path, doc_ids: Sequence[str], vectors: np.ndarray) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, vectors=vectors, signature=_cache_signature(doc_ids))
