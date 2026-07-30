## 1. Setup

- [x] 1.1 Create `day-19-agentic-rag/` directory structure
- [x] 1.2 Create `pyproject.toml` with dependencies (llama-index-workflows, llama-index-llms-ollama, llama-index-embeddings-huggingface, llama-index-core, rich)
- [x] 1.3 Set `[tool.uv] package = false` in pyproject.toml
- [x] 1.4 Register day-19-agentic-rag in root `pyproject.toml` workspace members
- [x] 1.5 Create `AGENTS.md` from template with day-specific details

## 2. Sample Data

- [x] 2.1 Create `docs/` directory in day-19-agentic-rag
- [x] 2.2 Write `caching.md` (semantic vs prompt caching)
- [x] 2.3 Write `agent-memory.md` (short vs long-term)
- [x] 2.4 Write `evaluation.md` (LLM-as-judge vs golden sets)
- [x] 2.5 Write `retrieval.md` (dense vs reranking)
- [x] 2.6 Write `deployment.md` (local vs hosted)

## 3. Workflow Implementation — Branching Logic (riskiest, do first)

- [x] 3.1 Define custom events: `ClassifiedEvent{is_vague: bool}`, `RewrittenEvent{rewritten: str}`, `AnsweredEvent{path: str, answer: str, nodes: list[NodeWithScore]}`
- [x] 3.2 Create `AgenticRAGWorkflow` class inheriting from `Workflow`, following Day 18's `RAGWorkflow` shape
- [x] 3.3 Implement `ingest` step: load markdown docs via SimpleDirectoryReader, build VectorStoreIndex, persist to `.agentic_rag_index/`, return StopEvent (reuse Day 18 pattern)
- [x] 3.4 Implement `classify` step: query path loads persisted index, prompts LLM to judge if query is vague, returns `ClassifiedEvent`
- [x] 3.5 Implement `rewrite` step: on `ClassifiedEvent{is_vague=True}`, prompts LLM to rewrite the query, returns `RewrittenEvent`
- [x] 3.6 Implement `retrieve`+`synthesize` for a single path (raw or rewritten), parameterized by which query string to use, returning `AnsweredEvent{path, answer, nodes}`
- [x] 3.7 Wire branching: `ClassifiedEvent{is_vague=False}` → one `retrieve`/`synthesize` call (path="raw") → skip rewrite; `ClassifiedEvent{is_vague=True}` → `rewrite` → two `retrieve`/`synthesize` calls (path="raw" and path="rewritten")
- [x] 3.8 Implement `judge` step: collect one or two `AnsweredEvent`s via `ctx.collect_events`, prompt LLM to score each answer 1-5 against the original question, return `StopEvent{result: {...}}`
- [x] 3.9 Configure Ollama LLM with llama3.2, request_timeout=360.0, context_window=8000 (reuse Day 18 config)
- [x] 3.10 Configure HuggingFaceEmbedding with BAAI/bge-small-en-v1.5, similarity_top_k=3 for both retrievers

## 4. REPL Implementation

- [x] 4.1 Create REPL loop with rich console (reuse Day 18's structure)
- [x] 4.2 Implement `ingest <dir>` command: run workflow with dirname, display success/failure
- [x] 4.3 Implement `query <text>` command: run workflow with query, stream ClassifiedEvent/RewrittenEvent/AnsweredEvent as they flow
- [x] 4.4 Render per-query rich Panel: rewritten query (if any), both answers, both judge scores (or single answer+score if skipped)
- [x] 4.5 Track running session tally: raw-avg score, rewritten-avg score, skipped-count
- [x] 4.6 Print summary Table on `exit` (mirrors Day 1's per-question latency table)
- [x] 4.7 Add Ollama server check at startup (verify localhost:11434 is reachable, reuse Day 18 pattern)

## 5. Integration and Testing

- [x] 5.1 Create `main.py` entrypoint that initializes workflow and starts REPL
- [x] 5.2 Test ingest flow: load 5 sample docs, verify index persists to `.agentic_rag_index/`
- [x] 5.3 Test classify-skip flow: run a specific/clear query, verify single path (no rewrite) and single score
- [x] 5.4 Test classify-vague flow: run a deliberately vague query, verify rewrite fires and both raw/rewritten answers + scores appear
- [x] 5.5 Test judge scoring: verify scores are 1-5 integers and independent of path
- [x] 5.6 Test error handling: query without ingest, invalid directory, Ollama not running
- [x] 5.7 Update root README.md with Day 19 status
