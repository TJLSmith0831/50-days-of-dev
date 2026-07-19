# Day 08 — Docs MCP — AGENTS.md
MCP server that exposes documentation from five backends (github, local, npm, pypi, web) as searchable tools, with a stdio round-trip client for each.

## Stack
TypeScript · MCP SDK · local via Ollama

## Commands (verified 2026-07-19)
```bash
pnpm install
pnpm test --run                # vitest, 24 tests
pnpm demo                      # default: local source
DEMO_SOURCE_TYPE=github DEMO_QUERY=... DEMO_TOPIC=... pnpm demo
DEMO_SOURCE_TYPE=npm    DEMO_QUERY=zod  DEMO_TOPIC=installation pnpm demo
DEMO_SOURCE_TYPE=pypi   DEMO_QUERY=requests pnpm demo
DEMO_SOURCE_TYPE=web    DEMO_QUERY="..." pnpm demo
```

Env: `DOCS_DIR` (local walk root), `GITHUB_TOKEN` (optional, raises unauthed rate limits), `DEMO_*` (override the demo client).

## Source-type gotchas
- **pypi**: no free JSON search endpoint — query is treated as an exact package name; a miss returns `[]`.
- **npm**: modern packages omit `readme` from the registry response; we fall back to `unpkg.com/{pkg}/README.md`.
- **web**: DuckDuckGo Instant Answer returns partial results only (Wikipedia-derived); expect thin coverage vs. a real search API. HTML→text is a stdlib regex, good enough for readable prose.
- **github**: hits public GitHub API — unauthed rate limit is 10 search req/min. Set `GITHUB_TOKEN` for real use.

## Concept
Build the smallest MCP server that serves local Markdown documentation to an MCP client, returning a relevant excerpt for a queried topic. The measurable outcome is a successful round-trip: client asks, server responds with the right docs chunk.

## Gotchas
- `package.json` needs `"private": true` and a `start` script for `pnpm start`.
- Add to root `pnpm-workspace.yaml` only after a `package.json` exists.
