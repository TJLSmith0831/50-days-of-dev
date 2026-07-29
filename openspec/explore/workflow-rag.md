# Day 18 — Workflow RAG — Exploration Notes

Topic: LlamaIndex Workflows — one ingestion-to-answer pipeline

## D1: What makes this different from Day 1's LangChain RAG?
- **Decision**: Day 1 uses LangChain's chain abstraction; Day 18 uses LlamaIndex Workflows' event-driven step pattern with explicit typed events between stages
- **Why**: The day is about learning the Workflow API (@step decorators, Event types, Context state), not about RAG itself. The point is to show how Workflows gives you explicit control over flow compared to chains
- **Source**: user (README topic line)

## D2: What's the concrete, measurable outcome?
- **Decision**: Streaming intermediate events captured and displayed per query — showing the workflow's event-driven nature with X events flowing through the pipeline
- **Why**: The point of Workflows is the event-driven step pattern, so the demo should show events flowing between steps (ingest → retrieve → synthesize). Latency is a side effect, not the teaching point
- **Source**: recommended-accepted

## D3: What data source should we use for ingestion?
- **Decision**: Markdown files from a local directory via `SimpleDirectoryReader`
- **Why**: Keeps the day focused on the Workflow API without wrestling with PDF parsing quirks, and markdown is easier to inspect/debug. Include a small `docs/` folder with 2-3 sample markdown files in the day's directory
- **Source**: user

## D4: What model and embedding setup should we use?
- **Decision**: Local Ollama `llama3.2` for LLM + HuggingFace `BAAI/bge-small-en-v1.5` for embeddings (via `llama-index-embeddings-huggingface`)
- **Why**: The LlamaIndex docs show this as the standard local setup pattern. Ollama for generation, HuggingFaceEmbedding for embeddings (not OllamaEmbedding). Use `request_timeout=360.0` and `context_window=8000` per docs recommendations
- **Source**: codebase (LlamaIndex official docs pattern)

## D5: What should the workflow steps be?
- **Decision**: 3-step pattern matching the docs: ingest (load docs, build index) → retrieve (query index, get nodes) → synthesize (generate answer from nodes)
- **Why**: Matches the LlamaIndex RAG Workflow example exactly and clearly demonstrates the event-driven flow. Adding query prep would muddy the teaching point (which is about Workflows, not query rewriting). Combined retrieve+synthesize would lose the event granularity we want to showcase
- **Source**: user

## D6: What should the CLI interface look like?
- **Decision**: REPL pattern with commands: `ingest <dir>`, `query <text>`, `exit`. Use `rich` for the REPL UI
- **Why**: Matches Day 1's pattern and keeps it familiar. Rich provides good formatting for displaying the streamed events. REPL allows multiple queries after a single ingest, which is a natural usage pattern
- **Source**: user

## D7: Should the index persist across runs?
- **Decision**: Yes, persist the index to disk (like Day 1) using `index.storage_context.persist()` to `.workflow_index/`
- **Why**: Matches Day 1's pattern and is more practical for real usage. The LlamaIndex docs show this as the standard pattern. Allows reusing without re-ingesting
- **Source**: user

## D8: What events should we define for the workflow?
- **Decision**: Two custom events: `IngestedEvent` (index built, passed to retrieve step) and `RetrievedEvent` (nodes retrieved, passed to synthesize step)
- **Why**: Better demonstrates the event-driven pattern with typed events flowing between steps. Using only `Context.store` would miss the teaching point about typed events. Two events show the full pipeline flow clearly
- **Source**: user

## D9: Should we use a single workflow class or separate workflows for ingest vs query?
- **Decision**: Single workflow class — steps branch based on `StartEvent` fields (has `dirname` for ingest, has `query` for query)
- **Why**: Matches the LlamaIndex docs pattern and demonstrates how workflows can handle multiple entry points through the same step graph. Branching logic is simple and keeps the code focused on one cohesive pipeline
- **Source**: user
