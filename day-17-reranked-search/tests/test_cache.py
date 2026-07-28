"""The corpus-embedding cache is the one place a silent wrong answer can hide.

Row i of the cached matrix only means anything beside `doc_ids[i]`. A stale or
misaligned cache does not raise — it returns confident nonsense — so the
signature guard gets its own tests.
"""

import numpy as np
import pytest

from src.lanes import _cache_signature, _load_cache, _save_cache, normalize

IDS = [f"d{i}" for i in range(50)]
VECTORS = normalize(np.random.RandomState(0).rand(50, 384).astype(np.float32))


@pytest.fixture
def cache_path(tmp_path):
    path = tmp_path / "corpus.npz"
    _save_cache(path, IDS, VECTORS)
    return path


def test_cache_round_trips_exactly(cache_path):
    loaded = _load_cache(cache_path, IDS)
    assert loaded is not None
    assert np.allclose(loaded, VECTORS)
    assert loaded.dtype == np.float32


def test_cold_cache_returns_none(tmp_path):
    assert _load_cache(tmp_path / "absent.npz", IDS) is None


def test_a_shorter_corpus_misses(cache_path):
    assert _load_cache(cache_path, IDS[:49]) is None


def test_a_reordered_corpus_misses(cache_path):
    # Same ids, same count, same first and last — only the middle moved.
    # A sampled signature would call this a hit and return misaligned vectors.
    reordered = IDS[:1] + list(reversed(IDS[1:-1])) + IDS[-1:]
    assert reordered != IDS
    assert (len(reordered), reordered[0], reordered[-1]) == (len(IDS), IDS[0], IDS[-1])
    assert _load_cache(cache_path, reordered) is None


def test_a_renamed_document_misses(cache_path):
    assert _load_cache(cache_path, ["renamed"] + IDS[1:]) is None


def test_signature_is_stable_across_calls():
    assert _cache_signature(IDS) == _cache_signature(list(IDS))
