# Day 15 — Agent Memory Recall

Compare a stateless Ollama agent against a Mem0-backed agent on cross-session fact recall.

## Run

    uv run main.py

## What it does

- 3 fact/question pairs, each isolated under its own Mem0 `user_id`.
- Each turn is an independent fresh-session Ollama `mistral` chat call.
- No-memory lane: no injected context, expected to fail/hallucinate.
- Memory-backed lane: seed + 3 filler turns are stored in local Mem0 (Chroma + `nomic-embed-text`), then retrieved before the recall question.
- Grading: case-insensitive substring match on an expected keyword.
- Prints a pass/fail table with per-pair and per-lane totals.
