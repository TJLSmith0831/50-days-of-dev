# Day 1 — Doc Speedrun — AGENTS.md
Interactive Q&A over PDFs/docx via LangChain + local Ollama, persisted FAISS index, streamed answers timed per question.

## Stack
Python · LangChain (langchain-community, langchain-ollama) · FAISS (local, persisted to `.faiss_index/`) · `rich` (CLI) · Ollama local (llama3.2 chat, nomic-embed-text embeddings)

## Commands (verified 2026-07-12)
`uv sync && uv run main.py`

## Concept
REPL over a retrieval chain: `add <path>` loads + chunks + embeds a PDF or docx into a FAISS store that persists across runs; questions stream through a prompt that refuses to answer outside the retrieved context. `nuke` clears the store, `exit` quits and prints a per-question latency table.

## Gotchas
- Store persists at `.faiss_index/` between runs — `nuke`, or delete the dir, to reset.
- `inspect_retrieval()` is a standalone debug helper (prints top-k retrieved chunks per question, no LLM call) — not wired into the REPL; call it directly if retrieval quality needs debugging.
- `allow_dangerous_deserialization=True` on load is safe only because the index is always self-generated locally by this script — never load one from an untrusted source.
