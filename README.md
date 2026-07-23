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
| 13 | 7/24 Fri | A2A handoff | Handoff Demo — agent A hands a task to agent B via A2A-style handoff | Py/TS | local | planned |
| 14 | 7/25 Sat | Ship-it | Ship Day — take Week 2's strongest build to portfolio-grade (see Ship DoD); target picked at week's end | — | — | planned |
| 15 | 7/26 Sun | Context engineering | Context Rebuild — raw prompt vs structured context, same task, compare output | Py | local | planned |
| 16 | 7/27 Mon | Chunking | Chunk Showdown — fixed vs semantic chunking, retrieval precision compared | Py | local | planned |
| 17 | 7/28 Tue | Reranking | Reranked Search — before/after reranker on 10 queries | Py | local | planned |
| 18 | 7/29 Wed | LlamaIndex Workflows | Workflow RAG — one ingestion-to-answer pipeline | Py | local | planned |
| 19 | 7/30 Thu | Agentic RAG | Smart RAG — agent rewrites a vague query before retrieving, compare quality | Py | local | planned |
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
| 38 | 8/18 Tue | Agent memory | Remembering Agent — long-term memory via vector store, recall a fact from 3 turns ago | Py | local | planned |
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