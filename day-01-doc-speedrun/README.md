# Day 1 — Doc Speedrun

Interactive Q&A over PDFs and Word docs, entirely on local models — the document store persists across runs, and every answer is timed.

## Stack
Python · LangChain (`langchain`, `langchain-community`, `langchain-ollama`) · FAISS (persisted locally to `.faiss_index/`) · `rich` (CLI) · Ollama, local (`llama3.2` chat + `nomic-embed-text` embeddings)

## Commands (verified 2026-07-12)
```
uv sync
uv run main.py
```

## Concept
A LangChain retrieval chain wired to a small REPL instead of a fixed question list. `add <path>` loads a PDF or `.docx`, chunks it, embeds it locally, and adds it to a FAISS index saved to disk — so the store survives between runs instead of rebuilding from scratch every time. Ask a question and the answer streams back grounded in the retrieved chunks, refusing to guess ("I don't know based on the provided context") when nothing relevant was retrieved.

## How to use it
1. `uv run main.py`
2. `add <path-to-a-pdf-or-docx>` — repeat for as many documents as you want in the store.
3. Ask a question — it streams the answer in a panel and reports that question's latency.
4. `nuke` clears the store and starts fresh; `exit` quits and prints a per-question latency table for the session.

## Gotchas
- `faiss-cpu` needs no GPU, fine on this machine.
- If Ollama isn't running, `ollama serve` first (or it may already be running as a background service).
- `.faiss_index/` is generated (gitignored) — delete it, or use `nuke`, to reset to an empty store.
- `FAISS.load_local(..., allow_dangerous_deserialization=True)` is safe here because the index is always one generated locally by this same script — never point it at an index from an untrusted source.
