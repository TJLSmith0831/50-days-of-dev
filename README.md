# 50 Days of Dev

50 mini-projects, one per day, 7/12 → 8/30/2026 — a learning challenge, not AI-generated slop.  
Each day ships something with a **concrete, measurable outcome** ("agent does X in Y seconds"),  
scoped to ~1-2 hours, local-model-first (Ollama), posted daily to LinkedIn.  
Grand recap posted 8/31 (birthday) — no new build that day, just the wrap-up thread.

See [AGENTS.md](AGENTS.md) for repo conventions/commands. Each day's own README has the specifics.

## Decision log (short version)

*   Polyglot monorepo: uv workspace (Python) + pnpm workspace (TypeScript) coexist, folder-per-day — see AGENTS.md.
*   Local-first models (Ollama) by default; hosted APIs (Claude/GPT) only when the day's concept requires it — flagged per day below.
*   Week 1 fixed (frameworks + harness/loop); Week 2 reshaped to fold in agent-permission/governance topics early (moved up from the original plan's week 6); Weeks 3-6 keep the original topic coverage (RAG, evals, optimization, production); Week 7 is an open buffer/polish week; Day 50 is the finale, 8/31 is recap-only.
*   Weekly Saturdays (Days 7, 14, 21, 28, 35, 42) are **Ship Days**, not capstones — rather than gluing the week's six builds together, pick the single strongest build *at week's end* and take it to portfolio-grade. **Ship DoD:** one-command run verified from a clean clone, a demo GIF/screenshot of the measurable result, a real README, pinned/reproducible deps, and the LinkedIn post *is* the artifact. "Shipped" = portfolio-grade repo + demo (not a public URL) for Weeks 1-5; Week 6 (deployment) is the exception where it means a live endpoint. Builds stay independent — they feed the Day 50 finale and 8/31 recap as ~6 portfolio pieces, not one integrated app.
*   Days 37-41 swapped from already-known ops skills (streaming, rate limiting, Docker, secrets/config, health checks) to new AI-engineering territory: semantic caching, agent memory, structured outputs, prompt-injection defense, model routing.
*   Day 5 swapped from Raw agent loop (Bare-Metal Agent — already covered elsewhere) to Self-improving agents (Self-Refining Agent, reflect-retry loop).
*   No CI/test suite — each day's entrypoint run is the check.

## Tracker

| Day | Date | Topic | Project | Lang | Model | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 7/12 Sun | LangChain | Doc Speedrun — Retrieval QA over a PDF, timed | Py | local | done |
| 2 | 7/13 Mon | LangGraph | Resumable Research Agent — 3-node graph, kill mid-run & resume from checkpoint | Py | local | done |
| 3 | 7/14 Tue | Claude Agent SDK / guardrails | Repo Doctor — diagnose and repair wiring-only failures in Python repos with tool/path/command guardrails | Py | hosted (Claude) | done |
| 4 | 7/15 Wed | CrewAI | First-Principles Crew — break messy problems into fundamental truths after challenging assumptions | Py | local | done |
| 5 | 7/16 Thu | Self-improving agents | Self-Improving Agent — writes code, gets graded by real tests it never sees, and distills each struggle into persistent lessons injected into future prompts; a lesson is only saved if it provably reproduces the win from scratch. Measured: fresh runs solve the money task in 3 attempts (6/6 runs); with the verified lesson loaded, **first try, 4/4 runs**. Also measured: unvalidated lessons bank bad advice, distilling without the winning code invents remedies, and a task-specific lesson injected as a command broke an unrelated task 0/7 | Py | local | done |
| 6 | 7/17 Fri | Harness engineering | Model-Swap Harness — same capability on local Llama vs Claude, compare output/latency/cost | Py | mixed | done |
| 7 | 7/18 Sat | Ship-it | Ship Day — take Week 1's strongest build to portfolio-grade (see Ship DoD); target picked at week's end | — | — | done |
| 8 | 7/19 Sun | MCP basics | Docs MCP — minimal MCP server that exposes local project docs, proves a round-trip | TS | local | done |
| 9 | 7/20 Mon | MCP caching | Cached Weather MCP — ttlMs caching, cache-hit vs cache-miss latency | TS | hosted API (weather) | in progress |
| 10 | 7/21 Tue | Subagent orchestration | Subagent MCP — bounded advisor/researcher/critiquer subagents on local Ollama, critiquer writes token-efficiency notes to AGENTS.md/CLAUDE.md | Py | local | done |
| 11 | 7/22 Wed | Audit logging | Audited Agent — every tool call logged to an audit trail, print it after a run | Py | local | done |
| 12 | 7/23 Thu | ACP | ACP Agent — 3 real BeeAI agents (researcher/writer/critic) chained over ACP's REST protocol, CLI discovers & displays live agent-to-agent output | Py | hosted (OpenAI) | done |
| 13 | 7/24 Fri | Tool selection | Smart Tool Selector — 8 human-phrased queries × a real 8-tool catalog through 3 strategies (naive all-tools, semantic-router pre-filter, OpenAI native `ToolSearchTool`), graded Precise/Acceptable/Incorrect/Failed with call count, latency, and billed tokens. Measured: **at 8 tools nobody thrashes** — all three lanes 8/8 Precise at ~1.0 calls, so the "too many tools" premise doesn't reproduce at this catalog size. The pre-filter's real win is cost: **3,445 tokens vs naive's 8,213 (-58%)** at equal accuracy, while native `ToolSearchTool` costs **13,429 (+63% over naive)** — the discovery round trip outweighs the smaller tool payload. `tool_search` is also refused on `gpt-4.1-mini` (and gpt-5/5.1), so that lane runs on `gpt-5.4-mini` with a same-model naive control | Py | hosted (OpenAI) | done |
| 14 | 7/25 Sat | Ship-it | Ship Day — **[toolsieve](https://github.com/TJLSmith0831/toolsieve)**, shipped as its own public MIT repo. Generalizes Day 13's semantic pre-filtering into an installable MCP server: aggregates real downstream stdio MCP servers, embeds each tool's own name + description (no hand-authored utterances), and exposes **3 tools instead of every server's catalog** — `find_tools` / `call_tool` / `get_savings_report` — with a live token-savings receipt. Demoed live in Claude Code (Sonnet) against 4 real servers: **15 tools aggregated, 3 exposed, 82.4% of tool-schema tokens saved**. Two findings that changed the design: the similarity floor became a confidence *flag* not a gate (on-topic 0.56–0.83 vs off-topic 0.38–0.55 — the distributions overlap, so any strict floor rejects real matches), and savings scale with catalog size (3 tools → 0%, 15 → 80%). Ships a Claude Code plugin + setup skill that migrates your existing MCP servers behind it | Py | local (fastembed, no API key) | done |
| 15 | 7/26 Sun | Agent memory | Agent Memory Recall — stateless baseline vs Mem0-backed cross-session recall, 3 fact/question pairs, pass/fail table | Py | local | done |
| 16 | 7/27 Mon | Graph engineering | Typed Graph Vault — private Markdown vault → validated typed graph; Mistral-grounded REPL and standalone traversal visualizer | Py | local | done |
| 17 | 7/28 Tue | Reranking | Reranked Search — 10 BEIR SciFact queries through two lanes (dense top-10 with `bge-small` vs the same search over-fetched to 50 and reordered by an `ms-marco-MiniLM` cross-encoder), scored on BEIR's published qrels. Reranking won on ranking — **nDCG@10 0.604 → 0.702, MRR@10 0.532 → 0.664, hit@1 4/10 → 6/10** — and lost on recall: **recall@10 0.850 → 0.800**, because one query's gold paper fell from dense rank 6 to 49. Cost: **~6 ms → ~370 ms per query, ~18 ms per candidate** (quote the per-candidate cost, not the multiplier — the dense baseline is small enough that the ratio swings 50–66× run to run). The row the day is built on is the ceiling — a reranker reorders, it cannot retrieve, so lane B's recall@10 can never exceed lane A's recall@depth. At `--depth 20` it binds and is visible: **ceiling 0.900 over lane B's 0.800**, with one query's gold paper rendering `-` in *both* lanes because it sits at dense rank 27 and never entered the candidate set. Second finding: **depth 20 → 50 costs 2.1× the latency and moves no @10 metric at all** — over-fetching isn't free and isn't automatically better. Honest limit: n=10, four queries had gold at rank 1 in both lanes, so the hit@1 move is 2 queries flipping (exact McNemar p=0.25) — the latency numbers and the structural ceiling hold, the quality delta is indicative only. Both models local ONNX on CPU, no API key and no Ollama | Py | local (fastembed, no API key) | done |
| 18 | 7/29 Wed | LlamaIndex Workflows | Workflow RAG — Day 1's RAG rebuilt as a 3-step event-driven Workflow (ingest → retrieve → synthesize) with typed `IngestedEvent`/`RetrievedEvent` between steps; every query streams those events live (per-node scores + previews) before the answer renders. Single workflow class, two entry points branched on `StartEvent` fields; index persists to `.workflow_index/`. Found: workflows 2.x only streams events passed to `ctx.write_event_to_stream()` — returned events dispatch silently | Py | local | done |
| 19 | 7/30 Thu | Agentic RAG | Smart RAG — a `classify` step decides whether a query is vague enough to be worth rewriting; vague ones get rewritten and then answered **twice** (raw and rewritten, same index, same top-3) so a `qwen3:14b` LLM judge can score both 1-5 against the original question. The decision works — specific queries skip the rewrite and score best for the least work (**5/5**, 1 LLM call instead of 6). Rewriting did not: on "why is my search bad?" the rewriter buried the query in invented jargon it had no documents for and the answer fell **4/5 → 1/5**, while the raw query got a good answer *explaining that vague queries retrieve badly*. Across the session rewriting never won — it tied or lost. Two things had to be fixed to get any signal at all: `llama3.2` as judge flattens every answer to the same score, so the judge is a bigger local model (`qwen3:14b`); and the classifier needs few-shot examples — given the criteria as prose it answers VAGUE to almost everything, at 7/8 with examples, and still misreads one query that appears verbatim in its own prompt. Honest limit: n=3 queries, one judge model, my own vagueness labels | Py | local | done |
| 20 | 7/31 Fri | RAG evals | RAG Scorecard — score 10 Q&A pairs, publish results | Py | local | planned |
| 21 | 8/1 Sat | Ship-it | Ship Day — Ask My Docs polished to a shippable RAG app (see Ship DoD); obvious pick for the week | Py | local | planned |
| 22 | 8/2 Sun | Tracing | Traced Agent — trace one pipeline, screenshot + walkthrough of a slow span | Py | local | planned |
| 23 | 8/3 Mon | LLM-as-judge | Judged Outputs — judge scores 10 outputs, eval config + results published | Py | mixed | planned |
| 24 | 8/4 Tue | Regression testing | Regression Catch — before/after test catches a deliberately introduced bug | Py | local | planned |
| 25 | 8/5 Wed | Cost/usage tracking | Cost Dashboard — cost or token count per run, simple table | Py | mixed | planned |
| 26 | 8/6 Thu | HITL evals | Approve-or-Reject Agent — agent pauses for human sign-off before a risky action | Py | local | planned |
| 27 | 8/7 Fri | Golden datasets | Golden Set v1 — 20-example eval dataset published to the repo | Py | local | planned |
| 28 | 8/8 Sat | Ship-it | Ship Day — take Week 4's strongest build to portfolio-grade (see Ship DoD); the eval harness as a reusable CLI you'll dogfeed in Weeks 5-6 is the likely pick | — | — | planned |
| 29 | 8/9 Sun | DSPy optimization | Auto-Tuned Prompt — DSPy-optimized vs hand-written, compared on golden set | Py | local | planned |
| 30 | 8/10 Mon | DSPy pipelines | DSPy Pipeline Demo — 2-stage program with metrics | Py | local | planned |
| 31 | 8/11 Tue | LoRA/QLoRA | Fine-Tuned Mini Model — fine-tune a small local model, before/after outputs | Py | local | planned |
| 32 | 8/12 Wed | Distillation | Distilled Model Demo — distill big→small, compare on 5 tasks | Py | mixed | planned |
| 33 | 8/13 Thu | Benchmarking | Model Bakeoff — 3 models, latency/cost/quality table | Py | mixed | planned |
| 34 | 8/14 Fri | Prompt caching | Cache-Boosted App — latency before/after caching | Py | hosted (Claude) | planned |
| 35 | 8/15 Sat | Ship-it | Ship Day — take Week 5's strongest build to portfolio-grade (see Ship DoD); fine-tuned/distilled model to HF Hub w/ model card is a natural fit | — | — | planned |
| 36 | 8/16 Sun | Deployment | Live Agent Endpoint — publicly callable deployed agent, free-tier host | Py/TS | local | planned |
| 37 | 8/17 Mon | Semantic caching | Fuzzy Cache — cache hit on paraphrased queries via embedding similarity, not exact match | Py | local | planned |
| 38 | 8/18 Tue | TBD | TBD — topic moved to Day 15 (Agent Memory) | — | — | planned |
| 39 | 8/19 Wed | Structured outputs | Schema or Bust — JSON-schema-enforced output vs freeform, reliability % over 20 tries | Py | local | planned |
| 40 | 8/20 Thu | Prompt injection defense | Injection Range — 10 injection attempts, show blocked vs bypassed | Py | local | planned |
| 41 | 8/21 Fri | Model routing | Cascade Router — cheap local model handles easy queries, escalates hard ones to hosted, cost/quality compared | Py | mixed | planned |
| 42 | 8/22 Sat | Ship-it | Ship Day — deploy the production agent as a live public endpoint (see Ship DoD); the deployment-week exception where "shipped" means a real URL | Py | mixed | planned |
| 43 | 8/23 Sun | Buffer | Open — polish your weakest day so far | — | — | planned |
| 44 | 8/24 Mon | Buffer | Open | — | — | planned |
| 45 | 8/25 Tue | Buffer | Open | — | — | planned |
| 46 | 8/26 Wed | Buffer | Open | — | — | planned |
| 47 | 8/27 Thu | Buffer | Open | — | — | planned |
| 48 | 8/28 Fri | Buffer | Open | — | — | planned |
| 49 | 8/29 Sat | Buffer | Open | — | — | planned |
| 50 | 8/30 Sun | Finale | Portfolio piece — polished version of your best project | — | — | planned |
| — | 8/31 Mon | 🎂 | Grand recap thread, links to all 50 | — | — | planned |
