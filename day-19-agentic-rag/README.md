# Day 19 — Agentic RAG

RAG with a decision in front of it. A `classify` step judges whether the query is vague; only then does a `rewrite` step run, and the vague query gets answered **twice** — raw and rewritten, same index — so an LLM judge can score both against the original question.

## Outcome

The decision works. The rewriting mostly doesn't.

A specific query skips the rewrite entirely and scores best for the least work — **5/5 off one LLM call instead of six**:

```text
❯ query What is the difference between prompt caching and semantic caching?
  → ClassifiedEvent SPECIFIC no rewrite — answering as typed
  → AnsweredEvent raw 3 nodes: caching.md, agent-memory.md, deployment.md
╭─ Q: What is the difference between prompt caching and semantic caching? ─╮
│ Already specific — no rewrite.                                           │
│ raw judge: 5/5                                                           │
╰──────────────────────────────────────────────────────────────────────────╯
```

A vague one gets rewritten, and the rewrite makes it **worse** — 4/5 down to 1/5. The rewriter had no documents about what it invented, so it retrieved a different, weaker set and gave up; the raw query meanwhile got a good answer explaining *why vague queries retrieve badly*:

```text
❯ query why is my search bad?
  → ClassifiedEvent VAGUE rewriting, then answering both
  → RewrittenEvent What are the implications of using a cached model on agent
    memory for efficient evaluation and retrieval in local versus hosted…
  → AnsweredEvent raw       3 nodes: retrieval.md, caching.md, evaluation.md
  → AnsweredEvent rewritten 3 nodes: caching.md, agent-memory.md, deployment.md

raw       judge: 4/5  "…vague queries embed to a vector near the center of
                        the corpus and return weakly-related chunks."
rewritten judge: 1/5  "I don't know based on the provided context."
```

Session tally on `exit`:

```text
          Session — judge scores (1-5)
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ bucket                  ┃ queries ┃ avg score ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ raw query (vague)       │       1 │      4.00 │
│ rewritten query         │       1 │      1.00 │
│ skipped — already clear │       1 │      5.00 │
└─────────────────────────┴─────────┴───────────┘
```

Across the session rewriting never won — it tied or lost. **Honest limit:** n=3 queries, one judge model, and the vagueness labels are mine. This is a demo, not an eval harness (that's Day 20).

## What it took to get any signal

Two things had to change before the comparison meant anything:

1. **`llama3.2` cannot be the judge.** A 3B model scoring 1-5 flattens toward one value regardless of answer quality, so the tally measured nothing. The judge is `qwen3:14b`; everything else stays on `llama3.2`.
2. **The classifier needs few-shot examples.** Given the criteria as prose it answers VAGUE to nearly everything — including "what is the difference between prompt caching and semantic caching?" — while calling "how do I make it faster?" specific. With four examples it hits **7/8** on a hand-labelled set, and *still* misreads one query that appears verbatim in its own prompt.

Also: `temperature=0` throughout. At Ollama's default the classifier returned different verdicts for the same query on consecutive runs.

## Stack

- **LlamaIndex Workflows** (`llama-index-workflows` 2.x) — `@step` functions, typed `Event`s, `ctx.send_event` fan-out, `ctx.collect_events` join
- **Ollama `llama3.2`** — classify, rewrite, answer (local, `temperature=0`)
- **Ollama `qwen3:14b`** — judge only (local, `temperature=0`)
- **HuggingFace `BAAI/bge-small-en-v1.5`** — embeddings
- **rich** — REPL UI

## Run

```bash
ollama serve                     # plus: ollama pull llama3.2 && ollama pull qwen3:14b
uv sync && uv run main.py
```

Commands in the REPL:

- `ingest <dir>` — load markdown files, build the vector index, persist to `.agentic_rag_index/`
- `query <text>` — classify → rewrite if vague → answer each path → judge, streaming every event
- `exit` — quit and print the score tally

## Design notes

- `ingest` and `classify` both take `StartEvent` and each returns `None` on the other's path — two single-purpose entry steps rather than one branching step.
- `rewrite` is where the branch happens: it either returns one `AnswerRequest`, or writes a `RewrittenEvent` to the stream and `ctx.send_event`s two. `judge` joins them back with `ctx.collect_events(ev, [AnsweredEvent] * expected)`, so the same step handles one answer or two.
- `answer` runs `num_workers=1` deliberately. At 2, both paths embed concurrently on one shared `HuggingFaceEmbedding` and torch intermittently spins forever. Serial costs nothing — Ollama generates one at a time regardless.
- A vague query costs 6 LLM calls, two of them on a 14B model. Expect minutes, not seconds.
- Full decision log: `openspec/changes/day-19-agentic-rag/` (D8a records the judge-model swap).
