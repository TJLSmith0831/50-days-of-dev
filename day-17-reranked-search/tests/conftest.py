"""Stub corpora carry their own query ids, so the real pin must never reach them.

`PINNED_QUERY_IDS` is production data: once filled, `select_query_ids` returns it
and ignores whatever corpus it was handed. Without this reset every stub test
dies on `query ids [...] are not in the SciFact query set`, which says nothing
about the test and everything about a global it never opted into.
"""

import pytest

from src import dataset


@pytest.fixture(autouse=True)
def unpinned_query_ids(monkeypatch):
    monkeypatch.setattr(dataset, "PINNED_QUERY_IDS", ())
