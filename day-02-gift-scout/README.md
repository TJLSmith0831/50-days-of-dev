# Day 2 — Gift Scout

An AI shopping intern you manage: hand it a recipient profile, it drafts gift
directions, you approve or redirect them, it goes shopping with real tools,
and if it crashes mid-errand it resumes without redoing work.

## Stack
Python · LangGraph (`StateGraph`, `SqliteSaver`, `interrupt`/`Command`) ·
`langchain-ollama` (local `llama3.2`) · `ddgs` (web search) · `rich` (CLI)

## Commands (not yet run — verify after Step 1)
```
uv sync
uv run main.py
```

## Concept
`brainstorm` drafts gift directions, an `interrupt()` gate lets you approve
or edit them, then an `agent ⇄ ToolNode` loop picks between `web_search`
(gather candidates) and `add_to_shortlist` (commit a good find) until it has
three, and `rank` picks the top 3 with a why-it-fits note and an
over-budget flag. Every step is checkpointed to `gift_scout.db` via
`SqliteSaver`, so a hard-kill mid-run resumes at the last completed node
instead of restarting.

## Build path
- **Step 1 (this scaffold):** stub nodes, real graph wiring, real
  `SqliteSaver`. Exit: `Ctrl-C` mid-`agent` loop, rerun, `brainstorm`
  doesn't re-run.
- **Step 2:** real `brainstorm` (local `llama3.2`), real `web_search` /
  `add_to_shortlist` tool bodies, `bind_tools` + `tools_condition` loop.
- **Step 3:** `rich` intern personality, edit-the-plan at the approval
  gate, live tool-call prints, resume-skip prints.

## Gotchas
- Not `MemorySaver` — it won't survive a kill. `SqliteSaver` only.
- Node is the atomic unit — kill *between* nodes to see partial progress.
- Small local models are shaky at tool-calling — 2 simple schemas, cap the
  loop at `MAX_TOOL_CALLS`, let `rank` handle a thin shortlist.
- `web_search` must be wrapped in try/except from the moment it's real;
  cache finished candidates into state so resume never re-hits the network.
- The `interrupt()` / `Command(resume=...)` call in `approval_gate` is
  unverified against the installed `langgraph` version — signatures drifted
  across 0.2 → 0.3+. Confirm before building on top of it.
