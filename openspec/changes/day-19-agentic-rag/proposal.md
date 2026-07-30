## Why

Day 19 of the 50-days-of-dev challenge focuses on agentic RAG — adding an actual agent decision point (whether and how to rewrite a query) on top of the plain retrieval pipelines built in Days 1 and 18. The goal is to measure whether a rewrite step improves answer quality on vague queries, using an LLM judge for scoring.

## What Changes

- Create `day-19-agentic-rag/` directory with a complete agentic RAG pipeline implementation, extending Day 18's LlamaIndex Workflow pattern
- Implement a branching workflow: `classify` (is the query already specific?) → if clear, `retrieve`/`synthesize` once and `judge` the single answer; if vague, `rewrite` → `retrieve`/`synthesize` on both the raw and rewritten queries → `judge` scores each independently
- Define new events: `ClassifiedEvent` (is_vague flag), `RewrittenEvent` (rewritten query text), `AnsweredEvent` (path, answer, retrieved nodes)
- Add an LLM-as-judge step that scores each answer 1-5 against the original question
- Build a REPL CLI with commands: `ingest <dir>`, `query <text>`, `exit`, matching Days 1/18
- Each query prints a rich Panel with the rewritten query (if any), both answers, and judge scores, plus a running summary Table (raw-avg vs rewritten-avg vs skipped-count) on exit
- Add a new markdown corpus (`docs/`) covering 5 overlapping AI-engineering topics (caching, agent memory, evaluation, retrieval, deployment) chosen to create real ambiguity for vague queries
- Reuse Day 18's local Ollama `llama3.2` LLM and HuggingFace `BAAI/bge-small-en-v1.5` embeddings for all roles (classify, rewrite, synthesize, judge)
- Persist the vector index to `.agentic_rag_index/` for reuse across runs

## Capabilities

### New Capabilities
None — this is a standalone day implementation for the 50-days-of-dev challenge, not a cross-cutting capability.

### Modified Capabilities
None — no existing specs are being modified.

## Impact

- New directory: `day-19-agentic-rag/` with Python implementation
- Dependencies: same as Day 18 — `llama-index-workflows`, `llama-index-llms-ollama`, `llama-index-embeddings-huggingface`, `llama-index-core`, `rich`
- Requires: Ollama running locally with `llama3.2` pulled
- Root `pyproject.toml`: register `day-19-agentic-rag` as a workspace member
- Sample data: 5 new markdown files in `day-19-agentic-rag/docs/`

## Non-Goals

- Reranking (Day 17's territory)
- A formal eval harness or golden datasets (Day 20/27's territory)
- Production concerns — rate limiting, auth, deployment
