# Day 15 — Agent Memory Recall — AGENTS.md

Cross-session fact recall: stateless baseline vs Mem0-backed retrieval over Ollama + Chroma, printed pass/fail table.

## Stack

Python · mem0ai · chromadb · ollama · Ollama (`mistral:latest`, `nomic-embed-text:latest`)

## Commands (verified 2026-07-26)

- `uv run main.py` — run the 3 pair × 2 lane recall test and print the report (~2 min)
- `uv run main.py --self-check` — assert the report/grading logic; no Ollama needed (instant)

## Concept

Persistence across sessions is the real value of agent memory. This demo isolates that comparison by making every turn a fresh Ollama chat call; the no-memory lane has no prior context, while the memory-backed lane stores each turn in Mem0 and retrieves it before the recall question.

## Gotchas

- The `chroma_db/` directory is reset at the start of each run to avoid stale-memory contamination.
- mem0 logs chroma/spaCy startup warnings to **stderr**; `2>/dev/null` gives a clean run for recording.
- The run streams per-lane progress to stdout. It printed nothing but the final table before, which left a terminal capture with ~35s of dead air.
- `mistral` is used as Mem0's internal fact-extraction LLM as well as the demo agent LLM; extraction quality is part of the measurement.
- If Ollama is running on a non-default host/port, set `OLLAMA_HOST` (e.g. `OLLAMA_HOST=http://127.0.0.1:11435 uv run main.py`); both the direct Ollama client and the Mem0 Ollama provider read this environment variable.
- If `ollama` returns a `MTLCompilerService` / `failed to initialize Metal library` error, the Ollama server needs to be restarted (this was hit during verification and was resolved by starting a fresh `ollama serve` process).
