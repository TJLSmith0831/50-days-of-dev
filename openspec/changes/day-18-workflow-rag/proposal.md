## Why

Day 18 of the 50-days-of-dev challenge focuses on LlamaIndex Workflows, an event-driven orchestration framework for building multi-step agentic AI applications. This day teaches the Workflow API (@step decorators, Event types, Context state) by building a RAG pipeline that demonstrates explicit control over flow compared to chain-based approaches like LangChain (Day 1).

## What Changes

- Create `day-18-workflow-rag/` directory with a complete RAG pipeline implementation
- Implement a 3-step LlamaIndex Workflow: ingest (load docs, build index) → retrieve (query index, get nodes) → synthesize (generate answer from nodes)
- Define two custom events: `IngestedEvent` (index built) and `RetrievedEvent` (nodes retrieved) to demonstrate typed event flow between steps
- Build a REPL CLI with commands: `ingest <dir>`, `query <text>`, `exit` using `rich` for UI
- Ingest markdown files from a local directory via `SimpleDirectoryReader`
- Use local Ollama `llama3.2` for LLM generation and HuggingFace `BAAI/bge-small-en-v1.5` for embeddings
- Persist the vector index to disk (`.workflow_index/`) for reuse across runs
- Stream and display intermediate workflow events per query to demonstrate the event-driven nature

## Capabilities

### New Capabilities
None — this is a standalone day implementation for the 50-days-of-dev challenge, not a cross-cutting capability.

### Modified Capabilities
None — no existing specs are being modified.

## Impact

- New directory: `day-18-workflow-rag/` with Python implementation
- Dependencies: `llama-index-workflows`, `llama-index-llms-ollama`, `llama-index-embeddings-huggingface`, `llama-index-core`, `rich`
- Requires: Ollama running locally with `llama3.2` model pulled
- Root `pyproject.toml`: register `day-18-workflow-rag` as a workspace member
- Sample data: include 2-3 markdown files in `day-18-workflow-rag/docs/` for testing
