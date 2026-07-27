# Day 16 — Typed Graph Vault — AGENTS.md

Markdown vault → validated typed graph, split-model REPL (Qwen3 planner + Mistral answerer), and standalone HTML/SVG path visualizer.

## Stack

Python · Pydantic · PyYAML · Ollama (`qwen3:14b` for planning, `mistral:latest` for synthesis)

## Commands (verified 2026-07-27)

- `uv run main.py --self-check` — validate the tracked example vault without Ollama.
- `uv run main.py` — start the REPL; requires Ollama with `qwen3:14b` and `mistral:latest` for `ask`.
- `npx playwright screenshot --device "Desktop Chrome HiDPI" --full-page "file://$PWD/graph.html" graph-screenshot.png`
  — refresh the handoff screenshot after `graph` has written a path into `graph.html`.

## Gotchas

- `vault/` is ignored and overrides `example-vault/` when present.
- A malformed vault blocks queries until it validates again via `reload`.
- The planner runs with `think=False`. Qwen3 is a hybrid reasoning model; left
  on it spends ~2 minutes reasoning out a plan the JSON schema already
  constrains. With it off a plan takes ~2s.
- The planner catalog includes each node's outgoing links. Without them it knows
  the relation vocabulary but not which node has which relation, and a guessed
  first hop that matches no edge returned `No grounded graph path found.` on
  roughly one question in five.
- `traverse` skips a relation with no matching edge from the current frontier
  instead of abandoning the plan, so one speculative hop no longer costs the
  whole chain.
- `ask` is slowest on the qwen3 → mistral swap (~15s cold), not on inference.
