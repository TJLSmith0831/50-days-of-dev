# Day 09 — Cached Weather MCP — AGENTS.md

MCP server with in-memory TTL caching for weather API responses, demonstrating cache-hit vs cache-miss latency differences with Open-Meteo.

## Stack

TypeScript · MCP SDK · Open-Meteo API (no auth required)

## Commands (verified 2026-07-20)

```bash
pnpm install
pnpm start                    # run MCP server
pnpm demo                     # run cache performance demo
```

## Concept

Build an MCP server that caches weather API responses with a 10-minute TTL. The measurable outcome is a clear latency comparison: cache misses show full API round-trip time, cache hits show in-memory retrieval speed. Demo calls the same location twice to prove the speedup.

## Gotchas

- `package.json` needs `"private": true` and a `start` script for `pnpm start`.
- Add to root `pnpm-workspace.yaml` only after a `package.json` exists.
- Cache is in-memory only — does not survive server restarts.
- Location normalization is trim + lowercase only — no alias resolution ("SF" ≠ "san francisco").
