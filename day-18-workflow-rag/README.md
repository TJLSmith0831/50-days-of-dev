# Day 18 — Workflow RAG

RAG over local markdown built as a 3-step **LlamaIndex Workflow** (ingest → retrieve → synthesize), streaming the typed events between steps on every query.

## Outcome

Every query shows the workflow's event-driven flow live — `IngestedEvent` and `RetrievedEvent` stream to the terminal with per-node scores and previews before the answer renders. Day 1's chain hid the pipeline; here the pipeline is the visible artifact.

```text
❯   → IngestedEvent index loaded from disk, handing off to retrieve step
    → RetrievedEvent 3 nodes
      [0] score=0.809 workflows.md # LlamaIndex Workflows …
╭──────── Q: how does stream_events work in a workflow? ────────╮
│ `stream_events()` yields every event as it flows through the  │
│ pipeline, which allows observing a run in real-time.          │
╰───────────────────────────────────────────────────────────────╯
```

## Stack

- **LlamaIndex Workflows** (`llama-index-workflows` 2.x) — `@step` functions, typed `Event`s, `Context.store`
- **Ollama `llama3.2`** — LLM (local, `request_timeout=360.0`, `context_window=8000`)
- **HuggingFace `BAAI/bge-small-en-v1.5`** — embeddings (local, ~100 MB download on first use)
- **rich** — REPL UI

## Run

```bash
ollama serve                     # plus: ollama pull llama3.2
uv sync && uv run main.py
```

Commands in the REPL:

- `ingest <dir>` — load markdown files, build the vector index, persist to `.workflow_index/`
- `query <text>` — retrieve + synthesize, streaming intermediate events
- `exit` — quit

## Design notes

- One `RAGWorkflow` class handles both entry points: the `ingest` step branches on `StartEvent.dirname` vs `StartEvent.query` (single workflow, two entry points).
- The query path loads the persisted index from `.workflow_index/` and emits `IngestedEvent`, so `retrieve` always receives an index the same way regardless of entry point.
- `llama-index-workflows` 2.x streams only events explicitly passed to `ctx.write_event_to_stream()` — steps write each custom event to the stream before returning it (see `decisions.md` D10 in the openspec change).
- Full decision log: `openspec/changes/day-18-workflow-rag/`.
