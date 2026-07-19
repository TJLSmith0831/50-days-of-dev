# Day 08 — Docs MCP

A minimal MCP server that exposes local project documentation (Markdown files) as a searchable resource/tool, with a round-trip client call proving it works.

## Outcome
An MCP client can ask the Docs MCP server for a topic and get back a relevant docs chunk from any of five sources:

| `sourceType` | Search backend | Fetch backend | Notes |
| --- | --- | --- | --- |
| `github` (default) | `octokit` repo search | README + recursive `docs/**/*.md` walk (depth 3, 20-file cap) | `GITHUB_TOKEN` optional |
| `local`  | walk `DOCS_DIR` for `*.md` (depth 6) | `fs.readFile` | filename hit ranks 0.9, miss 0.1 |
| `npm`    | `registry.npmjs.org/-/v1/search` | registry metadata + unpkg `README.md` fallback | fallback because modern packages drop README from registry |
| `pypi`   | `pypi.org/pypi/{q}/json` (exact package name — no free JSON search API) | same JSON endpoint's `description` field | returns `[]` on 404 |
| `web`    | DuckDuckGo Instant Answer API | `fetch()` + a stdlib HTML-strip regex | no key required |

## Stack
TypeScript · MCP SDK

## Commands
```bash
cd day-08-docs-mcp
pnpm install
pnpm start           # run the MCP server on stdio
pnpm demo            # spawn the server + run the round-trip client
pnpm test --run      # vitest suite
```

## Environment
- `DOCS_DIR` — directory the `local` source type walks for `*.md` files. Defaults to the repo root (`../..` from `src/lib/api.ts`).
- `GITHUB_TOKEN` — optional, raises GitHub's unauthenticated rate limits for the `github` source type.
- `DEMO_QUERY`, `DEMO_TOPIC`, `DEMO_SOURCE_TYPE` — override the demo client's hardcoded query.

## Live round-trip demos (verified 2026-07-19)

```bash
# GitHub
DEMO_SOURCE_TYPE=github DEMO_QUERY="modelcontextprotocol typescript-sdk" DEMO_TOPIC=installation pnpm demo

# npm
DEMO_SOURCE_TYPE=npm    DEMO_QUERY=zod                                 DEMO_TOPIC=installation pnpm demo

# PyPI
DEMO_SOURCE_TYPE=pypi   DEMO_QUERY=requests                             DEMO_TOPIC=usage        pnpm demo

# Web search
DEMO_SOURCE_TYPE=web    DEMO_QUERY="model context protocol"             DEMO_TOPIC=protocol     pnpm demo

# Local (repo docs)
DOCS_DIR="$PWD/.." DEMO_SOURCE_TYPE=local DEMO_QUERY=armadillo DEMO_TOPIC=usage pnpm demo
```

## Plan
1. Scaffold a TypeScript MCP server.
2. Expose a `docs` tool/resource that reads Markdown from a configured directory.
3. Run a simple MCP client that calls it and prints the returned docs chunk.

## Structure

```
doc-research-mcp/
├── src/
│   ├── index.ts              # Entry point, CLI parsing, transport selection
│   ├── lib/
│   │   └── api.ts            # API client layer (searchSources, fetchDocs)
│   └── types.ts             # TypeScript types
├── package.json
└── tsconfig.json
```
