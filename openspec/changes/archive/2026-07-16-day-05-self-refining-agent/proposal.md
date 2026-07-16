# Day 5 — Self-Refining Agent Proposal

## Why

Day 5 of the 50-days-of-dev challenge exercises **self-improving agents**: an agent that critiques and revises its own output in a reflect-retry loop. The lesson only lands if the improvement is *measured*, not asserted — so this build scores every iteration on three real axes (test pass rate, code quality, runtime) using established static-analysis tooling rather than the LLM's own opinion of its work. The deliverable is an interactive Rich REPL where the user watches an agent write code, grade itself, and get better; the built-in coding tasks exist to make that improvement demonstrable and graphable.

## What Changes

- Add `day-05-self-refining-agent/` as a self-contained Python day project (folder, `pyproject.toml`, `AGENTS.md`, `architecture.md`, and `.gitignore` already scaffolded).
- Implement a **LangGraph reflect-retry loop**: generate → test → score → critique → revise, iterating until improvement plateaus rather than for a fixed count.
- Implement a **real metrics layer**: `radon` for maintainability index and cyclomatic complexity, `pylint` for PEP8/style violations, `timeit` for runtime. Composite quality score = 40% maintainability + 30% style + 30% complexity.
- Implement an **explicit memory log**: after each task plateaus, the agent distills 3–5 transferable insights to a human-readable Markdown file, and reads that log before starting the next task so learning compounds across tasks and across sessions.
- Implement **three built-in tasks** (sorting, graph shortest-path, Ollama-backed REPL builder) run sequentially, each to plateau.
- Implement an **interactive Rich REPL** as the default entrypoint (`uv run main.py`), plus `uv run main.py --demo` for an automated all-tasks run.
- Emit **JSON + CSV per task** to `results/` so the improvement curve can be graphed externally.
- **Execute LLM-generated code in a subprocess sandbox** with a wall-clock timeout — required because scoring the agent's output means running it.

## Capabilities

### New Capabilities

- `self-refining-loop`: The LangGraph state machine that drives generate → test → score → critique → revise, tracks per-iteration deltas, detects plateau, retains the best-scoring version, and sequences the three tasks.
- `code-quality-metrics`: The measurement layer — pass rate from the task's test suite, composite quality score from `radon` + `pylint`, runtime from `timeit` — plus sandboxed execution of generated code and JSON/CSV emission.
- `agent-memory-log`: Cross-task and cross-session learning persistence: distilling transferable insights on task completion, and injecting them into generation for subsequent tasks.
- `refinement-repl`: The Rich terminal interface — interactive command surface (default) and the automated `--demo` run, including live per-iteration metric display.

### Modified Capabilities

None.

## Impact

- **New dependencies**: `langgraph` and `langchain-ollama` (loop + local model), `radon` and `pylint` (metrics), `rich` (REPL). Local-model-first per repo convention — no hosted API key required.
- **Executes model-generated code.** Scoring requires running what the agent writes. Generated code runs in a subprocess with a timeout and is never `exec`'d in the host process. This is the first day in the challenge that runs untrusted generated code; the sandbox boundary is a first-class requirement, not an implementation detail.
- **Requires Ollama running locally** with a code-capable model pulled; the REPL should fail with a clear message rather than a stack trace if it is not.
- `results/` (metrics output and `memory_log_<model>.md`) is written at runtime and gitignored — except the memory logs, which are the artifact proving cross-session learning and are worth committing. Logs are keyed per model so that swapping models cannot silently contaminate a comparison.
- Wall-clock risk: plateau-based iteration on a local model is unbounded by construction. An iteration cap per task is required so a demo run terminates.
- No changes to existing days or to root workspace configuration.
