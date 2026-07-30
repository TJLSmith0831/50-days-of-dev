# Day 19 — Agentic RAG — AGENTS.md
RAG that decides whether to rewrite a vague query before retrieving, then runs the raw and rewritten queries side by side and has an LLM judge score both.

## Stack
Python · LlamaIndex Workflows (`llama-index-workflows`, `llama-index-core`) · Ollama local (`llama3.2` for classify/rewrite/answer, `qwen3:14b` for the judge) · HuggingFace embeddings (`BAAI/bge-small-en-v1.5`) · `rich` (CLI)

## Commands (verified 2026-07-30)
`uv run main.py` — requires `ollama serve` running with both `llama3.2` and `qwen3:14b` pulled.

## Concept
Day 18 retrieved on the raw query, always. The agentic part here is the *decision*: a classify step judges whether the query is already specific, and only a vague one gets rewritten. Vague queries then run both the raw and the rewritten text through the same retriever so an LLM judge can score the two answers against the original question — the day's outcome is that comparison, not the answers.

## Gotchas
- Two steps take `StartEvent` (`ingest` and `classify`); each returns `None` on the other's path. Both fire on every run — that's the dispatch, not a bug.
- `answer` is `@step(num_workers=1)` on purpose. At 2 the raw and rewritten paths embed concurrently on one shared `HuggingFaceEmbedding` and torch intermittently spins forever — two cores pinned, no Ollama traffic, no timeout. Serial costs nothing: Ollama generates one at a time anyway.
- `temperature=0` everywhere, for reproducibility more than quality. At Ollama's default the classifier returns different verdicts for the same query across runs, which makes both the tally and a recorded demo meaningless.
- The classify prompt is few-shot because it has to be. Given the same criteria as prose with no examples, `llama3.2` answers VAGUE to almost everything while calling "how do I make it faster?" specific. With four examples it hits 7/8 on a hand-labelled set — and still misclassifies one query that appears verbatim in its own prompt.
- `_parse_verdict` scans the whole reply and takes the *last* VAGUE/SPECIFIC. The model often leads with a preamble ("Based on the criteria, this is SPECIFIC"); taking the first word gets you "BASED".
- Ollama keeps one model resident at a time here, so every query swaps `llama3.2` out for `qwen3:14b` and back. That thrashing killed the Ollama server outright once, mid-session. `run_query` catches every exception and re-checks the server rather than letting the REPL die with it — a crash costs the whole session tally. Pre-warm both models if a run has to be reliable.
- The judge is deliberately a bigger model than everything else (D8a). `llama3.2` as judge flattens every answer to the same score and the comparison stops meaning anything.
- `qwen3:14b` is a thinking model — its reply starts with a `<think>` block full of digits. `_parse_score` strips that block before reading the score; don't "simplify" it to a bare digit search.
- A vague query costs 6 LLM calls (classify, rewrite, 2 answers, 2 judgments), two of them on a 14B model. Expect ~2-4 min per vague query on a laptop; the first one also pays qwen3's ~9 GB model load.
- Rewriting is not automatically an improvement. A query with no topic at all ("how do I evaluate this?") makes the rewriter invent specificity the corpus can't answer, and the rewritten answer scores *worse*. That's a real finding, not a bug to prompt around.
- `.agentic_rag_index/` is generated state — do not commit. The index is cached on the workflow instance after first load, so `ingest` mid-session updates it in place.
