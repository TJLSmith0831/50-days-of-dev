# Docs MCP — Demo Brief

**Hook:** A two-tool MCP server that gives Claude Code the ability to search and retrieve docs from any directory — resolve a query to source IDs, fetch content by ID.

---

## What it proves

1. **MCP tool registration works** — Claude Code discovers `resolve-docs-source` and `get-docs-content` automatically once the server is registered.
2. **An agent uses the two-tool pattern autonomously** — it resolves sources first, picks the right one, then fetches — without being told to chain the calls.

---

## What is MCP? (10–15s definition beat)

> "The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to LLMs… MCP provides a standardized way to connect AI models to different data sources and tools."
>
> — [modelcontextprotocol.io/introduction](https://modelcontextprotocol.io/introduction)

Plain English:

- AI models are isolated by default. They can't read your files, call your APIs, or search your docs unless someone hardcodes that connection.
- MCP removes the hardcoding. You build one server, expose your tools and data, and any client that speaks the protocol can use them.
- Think USB-C: one plug, every device. The "devices" here are AI agents; the "plug" is MCP.
- Build it once. Claude Code, Cursor, any MCP client picks it up — no custom glue per integration.

**Sources:**
- Model Context Protocol Introduction: https://modelcontextprotocol.io/introduction
- MCP Specification: https://spec.modelcontextprotocol.io/

---

## Setup

```bash
cd day-08-docs-mcp
pnpm build                                          # compile to dist/

# Register with Claude Code (persists across sessions)
claude mcp add docs-mcp node $(pwd)/dist/index.js

# Confirm it's wired
claude mcp list
```

`DOCS_DIR` defaults to the repo root. Override with `DOCS_DIR=/path/to/dir` in the `claude mcp add` env flags if needed.

---

## Pre-recording workflow

**Step 1 — Test inputs without recording.**

Verify the demo scenario end-to-end before touching a recorder:

1. Start a Claude Code session in the repo root.
2. Type the demo prompt manually.
3. Confirm `resolve-docs-source` fires, picks a source, then `get-docs-content` fires and returns content.
4. If either tool call is missing or returns an error — **stop and do not record**. Diagnose the failure (build stale, MCP not registered, source walk returning zero results) and resolve it first.

Check that the `.exp` script and any supporting assets do not allow the same prompt to be submitted twice in one session. The demo should read as a human using Claude Code for the first time — one question, two tool calls, one grounded answer.

**Step 2 — Record the terminal demo.**

Once Step 1 passes cleanly on a dry run, start recording.

**Step 3 — Create the Remotion video.**

Composite the MCP definition animated intro with the terminal recording.

---

## Demo scenario

Type this into Claude Code:

> "Use the docs MCP to find what this repo says about model routing, then summarize it."

This forces both tool calls. Claude Code cannot answer from training data — it has to resolve sources and fetch content. If it attempts to answer without calling the tools, add: *"You must use the resolve-docs-source and get-docs-content tools."*

---

## Shot list (~40–50s)

### Remotion intro (10–15s)
1. **MCP definition (10–15s):** animated text or diagram. Show the client-server model: Claude Code (client) ↔ MCP server ↔ local docs / GitHub / npm. Caption pulls from the modelcontextprotocol.io quote above. Cite the source on screen.

### Terminal demo (30–35s)
2. **MCP registered (5s):** `claude mcp list` output showing `docs-mcp` entry. Caption: *one registration, any MCP client.*
3. **Prompt typed (5s):** demo question entered into Claude Code TUI.
4. **`resolve-docs-source` fires (10s):** tool call block visible, ranked source list returned. Caption: *step 1 — find the right source.*
5. **`get-docs-content` fires (10s):** tool call block visible with the chosen source ID, Markdown excerpt returned. Caption: *step 2 — fetch the content.*
6. **Grounded answer (10s):** Claude Code's summary, grounded in the returned docs. Caption: *two tool calls, one grounded answer.*

---

## What NOT to demo

- `pnpm demo` — hides the agent layer; the whole point is Claude Code using the tools.
- GitHub or web source types — network variance on camera.
- A prompt Claude Code can answer from training data without calling the tools (it'll skip them).

---

## Frame

- Claude Code TUI fullscreen, dark theme.
- The tool call blocks are the visual — let each one finish rendering before cutting.
- End on the grounded answer held for 1–2s.

---

## Checks before recording

- `pnpm test --run` — 17 tests green
- `claude mcp list` — `docs-mcp` present
- Dry run of the demo prompt — both tools fire, content returned
