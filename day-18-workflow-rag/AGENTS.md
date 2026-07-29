# Day 18 — Workflow RAG — AGENTS.md
RAG over local markdown via a 3-step LlamaIndex Workflow (ingest → retrieve → synthesize), streaming the typed events between steps on every query.

## Stack
Python · LlamaIndex Workflows (`llama-index-workflows`, `llama-index-core`) · Ollama local (`llama3.2` LLM) · HuggingFace embeddings (`BAAI/bge-small-en-v1.5`) · `rich` (CLI)

## Commands (verified 2026-07-29)
`uv sync && uv run main.py` — requires `ollama serve` running with `llama3.2` pulled.

## Concept
Same RAG outcome as Day 1, built on the event-driven Workflow API instead of LangChain chains: `@step` functions communicate through typed events (`IngestedEvent`, `RetrievedEvent`), and the REPL streams those intermediate events per query so the pipeline's flow is visible, not just the answer.

## Gotchas
- One workflow class handles both entry points: `ingest` branches on `StartEvent.dirname` vs `StartEvent.query` (D9). Ingest returns `StopEvent` directly; query continues through retrieve → synthesize.
- Index persists to `.workflow_index/` (D7). Queries load it from disk if present, so `query` works across runs without re-ingesting — but the embedding model must be the same one that built it.
- First query downloads the `bge-small-en-v1.5` embedding model (~100 MB) from HuggingFace.
- `.workflow_index/` is generated state — do not commit.
