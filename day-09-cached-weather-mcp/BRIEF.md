# Cached Weather MCP — Demo Brief

**Hook:** When an agent calls the same MCP tool twice, the second call should be 1000x faster. Not because the agent is smart — because the tool server is.

---

## What it proves

1. **Transparent caching at the tool layer** — the MCP server caches weather API responses with a 10-minute TTL. The agent doesn't know about the cache. It just calls `get_weather("Paris")` and gets a response with `"cached": false` → `"cached": true` and timing data in the payload.
2. **Measurable performance** — the tool response includes `responseTimeMs`. Cache miss: ~1100ms (geocoding + forecast API round-trip). Cache hit: ~1ms (in-memory Map lookup). The speedup is visible right in Claude Code's tool output block.
3. **Location-keyed cache** — a different location is still a miss. The cache is keyed by normalized location string (trim + lowercase), not just "second call = fast."

---

## Why this matters (the employer story)

This isn't "I know how to cache." It's "I design agent infrastructure that makes agents faster without changing them."

- **MCP integration** — the server speaks the Model Context Protocol; any MCP client (Claude Code, Cursor, custom agents) can use it.
- **Server-side caching strategy** — TTL-based in-memory cache, keyed by normalized input, transparent to the caller.
- **Performance engineering** — measurable latency difference, not theoretical. The numbers are in the response payload.
- **Agent-aware design** — the agent doesn't need to be taught about caching. The tool server handles it. That's the point of infrastructure: it works so the consumer doesn't have to think about it.

---

## Setup

```bash
cd day-09-cached-weather-mcp
pnpm install
pnpm build

# Register with Claude Code (persists across sessions)
claude mcp add cached-weather node /Users/tjlsmith0831/Desktop/Programming/50-days-of-dev/day-09-cached-weather-mcp/dist/src/index.js

# Confirm it's wired
claude mcp list
```

---

## Pre-recording workflow

**Step 1 — Test inputs without recording.**

1. Start a Claude Code session in the repo root.
2. Type the demo prompt (below) manually.
3. Confirm `get_weather` fires twice for the same location, and the `cached` flag flips from `false` to `true`.
4. Verify `responseTimeMs` is visible in both tool response blocks.
5. If the agent refuses to call the tool twice (says "I already have that"), add the explicit instruction: *"You must use the get_weather tool for both requests."*
6. If either tool call is missing or returns an error — **stop and do not record**. Diagnose first.

**Step 2 — Record the terminal demo live.**

The agent is non-deterministic. Do not expect specific items — exact wording, number of tool calls, or response format may vary between runs. The process is:

1. Start recording the terminal.
2. Run `claude mcp list` to show the server is registered.
3. Type the demo prompt into Claude Code.
4. Let the agent run — do not script or predict what it will do.
5. Stop recording once the agent has finished responding.
6. Adapt the video timing in post based on what actually happened — trim dead space, hold on key tool output blocks, adjust caption timing to match the real response.

**Step 3 — Create the Remotion video.**

Composite the animated intro with the terminal recording. Adapt the shot list timing to match the actual recording — the timings below are targets, not guarantees.

---

## Demo scenario

Type this into Claude Code:

> "Use the get_weather tool to check the current weather in Paris. Then use the get_weather tool to check Paris again — I want to compare the response times."

This forces two tool calls to the same location. The agent cannot answer from training data — it has to call the tool. The tool response includes `cached` and `responseTimeMs`, so the viewer sees the difference in the tool output blocks.

If the agent tries to skip the second call, add: *"You must call get_weather for both requests, even though the location is the same."*

---

## Shot list (~40–50s)

### Remotion intro (10–15s)
1. **Caching concept (10–15s):** animated diagram showing the flow: Agent (blue) → MCP Server (green) → Cache layer. On first call: cache miss → arrow to Open-Meteo API (yellow) → ~1100ms. On second call: cache hit → arrow back from memory → ~1ms. Caption: *transparent caching at the tool layer, invisible to the agent.*

### Terminal demo (30–35s)
2. **MCP registered (5s):** `claude mcp list` output showing `cached-weather` entry. Caption: *one registration, any MCP client.*
3. **Prompt typed (5s):** demo question entered into Claude Code TUI. Caption: *the agent doesn't know about the cache.*
4. **First `get_weather` fires (10s):** tool call block visible, response shows `"cached": false, "responseTimeMs": ~1100`. Caption: *cache miss — full API round-trip.*
5. **Second `get_weather` fires (10s):** tool call block visible, response shows `"cached": true, "responseTimeMs": ~1`. Caption: *cache hit — in-memory lookup, 1000x faster.*
6. **Agent's summary (5s):** Claude Code's answer, noting both calls returned the same data. Caption: *same answer, 1000x faster the second time.*

---

## What NOT to demo

- `pnpm demo` — hides the agent layer; the whole point is Claude Code calling the tool and seeing the cached flag in the response.
- TTL expiry — would require waiting 10 minutes on camera. Mention it in the post text, don't show it.
- The test suite — unit tests aren't the story here.
- A different location as a third call — adds time without adding clarity. Mention "location-keyed" in the post text instead.

---

## Frame

- Claude Code TUI fullscreen, dark theme.
- The tool call blocks are the visual — let each one finish rendering before cutting.
- The `cached` and `responseTimeMs` fields are the punchline. Make sure they're legible.
- End on the agent's summary held for 1–2s.

---

## LinkedIn post draft

> When an agent calls the same tool twice, the second call should be 1000x faster.
>
> Not because the agent is smart — because the tool server is.
>
> Built an MCP server that caches weather API responses with a 10-minute TTL. The agent doesn't know about the cache. It just calls `get_weather("Paris")` and gets the response back with `cached: false` (1100ms) → `cached: true` (0.9ms).
>
> Transparent caching at the tool layer. The agent doesn't change behavior. The infrastructure does the work.
>
> Day 9 of 50 — MCP caching. #AIEngineering #MCP #AgentInfrastructure

---

## Checks before recording

- `pnpm test --run` — all tests green
- `claude mcp list` — `cached-weather` present
- Dry run of the demo prompt — both tool calls fire, `cached` flag flips, `responseTimeMs` visible
