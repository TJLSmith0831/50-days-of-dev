<!-- Status: Completed 2026-07-19 -->
# Spec: Day-08 Local Markdown Source

## Problem
The original concept was "serve this repo's Markdown docs." What was built hits the GitHub API, requires a `GITHUB_TOKEN`, and rate-limits at 10 search reqs/min unauthed. The local-first framing was dropped without reason.

## Goal
Add a `local` source type that reads Markdown from a configured directory on disk, no network required.

## Scope
- New `sourceType` value: `"local"`
- New env var: `DOCS_DIR` (default: `../../` relative to the server, i.e. the repo root)
- `searchSources` for `sourceType === "local"`: walk `DOCS_DIR` for `*.md` files, return each as a `SourceResult` with `id: "local:<relative-path>"`, relevance scored by filename match to query
- `fetchDocs` for `sourceId.startsWith("local:")`: read the file from disk, return its content

## File changes
- `src/lib/api.ts` — add local branch to `searchSources` and `fetchDocs`
- `src/types.ts` — add `"local"` to the `SourceResult.type` union
- `src/index.ts` — add `"local"` to the `sourceType` enum in the tool schema
- `README.md` — document `DOCS_DIR` env var

## Success criterion
`resolve-docs-source` with `sourceType: "local"` and `query: "armadillo"` returns at least one result pointing to a file in the repo. `get-docs-content` on that result returns the file's Markdown.

## Out of scope
- Semantic search / embeddings
- Caching the file listing
- Non-Markdown files
