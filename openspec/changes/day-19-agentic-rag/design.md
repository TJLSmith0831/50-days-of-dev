## Context

Day 19 is a standalone implementation in the 50-days-of-dev challenge, extending Day 18's LlamaIndex Workflow RAG pipeline with an agentic decision point: an LLM classifies whether a query is vague, and if so rewrites it before retrieval, so raw-query and rewritten-query answers can be compared via an LLM judge. The implementation is self-contained in `day-19-agentic-rag/` with its own dependencies and a new sample corpus.

## Goals / Non-Goals

**Goals:**

- Add a `classify` step that decides whether a query needs rewriting (the actual "agentic" decision point) (D7)
- Add a `rewrite` step for vague queries, then run retrieve+synthesize on both the raw and rewritten query so they're directly comparable (D1, D10)
- Add an LLM-as-judge `judge` step that scores each answer 1-5 against the original question, independent of which path produced it (D2, D9)
- Build a REPL CLI (rich Panel per query + running summary Table on exit) matching Days 1/18's UX (D6)
- Use a new markdown corpus with deliberately overlapping topics so vague queries create real retrieval ambiguity (D4, D11)
- Reuse Day 18's local model setup (Ollama `llama3.2`, HuggingFace `bge-small-en-v1.5`) for every LLM role (D8)

**Non-Goals:**

- Reranking (Day 17's territory) (D13)
- A formal eval harness or golden datasets (Day 20/27's territory) (D13)
- Production concerns — rate limiting, auth, deployment (D13)

## Decisions

**Classify-then-branch workflow** (D7, D10)

- `classify` runs first on every query (`StartEvent → ClassifiedEvent{is_vague: bool}`). If not vague, the workflow collapses to a single `retrieve → synthesize → judge` path. If vague, it proceeds through `rewrite → RewrittenEvent{rewritten: str}`, then `retrieve`/`synthesize` run for both the raw and rewritten queries, each emitting `AnsweredEvent{path: "raw"|"rewritten", answer: str, nodes: list[NodeWithScore]}`, which `judge` collects (via `ctx.collect_events`) before scoring.
- **Alternative considered**: Always rewrite, always run both paths (no classify step).
- **Rationale**: A fixed rewrite-always pipeline has no real decision point — it's not agentic, just a longer chain. Classifying first is the smallest change that makes "whether to act" the thing being demonstrated, matching the day's README topic line.

**Typed events over `Context.store` for the new steps** (D10)

- `ClassifiedEvent`, `RewrittenEvent`, and `AnsweredEvent` are typed `Event` subclasses passed between steps and streamed via `ctx.write_event_to_stream()`, extending Day 18's `IngestedEvent`/`RetrievedEvent` pattern.
- **Alternative considered**: Store classify/rewrite/answer state in `ctx.store` and have `judge` read it back directly.
- **Rationale**: Keeps the event-driven, streamable pattern established in Day 18 consistent across both days; each step's output stays visible in `stream_events()` without extra plumbing to reconstruct it from store keys.

**1-5 LLM-judge scoring, per answer** (D2, D9)

- A judge prompt scores each `AnsweredEvent`'s answer independently (blind to `path`) on a 1-5 scale against the original question. The workflow's `StopEvent.result` carries both scores (or one, if skipped).
- **Alternative considered**: Binary pass/fail, or a single head-to-head preference judged with both answers shown together.
- **Rationale**: 1-5 gives finer-grained signal than pass/fail for a "compare quality" framing, and independent scoring is simpler to implement than a combined head-to-head judge call.

**REPL output: per-query Panel + running summary Table** (D6)

- Each `query <text>` prints a rich Panel with the rewritten query (if any), both answers, and their scores. On `exit`, a summary Table tallies raw-avg score, rewritten-avg score, and skipped-count across the session — mirrors Day 1's per-question latency table.
- **Alternative considered**: Per-query output only, no aggregate.
- **Rationale**: The day's whole point is a *measured* comparison; a session-level tally is the artifact that makes the outcome citable in the README, not just anecdotal per-query prints.

**New markdown corpus with overlapping topics** (D4, D11)

- `docs/` gets 5 new files: `caching.md`, `agent-memory.md`, `evaluation.md`, `retrieval.md`, `deployment.md` — topics chosen to overlap in vocabulary (e.g. "evaluation" touches both `evaluation.md` and `retrieval.md`'s reranking discussion) so a vague query like "tell me about evaluation" has genuine ambiguity to resolve.
- **Alternative considered**: Reuse Day 18's 3 markdown files.
- **Rationale**: Day 18's docs are narrow/non-overlapping and wouldn't demonstrate the rewrite step's value; a corpus needs deliberate ambiguity for the comparison to mean anything.

**Model/index reuse from Day 18** (D8, D12)

- Ollama `llama3.2` (`request_timeout=360.0`, `context_window=8000`) handles classify, rewrite, synthesize, and judge via different prompts; HuggingFace `bge-small-en-v1.5` handles embeddings; `similarity_top_k=3` for both retrievers; index persists to a new `.agentic_rag_index/` dir (separate from Day 18's `.workflow_index/` since the corpus differs).
- **Alternative considered**: A separate, smaller/faster model for classify (since it's a simpler task than synthesis).
- **Rationale**: One model already proven to work locally in Day 18; introducing a second model adds setup complexity without a clear day-scoped teaching benefit.

## Risks / Trade-offs

**[Risk] Classify step misjudges vagueness** → Mitigation: This is itself the interesting behavior to observe and report on (the agent's decision quality is part of what the day demonstrates), not a bug to eliminate. The REPL surfaces the classify verdict per query so misjudgments are visible, not hidden.

**[Risk] Judge score noise from a small local model** → Mitigation: Accepted as a known limitation of local LLM-as-judge (documented in the day's README); the running Table's averages smooth out some per-query noise across a session.

**[Risk] Ollama server not running** → Mitigation: Reuse Day 18's startup check against `localhost:11434` with a clear error message before initializing the workflow.

**[Trade-off] Four LLM roles (classify/rewrite/synthesize/judge) via one model** → Slower per-query latency (up to 4-5 sequential LLM calls for a vague query) versus a lighter pipeline, but acceptable for a REPL demo day scoped to illustrating the comparison, not production throughput.

**[Trade-off] No fixed benchmark query set** → The reported "measured outcome" depends on whichever vague queries are typed during the demo session (D5), which is less rigorous than a fixed golden set, but matches Days 1/18's REPL-first pattern and keeps the day's scope to ~1-2 hrs.

## Migration Plan

No migration required — this is a new standalone day implementation. The workflow:

1. Create `day-19-agentic-rag/` directory structure
2. Add `pyproject.toml` with dependencies (same as Day 18)
3. Implement the workflow class with classify/rewrite/retrieve/synthesize/judge steps and new events
4. Implement the REPL with rich (Panel per query, summary Table on exit)
5. Add the 5 new markdown files to `docs/`
6. Register the day in root `pyproject.toml` workspace
7. Test classify-skip, classify-vague-rewrite, and judge-scoring flows

## Open Questions

None — all technical decisions are resolved in the decision log (`decisions.md`).
