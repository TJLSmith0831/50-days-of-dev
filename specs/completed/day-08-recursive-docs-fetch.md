<!-- Status: Completed 2026-07-19 -->
# Spec: Day-08 Recursive `docs/` Fetch

## Problem
`fetchDocs` in `src/lib/api.ts:92-130` fetches `docs/*.md` at one level only. Repos that nest docs under subdirectories (e.g. `docs/api/`, `docs/guides/`) have their content silently skipped.

## Goal
Walk the `docs/` tree recursively and collect all `*.md` files.

## Logic
Replace the flat `docsData.filter(entry => entry.type === "file")` block with a recursive helper:
```ts
async function collectMarkdown(owner, repo, path, octokit): Promise<string[]>
  data = octokit.rest.repos.getContent({ owner, repo, path })
  for each entry:
    if entry.type === "file" && entry.name.endsWith(".md") → fetch and collect
    if entry.type === "dir" → recurse into collectMarkdown(owner, repo, entry.path, octokit)
```

## Constraints
- Depth limit: 3 levels max to avoid runaway API calls on pathological repos
- Per-file errors should be caught and skipped (same as current behavior)
- Total files fetched: cap at 20 to stay within rate limits

## File changes
- `src/lib/api.ts` — extract recursive helper, call it from `fetchDocs`

## Success criterion
`get-docs-content` on a repo with `docs/api/auth.md` returns that file's content alongside the root `docs/*.md` files.

## Out of scope
- Configurable depth or file count limits (hardcode for now)
- Non-docs directories
