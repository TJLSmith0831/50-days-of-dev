# Day 19 — Agentic RAG — Decision Log

Topic: Smart RAG — agent rewrites a vague query before retrieving, compare quality

## D1: What makes this different from Day 1 (LangChain RAG) and Day 18 (Workflow RAG)?
- **Decision**: Days 1 and 18 both retrieve on the raw user query verbatim. Day 19 adds a query-rewrite step before retrieval: an LLM call reformulates a vague/underspecified query into a more retrieval-friendly one, then both the raw and rewritten queries are run through the same retrieval+answer pipeline so results are directly comparable.
- **Why**: Matches the README topic line exactly ("agent rewrites a vague query before retrieving, compare quality") and is the smallest addition that turns plain RAG into *agentic* RAG — a decision step (rewrite or not / how to rewrite) added to the pipeline.
- **Source**: user (README topic line)

## D2: How is "quality" scored for the comparison?
- **Decision**: LLM-as-judge — a separate local LLM call scores each pipeline's final answer against the question (blind to which pipeline produced it), producing a per-query score used to tabulate raw-vs-rewritten quality.
- **Why**: User-selected. No gold answer set needed, keeps day scoped to ~1-2 hrs unlike hand-labeling a gold chunk set (Day 17-style).
- **Source**: user

## D3: What stack/base does Day 19 build on?
- **Decision**: LlamaIndex Workflows, extending Day 18's pattern — add a `RewriteEvent` step before retrieve, so the pipeline becomes rewrite → retrieve (x2: raw + rewritten) → synthesize (x2) → judge.
- **Why**: User-selected. Keeps the event-driven step/typed-event pattern established Day 18, and a rewrite step composes naturally as one more `@step` in the same graph.
- **Source**: user

## D4: What doc corpus does Day 19 ingest?
- **Decision**: New small markdown corpus (3-5 files) written for this day, covering distinct-but-adjacent topics deliberately chosen so a vague query could plausibly match multiple docs (e.g. topics that share vocabulary but diverge in specifics).
- **Why**: User-selected. Reusing Day 18's 3 docs risks not demonstrating ambiguity, since the whole point of the day is showing the rewrite step disambiguate a vague query — needs a corpus built for that.
- **Source**: user

## D5: How are vague test queries generated/selected?
- **Decision**: REPL-driven — a `query <text>` command (matching Days 1/18) where the user types vague queries live; each one streams rewrite → both retrievals → both answers → judge verdict. No fixed hardcoded benchmark batch.
- **Why**: User-selected. Consistent with the established REPL pattern; the README's reported outcome will cite whichever vague queries were run during the demo/dev session rather than a pre-baked set.
- **Source**: user

## D6: What does the CLI show as the measured "compare quality" result?
- **Decision**: Per-query rich Panel showing the rewritten query, both answers, and both judge scores, plus a running summary Table (raw-score vs rewritten-score tally) printed on exit — mirrors Day 1's per-question latency table pattern.
- **Why**: User-selected. Gives both live per-query insight and a single aggregate snapshot suitable for the README's measured-outcome line and tracker entry.
- **Source**: user

## D7: Does the agent always rewrite, or decide whether to?
- **Decision**: Agent decides — a cheap classification step (LLM call: "is this query already specific enough to retrieve well?") runs first; if clear, skip rewriting and the two paths collapse to one (raw only, table row marks it "skipped — already clear" with a single score, not a raw-vs-rewritten pair). If vague, proceed with full rewrite → dual-retrieve → dual-answer → judge as in D1/D6.
- **Why**: User-selected — this is the actual "agentic" decision point (whether to act), not just a fixed rewrite-always pipeline. Interacts with D6: the running summary table needs a third bucket ("skipped") alongside raw-wins/rewritten-wins/tie, so the aggregate stays honest when not every query produces a comparable pair.
- **Source**: user

## D8: What model/embedding setup does the workflow use?
- **Decision**: ~~Same as Day 18 — Ollama `llama3.2` for all four LLM roles.~~ **Amended at implementation time (see D8a).** Ollama `llama3.2` (`request_timeout=360.0`, `context_window=8000`) for classify/rewrite/synthesize; Ollama `qwen3:14b` for judge only. HuggingFace `BAAI/bge-small-en-v1.5` for embeddings.
- **Why**: Reuses the day's own proven local setup for the three roles where a 3B model is adequate; the judge is the one role where model capacity directly determines whether the day has a reportable result.
- **Source**: codebase (`day-18-workflow-rag/main.py:103-104`), amended by user

