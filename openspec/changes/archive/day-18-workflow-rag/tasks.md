## 1. Setup

- [x] 1.1 Create `day-18-workflow-rag/` directory structure
- [x] 1.2 Create `pyproject.toml` with dependencies (llama-index-workflows, llama-index-llms-ollama, llama-index-embeddings-huggingface, llama-index-core, rich)
- [x] 1.3 Set `[tool.uv] package = false` in pyproject.toml
- [x] 1.4 Register day-18-workflow-rag in root `pyproject.toml` workspace members
- [x] 1.5 Create `AGENTS.md` from template with day-specific details

## 2. Sample Data

- [x] 2.1 Create `docs/` directory in day-18-workflow-rag
- [x] 2.2 Add 2-3 sample markdown files with test content

## 3. Workflow Implementation

- [x] 3.1 Define custom events: `IngestedEvent` (index field) and `RetrievedEvent` (nodes field)
- [x] 3.2 Create `RAGWorkflow` class inheriting from `Workflow`
- [x] 3.3 Implement `ingest` step: load markdown docs via SimpleDirectoryReader, build VectorStoreIndex, persist to `.workflow_index/`, return IngestedEvent
- [x] 3.4 Implement `retrieve` step: accept IngestedEvent, query index with retriever, return RetrievedEvent with nodes
- [x] 3.5 Implement `synthesize` step: accept RetrievedEvent, generate answer using LLM, return StopEvent with result
- [x] 3.6 Add branching logic in first step: check for `dirname` (ingest path) vs `query` (query text) in StartEvent
- [x] 3.7 Configure Ollama LLM with llama3.2, request_timeout=360.0, context_window=8000
- [x] 3.8 Configure HuggingFaceEmbedding with BAAI/bge-small-en-v1.5

## 4. REPL Implementation

- [x] 4.1 Create REPL loop with rich console
- [x] 4.2 Implement `ingest <dir>` command: run workflow with dirname, display success/failure
- [x] 4.3 Implement `query <text>` command: run workflow with query, stream intermediate events via handler.stream_events()
- [x] 4.4 Implement `exit` command: quit REPL
- [x] 4.5 Add Ollama server check at startup (verify localhost:11434 is reachable)
- [x] 4.6 Format streamed events with rich for clear display

## 5. Integration and Testing

- [x] 5.1 Create `main.py` entrypoint that initializes workflow and starts REPL
- [x] 5.2 Test ingest flow: load sample docs, verify index persists to `.workflow_index/`
- [x] 5.3 Test query flow: run query, verify events stream and display correctly
- [x] 5.4 Test error handling: query without ingest, invalid directory, Ollama not running
- [x] 5.5 Update root README.md with Day 18 status
