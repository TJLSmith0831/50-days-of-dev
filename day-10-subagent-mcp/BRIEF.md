# Subagent MCP — Demo Brief

**Hook:** Claude Code delegates to bounded local subagents mid-session — an advisor plans, a critiquer watches the actual coding work and writes token-efficiency notes back into the repo's own AGENTS.md/CLAUDE.md, and the second pass visibly improves because of them.

---

## What it proves

1. **Real delegation, not a scripted demo** — Claude Code (the conductor) calls `advise`, `start_session`, and `end_session` as live MCP tool calls mid-conversation, backed by a local Ollama model (`mistral`), while doing a real coding task.
2. **The critique loop closes** — `end_session` doesn't just return text. It writes `critiques/<session_id>.md` (Continue/Avoid) and appends a pointer into the monorepo's `AGENTS.md`/`CLAUDE.md`, so a *future* session — not just this one — inherits the lesson.
3. **The notes change behavior, on camera** — the advisor is consulted twice for the same task: once cold, once fed the critiquer's notes from the first pass. The second plan is visibly different (tighter, avoids the flagged waste), and the second implementation pass reflects it.

---

## Setup

```bash
cd day-10-subagent-mcp

# Register with Claude Code (persists across sessions) — use an absolute path,
# a relative "src/index.py" only resolves if Claude Code's cwd happens to be this folder.
claude mcp add --transport stdio subagent-mcp -- \
  uv run --no-project --with mcp --with ollama --with ddgs python \
  "$(pwd)/src/index.py"

# Confirm it's wired
claude mcp list
```

Ollama must be running locally with `mistral` pulled (`ollama pull mistral`). New MCP servers only load their tool schemas at session start — after `claude mcp add`, start a fresh Claude Code session before the tools (`advise`, `research`, `start_session`, `end_session`) become callable.

---

## Demo scenario

Ask Claude Code, in a session where `subagent-mcp` is connected:

> "Use the subagent-mcp tools to plan and build a simple calculator app in TypeScript in `demo-app/`. Advise first, start a session, build it, then end the session so the critiquer can review, then advise again using its notes and do a quick improvement pass."

This forces the full loop: `advise` → `start_session` → real file writes in `demo-app/` → `end_session` (critiquer writes `critiques/<session_id>.md` + appends to root `AGENTS.md`/`CLAUDE.md`) → a second `advise` call seeded with the critique → a short revision pass.

---

## Shot list (~50–60s)

1. **MCP registered (5s):** `claude mcp list` showing `subagent-mcp` connected. Caption: *one server, three bounded subagents.*
2. **`advise` fires (10s):** tool call block, Approach/Pitfalls/Efficiency guidance for the calculator task. Caption: *local model plans before the frontier model writes a line.*
3. **Real build (10s):** Claude Code writing `demo-app/` files, following the plan. Caption: *the conductor does the work — the subagent only advised.*
4. **`end_session` fires (10s):** critiquer's Continue/Avoid note appears; cut to `critiques/<session_id>.md` on disk. Caption: *the critique isn't a chat message — it's a file.*
5. **AGENTS.md diff (5s):** the appended `## Session critique notes` pointer in the repo's own AGENTS.md. Caption: *the next session inherits this automatically.*
6. **Second `advise` fires (10s):** guidance now shaped by the first critique. Caption: *same tool, sharper answer.*
7. **Revision pass (5–10s):** the follow-up edit informed by the second plan.

---

## What NOT to demo

- `python src/demo.py` — that's a scripted stand-in for when Claude Code isn't the live client; the whole point of this day is Claude Code itself as the MCP client.
- The `research` tool — useful, but a third tool call adds time without adding to the advisor/critiquer story above.
- Ollama cold-start — warm the model (`ollama run mistral` once) before recording.

---

## Frame

- Claude Code TUI fullscreen, dark theme.
- Tool call blocks are the visual — let each finish rendering before cutting.
- Hold on the `critiques/<session_id>.md` file and the AGENTS.md diff; those are the payoff, not the chat text.
- End on the revised calculator code held for 1–2s.

---

## Checks before recording

- `PYTHONPATH=. uv run --no-project --with pytest --with pytest-asyncio --with mcp pytest tests/test_server.py -q` — 4 tests green
- `claude mcp list` — `subagent-mcp` connected
- Ollama running locally with `mistral` pulled
- Dry run of the demo scenario — both `advise` calls, `start_session`, `end_session`, and the critique note all fire without manual intervention
