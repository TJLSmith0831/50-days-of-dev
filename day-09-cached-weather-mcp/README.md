# Day 9 — Cached Weather MCP

An MCP (Model Context Protocol) server with in-memory TTL caching for weather API responses, demonstrating cache-hit vs cache-miss latency differences.

## Overview

When an agent calls the same tool twice, the second call should be 1000x faster. Not because the agent is smart — because the tool server is.

This MCP server caches weather API responses with a 10-minute TTL. The agent doesn't know about the cache. It just calls `get_weather("Paris")` and gets the response back with `cached: false` (1100ms) → `cached: true` (0.9ms).

## Features

- **Transparent caching** — 10-minute TTL cache for weather API responses, invisible to the calling agent
- **Measurable performance** — Tool responses include `cached` flag and `responseTimeMs` for direct comparison
- **Location-keyed cache** — Cache keyed by normalized location string (trim + lowercase)
- **MCP-compliant** — Works with any MCP client (Claude Code, Cursor, custom agents)

## Stack

- TypeScript
- MCP SDK (@modelcontextprotocol/server)
- Open-Meteo API (no authentication required)

## Setup

```bash
cd day-09-cached-weather-mcp
pnpm install
pnpm build
```

## Usage

### Run the MCP server

```bash
pnpm start
```

### Run the cache performance demo

```bash
pnpm demo
```

This calls the same location twice to demonstrate the latency difference between cache miss and cache hit.

### Register with Claude Code

```bash
claude mcp add cached-weather node /Users/tjlsmith0831/Desktop/Programming/50-days-of-dev/day-09-cached-weather-mcp/dist/src/index.js
claude mcp list
```

## Technical Details

### Cache Behavior

- **TTL**: 10 minutes (600,000 ms) for all weather data
- **Storage**: In-memory Map (does not survive server restarts)
- **Key**: Normalized location string (trimmed + lowercase)
- **Scope**: Raw API responses only; MCP formatting happens after cache retrieval

### Tool Response Format

```json
{
  "location": "paris",
  "current": { ... },
  "forecast": [ ... ],
  "cached": false,
  "responseTimeMs": 1100
}
```

- `cached`: `false` for cache miss (fresh API call), `true` for cache hit
- `responseTimeMs`: Latency in milliseconds (~1100ms for miss, ~1ms for hit)

### Location Normalization

- Trims whitespace and converts to lowercase
- No alias resolution ("SF" ≠ "san francisco")
- Example: " San Francisco " → "san francisco"

## Testing

```bash
pnpm test
```

## Gotchas

- `package.json` requires `"private": true` and a `start` script for `pnpm start`
- Add to root `pnpm-workspace.yaml` only after `package.json` exists
- Cache is in-memory only — does not survive server restarts
- Location normalization is trim + lowercase only — no alias resolution

## Demo Scenario

In Claude Code, type:

> "Use the get_weather tool to check the current weather in Paris. Then use the get_weather tool to check Paris again — I want to compare the response times."

The agent will call the tool twice. The first call shows `cached: false` with ~1100ms latency. The second call shows `cached: true` with ~1ms latency — a 1000x speedup.

## Status

✅ Complete — MCP server with caching, demo script, and tests
