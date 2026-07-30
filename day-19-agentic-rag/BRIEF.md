# Day 19 — Agentic RAG — BRIEF.md

## What was built

A LlamaIndex Workflow that puts a decision in front of retrieval. `classify` judges whether the query is vague; if it is, `rewrite` reformulates it and the workflow answers the raw *and* rewritten queries against the same index, then an LLM judge scores each answer 1-5 against the original question. If the query is already specific there is no rewrite and no second answer. REPL commands are `ingest <dir>`, `query <text>`, `exit` — `exit` prints a session tally with three buckets: raw, rewritten, and skipped.

## Implementation facts

- `AgenticRAGWorkflow` has five `@step` methods: `ingest`, `classify`, `rewrite`, `answer`, `judge`.
- `ingest` and `classify` both accept `StartEvent`; each returns `None` on the other's path. If neither `dirname` nor `query` is set, `classify` raises rather than letting the run sit until the timeout.
- Custom events: `ClassifiedEvent{is_vague}`, `RewrittenEvent{rewritten}`, `AnswerRequest{path, query}`, `AnsweredEvent{path, query, answer, nodes}`.
- `rewrite` is the branch. Specific → returns one `AnswerRequest(path="raw")`. Vague → writes `RewrittenEvent` to the stream and `ctx.send_event`s two `AnswerRequest`s (`raw`, `rewritten`).
- `judge` joins with `ctx.collect_events(ev, [AnsweredEvent] * expected)`, where `expected` (1 or 2) was stored by `rewrite`. It scores each answer blind to its path.
- `answer` is `@step(num_workers=1)`, deliberately serial.
- LLM: Ollama `llama3.2`, `temperature=0`, `request_timeout=360.0`, `context_window=8000`. Judge: Ollama `qwen3:14b`, same settings.
- Embeddings: HuggingFace `BAAI/bge-small-en-v1.5`, `similarity_top_k=3` for both paths.
- Index persists to `.agentic_rag_index/`; it is cached on the workflow instance after first load, since two steps per query need it.
- Corpus: 5 markdown files with deliberately overlapping vocabulary — `caching.md`, `agent-memory.md`, `evaluation.md`, `retrieval.md`, `deployment.md`.

## Discoveries during implementation

1. **`num_workers=2` on the answer step hangs.** Running the raw and rewritten paths concurrently means two threads calling the same `HuggingFaceEmbedding` at once. Torch intermittently spins instead of returning — observed as two cores pinned for 13 minutes with *zero* requests reaching Ollama, plus a `loky` leaked-semaphore warning at shutdown. No timeout fires because the workflow's clock only sees a step that never returned. Fixed by `num_workers=1`; the parallelism bought nothing anyway, since Ollama serializes generations on one model.

2. **`llama3.2` is unusable as the judge.** It flattens toward a single score regardless of answer quality, which silently invalidates the whole comparison — a bad synthesis is visible in the transcript, a bad judge is not. The judge moved to `qwen3:14b` (logged as D8a, amending D8). qwen3 is a thinking model, so `_parse_score` strips the `<think>` block — it is full of digits — before reading the score.

3. **The classify prompt needs few-shot examples.** With the criteria stated as prose and no examples, `llama3.2` answered VAGUE to almost every query, including "what is the difference between prompt caching and semantic caching?", while calling "how do I make it faster?" SPECIFIC. Four examples took it to 7/8 on a hand-labelled set. It still misclassifies "how do I make it faster?" — a query that appears **verbatim in its own prompt** as a VAGUE example.

4. **Default temperature makes the demo unreproducible.** The classifier returned VAGUE and SPECIFIC for "tell me about evaluation" on consecutive sessions. `temperature=0` everywhere.

5. **Asking for a reason alongside the verdict degrades the verdict.** The first classify prompt requested `VAGUE - <eight words of reason>`; dropping the reason is what recovered the accuracy. `ClassifiedEvent` carries only `is_vague`.

6. **The two-model setup can take Ollama down with it.** Ollama keeps one model resident at a time on this machine, so each query evicts `llama3.2` for `qwen3:14b` and back. During the first demo recording the server died mid-session; the REPL, which only caught `ValueError`, went down with it and the take ended on a Python traceback where the second query should have been. `run_query` now catches every exception, prints it, re-checks the server, and keeps the REPL alive so the tally survives. The capture script gates on the absence of a traceback in the take.

## Verification

- Ingest: `ingest docs` reported "Ingested 5 documents (5 nodes), persisted to …/.agentic_rag_index" and the directory was created.
- Skip path: `query What is the difference between prompt caching and semantic caching?` streamed `ClassifiedEvent SPECIFIC`, one `AnsweredEvent raw`, and scored **5/5**. No `RewrittenEvent`, no second answer.
- Vague path: `query why is my search bad?` streamed `ClassifiedEvent VAGUE`, `RewrittenEvent`, then both `AnsweredEvent raw` and `AnsweredEvent rewritten` — raw **4/5**, rewritten **1/5**. The two paths retrieved different node sets (`retrieval.md, caching.md, evaluation.md` vs `caching.md, agent-memory.md, deployment.md`).
- Judge output: scores are 1-5 integers; observed 1, 3, 4, and 5 across the session, so the scale is not collapsing.
- Tally: on `exit` the table showed raw 1 @ 4.00, rewritten 1 @ 1.00, skipped 1 @ 5.00.
- Error handling: `ingest /nonexistent-dir` → "Not a directory: /nonexistent-dir". Querying with no index → "No index at … — run `ingest <dir>` first." Empty `StartEvent` → "StartEvent needs either `dirname` or `query`." Unknown command → command list.
- Linting: `ruff check` passed.

## The measured claim

Rewriting never won. Across the session it tied or lost, and on the one query where the difference was large it lost badly (4/5 → 1/5) because the rewriter invented specificity the corpus could not support. The classify decision itself is the part that paid off: the specific query got the best score off one LLM call instead of six.

n=3 queries, one judge model, vagueness labels are the author's. Indicative, not an eval.
