# Day 18 — Workflow RAG — BRIEF.md

## What was built

A 3-step LlamaIndex Workflow (ingest → retrieve → synthesize) that answers questions about local markdown files. The REPL commands are `ingest <dir>` (builds and persists the index to `.workflow_index/`), `query <text>` (retrieves and synthesizes), and `exit`. Every query streams the intermediate events live: `IngestedEvent` (index loaded) and `RetrievedEvent` (top-k nodes with scores and previews) appear before the answer.

## Implementation facts

- `RAGWorkflow` inherits from `Workflow` and has three `@step` methods: `ingest`, `retrieve`, `synthesize`.
- Custom events: `IngestedEvent` (carries `VectorStoreIndex`), `RetrievedEvent` (carries `list[NodeWithScore]`).
- The `ingest` step branches on `StartEvent` fields: if `dirname` is present, it loads markdown files via `SimpleDirectoryReader`, builds the index, persists it, and returns `StopEvent`. If `query` is present, it loads the persisted index and returns `IngestedEvent`.
- LLM: Ollama `llama3.2` with `request_timeout=360.0` and `context_window=8000`.
- Embeddings: HuggingFace `BAAI/bge-small-en-v1.5`.
- Index persistence: `index.storage_context.persist(persist_dir=".workflow_index/")`.
- REPL uses `rich` for the console; Ollama is checked at startup via `urllib.request.urlopen("http://localhost:11434/api/version")`.

## Discovery during implementation

The installed `llama-index-workflows` version (2.22.2) only yields events on `handler.stream_events()` if steps explicitly call `ctx.write_event_to_stream(ev)`. Events returned by steps are dispatched to the next step but do not appear in the stream automatically. This was verified by inspecting the installed `WorkflowHandler.stream_events` source. The fix: both `ingest` (on the query path) and `retrieve` call `ctx.write_event_to_stream()` before returning their custom events. Logged as D10 in the decision log.

## Verification

- Ingest: `docs/` contains 3 markdown files; `ingest docs` reported "Ingested 3 documents (3 nodes), persisted to .workflow_index/". The directory was created and contained the expected index files.
- Query: `query what are the three stages of a RAG pipeline?` streamed `IngestedEvent` and `RetrievedEvent` (3 nodes with scores 0.667, 0.582, 0.540 and file previews), then returned the correct answer listing ingest/retrieve/synthesize.
- Error handling: `query <text>` without an index returned "No index at .workflow_index/ — run `ingest <dir>` first." `ingest /nonexistent-dir` returned "Not a directory: /nonexistent-dir." Simulating an unreachable Ollama port returned the expected error message.
- Linting: `ruff check` passed with no errors.
