# Day 17 — Reranked Search

## Goal

Establish with numbers whether a cross-encoder reranking stage earns its latency on top of plain dense retrieval: 10 BEIR SciFact queries × 2 lanes → nDCG@10 / Recall@10 / MRR@10 / Hit@1, the per-query movement of the gold document, staged ms-per-query, and a ceiling row bounding what reranking could ever have achieved.

## Architecture

```
BEIR SciFact (5,183 abstracts, 300 test queries, real qrels)
        |
        v
  src/dataset.py     load corpus/queries/qrels; fixed 10-query selection rule
        |
        v
  src/lanes.py       lane A: bge-small -> cosine top-10
                     lane B: bge-small -> top-50 -> ms-marco cross-encoder -> top-10
        |                                (the only module importing fastembed)
        v
  src/metrics.py     nDCG / recall / MRR / hit@1 / first-gold-rank  (pure)
        |
        v
  src/report.py      per-query table, lane summary + ceiling row, latency table
```

## Tech stack

Python 3.13 · fastembed (local ONNX, no API key, no Ollama) · `BAAI/bge-small-en-v1.5` · `Xenova/ms-marco-MiniLM-L-6-v2` · HuggingFace `datasets` · numpy · pytest

## Domain contract

- **ranking** — a list of document ids, best first; rank 1 is index 0.
- **qrels** — `{doc_id: grade}` from BEIR's published judgments; any id absent scores 0. A document is *gold* iff its grade is > 0.
- **depth** — how many candidates lane A retrieves and the reranker sees (50).
- **k** — how many documents each lane returns (10). Both lanes return k, so the reranker is the only variable between them.
- **ceiling** — lane A's `recall@depth`. A reranker reorders the candidate set; it cannot add to it, so lane B's `recall@k` can never exceed this.

## Repository context

- `pyproject.toml` sets `[tool.uv] package = false` — without it `uv run` tries to build a wheel and fails.
- No root `pyproject.toml` edit needed: `members = ["day-*"]` picks up any new Python day. `exclude` is only for non-Python days.
- No `.env`, no secrets, no API key — this day has none by construction.
- The tracker row flips to `done` only after a live run, with observed numbers replacing the placeholder tagline.

## Tasks

1. **Scaffold** — `pyproject.toml`, `.gitignore` (`.cache/`), `src/`, `tests/`. **Done.**
2. **`src/metrics.py` + tests**, TDD, pure. **Done** — 11 tests.
3. **`src/dataset.py`** — SciFact loading, `select_query_ids`, `PINNED_QUERY_IDS`. **Written; the loader is unverified against the live HF schema** (see Open questions).
4. **`src/lanes.py` + tests** — cached corpus embeddings, cosine top-k with id tie-break, cross-encoder rescoring, staged timings. **Done** — 7 tests cover the pure ranking math on synthetic vectors.
5. **`src/report.py` + tests** — three tables, ceiling row, 100-column discipline. **Done** — 9 tests.
6. **`main.py`** — argparse, lane orchestration, `self_check()`. **Done.**
7. **Live run** — `uv run main.py`, capture the report. **Blocked** (see below).
8. **Docs** — `README.md`, `AGENTS.md`, this plan. **Done except the Result section**, which stays empty until task 7.
9. **`BRIEF.md`** — demo/LinkedIn handoff. **Deferred**: it is built around the measured numbers and the captured terminal output.
10. **Tracker** — `README.md` line 40 `planned` → `done` with a number-dense outcome cell. **Blocked on task 7.**

## Verification

```bash
cd day-17-reranked-search && uv run main.py --self-check   # offline; no downloads
cd day-17-reranked-search && uv run --group dev pytest -q  # 27 tests
cd day-17-reranked-search && uv run main.py                # live report [needs huggingface.co]
uv sync --all-packages                                     # from repo root
```

## Open questions for the live run

- **The SciFact schema is assumed, not verified.** `src/dataset.py` expects `BeIR/scifact` configs `corpus` (`_id`/`title`/`text`) and `queries` (`_id`/`text`), plus `BeIR/scifact-qrels` split `test` (`query-id`/`corpus-id`/`score`). `_pick()` tolerates the `_id`/`id` and `query-id`/`query_id` variants; anything further will need a fix at first run.
- **Pin the query ids.** The first run prints the resolved ids; paste them into `PINNED_QUERY_IDS` so later runs stop depending on the selection rule.
- **Reranking may show no gain.** SciFact averages ~1.1 gold documents per query and `bge-small` is already strong on it. That is a publishable result and on-brand for this repo; the ceiling finding gives the day a headline either way. If probing first, try `--depth 100`, then `DAY17_RERANKER=jinaai/jina-reranker-v1-turbo-en`. Do not re-pick the 10 queries.
- **10 queries is a tiny sample** — report it as an illustration, not a benchmark claim.

## Blocker on task 7

`huggingface.co` and `cdn-lfs.huggingface.co` are unreachable from the remote build container (`CONNECT tunnel failed, response 403`). fastembed's GCS mirror serves the bi-encoder (`fast-bge-small-en-v1.5.tar.gz` → 206) but carries no cross-encoder tarball, and the SciFact data is HF-only, so there is no HF-free path. PyPI and GitHub raw are reachable, so dependency resolution, tests, and `--self-check` all pass in the container. Tasks 7, 9, and 10 need a machine with HuggingFace access.