## D8a: Why is the judge a different (larger) model than the rest?
- **Decision**: The `judge` step uses Ollama `qwen3:14b` (already pulled locally); classify/rewrite/synthesize stay on `llama3.2`. Amends D8's "one model for all four roles".
- **Why**: User-selected. The day's headline outcome is a raw-vs-rewritten score comparison, so the judge is the measurement instrument, not just another prompt. A 3B model scoring on a 1-5 scale tends to flatten toward a single value, which would make the aggregate table (D6/D9) unciteable regardless of whether rewriting actually helped. The original D8 rationale ("no reason to introduce a second model") assumed all four roles were equally forgiving; they are not — a bad synthesis is visible in the transcript, a bad judge silently invalidates the measurement. Cost is judge latency, accepted since the REPL is a demo, not a throughput path.
- **Source**: user

## D9: What scale/format does the LLM judge use?
- **Decision**: 1-5 integer score per answer, judged independently (blind to which path produced it) against the original question. The running Table (D6) tallies raw-avg vs rewritten-avg per session, plus the skipped bucket (D7) count.
- **Why**: User-selected. Finer-grained than pass/fail, and simpler to implement than a single head-to-head judge call structured around two answers at once.
- **Source**: user

## D10: What are the workflow's steps/events?
- **Decision**: `classify` (StartEvent → `ClassifiedEvent{is_vague: bool}`) → if not vague: `retrieve`/`synthesize` once → `judge` scores the single answer → `StopEvent`. If vague: `rewrite` (→ `RewrittenEvent{rewritten: str}`) → `retrieve`+`synthesize` run for both raw and rewritten paths, each emitting `AnsweredEvent{path: "raw"|"rewritten", answer: str, nodes: list[NodeWithScore]}` → `judge` collects one or two `AnsweredEvent`s (via `ctx.collect_events`) and scores each → `StopEvent{result: {...}}`.
- **Why**: User-accepted. Extends Day 18's typed-event pattern (`IngestedEvent`/`RetrievedEvent`) with new events for the branching/comparison logic added in D1/D7, keeping each step single-responsibility and streamable via `ctx.write_event_to_stream()` per Day 18's D10.
- **Source**: recommended-accepted

## D11: What topics does the new markdown corpus cover?
- **Decision**: 5 short docs — `caching.md` (semantic vs prompt caching), `agent-memory.md` (short vs long-term), `evaluation.md` (LLM-as-judge vs golden sets), `retrieval.md` (dense vs reranking), `deployment.md` (local vs hosted) — in a `docs/` folder under `day-19-agentic-rag/`.
- **Why**: Recommended and accepted. Topics deliberately overlap in vocabulary (e.g. "evaluation" touches both `evaluation.md` and `retrieval.md`'s reranking discussion) so a vague query has real ambiguity to resolve, and each topic maps to this challenge's own Weeks 4-6 themes so content is accurate without external research.
- **Source**: recommended-accepted

## D12: What implementation patterns carry over unchanged from Day 18?
- **Decision**: `similarity_top_k=3` for both raw and rewritten retrievers; index persists to a new `.agentic_rag_index/` dir (distinct from Day 18's `.workflow_index/` since the corpus differs) via `index.storage_context.persist()`; REPL commands stay `ingest <dir>` / `query <text>` / `exit`; Ollama-reachability check at startup (`localhost:11434`) before initializing the workflow.
- **Why**: These are mechanical reuses of Day 18's already-working patterns with no reason to diverge — only the index directory name changes because it's a different corpus/index.
- **Source**: codebase (`day-18-workflow-rag/rag_workflow.py:56,80`, `day-18-workflow-rag/main.py:26,30-40,133-140`)

## D13: What are the explicit non-goals?
- **Decision**: Out of scope — reranking (Day 17's territory), a formal eval harness/golden datasets (Day 20/27), and production concerns (rate limiting, auth, deployment).
- **Why**: Recommended and accepted. Keeps the day scoped to the rewrite/classify/judge comparison rather than re-solving already-covered or not-yet-covered days' topics.
- **Source**: recommended-accepted
