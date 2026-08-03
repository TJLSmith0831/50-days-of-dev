## Context

Day 18 is a standalone implementation in the 50-days-of-dev challenge, focused on learning LlamaIndex Workflows — an event-driven orchestration framework for multi-step agentic AI applications. The day builds a RAG pipeline to demonstrate explicit control over flow compared to chain-based approaches (Day 1 used LangChain). The implementation is self-contained in `day-18-workflow-rag/` with its own dependencies and sample data.

## Goals / Non-Goals

**Goals:**
- Implement a 3-step LlamaIndex Workflow (ingest → retrieve → synthesize) that demonstrates the event-driven step pattern
- Define custom events (`IngestedEvent`, `RetrievedEvent`) to show typed event flow between steps
- Build a REPL CLI with rich formatting that streams and displays intermediate workflow events
- Use local models (Ollama llama3.2 + HuggingFace embeddings) following the repo's local-first philosophy
- Persist the vector index for reuse across runs

**Non-Goals:**
- Query rewriting or agentic RAG (that's Day 19)
- Reranking (that's Day 17)
- Complex branching or multi-agent orchestration
- Production deployment or API endpoints

## Decisions

**Single workflow class with branching logic** (D9)
- The workflow handles both ingest and query operations through the same step graph, branching based on `StartEvent` fields (`dirname` for ingest, `query` for query)
- **Alternative considered**: Separate `IngestWorkflow` and `QueryWorkflow` classes
- **Rationale**: Matches LlamaIndex docs pattern, demonstrates how workflows handle multiple entry points, keeps code cohesive

**Custom events for inter-step communication** (D8)
- `IngestedEvent` carries the built index from ingest to retrieve step
- `RetrievedEvent` carries retrieved nodes from retrieve to synthesize step
- **Alternative considered**: Using only `Context.store` for all data passing
- **Rationale**: Typed events demonstrate the core Workflow API pattern; `Context.store` would miss the teaching point

**Local Ollama + HuggingFace embeddings** (D4)
- Ollama `llama3.2` for LLM generation, HuggingFace `BAAI/bge-small-en-v1.5` for embeddings
- **Alternative considered**: Ollama for both LLM and embeddings
- **Rationale**: LlamaIndex docs show HuggingFaceEmbedding as the standard local pattern; OllamaEmbedding is less commonly used in examples

**Markdown data source** (D3)
- Ingest markdown files via `SimpleDirectoryReader` instead of PDFs
- **Alternative considered**: PDF/docx like Day 1
- **Rationale**: Avoids PDF parsing quirks, keeps focus on Workflow API, markdown is easier to inspect/debug

**Persisted index** (D7)
- Index persists to `.workflow_index/` using `index.storage_context.persist()`
- **Alternative considered**: In-memory only
- **Rationale**: Matches Day 1 pattern, practical for real usage, allows reusing without re-ingesting

## Risks / Trade-offs

**[Risk] Ollama server not running** → Mitigation: Add a check at startup that verifies Ollama is accessible on localhost:11434 before initializing the workflow, with a clear error message telling the user to run `ollama serve`

**[Risk] Model download latency on first run** → Mitigation: Document that `ollama pull llama3.2` should be run beforehand; the LLM initialization uses `request_timeout=360.0` per LlamaIndex docs recommendations

**[Risk] HuggingFace model download on first run** → Mitigation: The embedding model downloads on first use; this is acceptable for a development-focused day, but we should document the expected download size

**[Trade-off] Single workflow class vs separate classes** → The single class with branching is simpler for this scope but would not scale well if ingest and query needed significantly different logic. For this day's teaching goal, the trade-off is acceptable

**[Trade-off] Markdown-only data source** → Limits the day to text-based documents, but this keeps the focus on Workflows rather than file parsing. PDF support could be added later if needed

## Migration Plan

No migration required — this is a new standalone day implementation. The workflow:

1. Create `day-18-workflow-rag/` directory structure
2. Add `pyproject.toml` with dependencies
3. Implement the workflow class with 3 steps
4. Implement the REPL with rich
5. Add sample markdown files to `docs/`
6. Register the day in root `pyproject.toml` workspace
7. Test ingest and query flows

## Open Questions

None — all technical decisions are resolved in the decision log.
