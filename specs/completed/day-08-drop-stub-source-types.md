<!-- Status: Superseded 2026-07-19 — the enum was narrowed to ["github","local"], then re-widened to ["github","local","npm","pypi","web"] once real implementations landed. Stubs are no longer stubs. -->
# Spec: Day-08 Drop Stub Source Types

## Problem
The `sourceType` enum in both the Zod schema (`src/index.ts:32`) and `types.ts` advertises `"npm"`, `"pypi"`, `"official-docs"`, and `"web-scrape"`. None are implemented. Passing any of them to `searchSources` silently returns `[]`, and the tool responds "No documentation sources found" — no indication that the type is unimplemented.

## Goal
Remove the fiction. The tool should only advertise what it does.

## Option A (preferred for MVP): Shrink the enum
Remove unimplemented values from the Zod schema and the `SourceResult.type` / `SearchOptions.sourceType` unions in `types.ts`. Keep only `"github"` (and `"local"` once that spec is implemented).

## Option B (if stubs are intentional scaffolding): Explicit not-implemented error
In `searchSources`, replace the silent `return []` with:
```ts
throw new Error(`Source type "${options.sourceType}" is not yet implemented. Supported: github`)
```

## File changes (Option A)
- `src/index.ts` — enum on line ~32: `z.enum(["github"])` (or `["github", "local"]`)
- `src/types.ts` — narrow the union types accordingly

## Success criterion
A caller passing `sourceType: "npm"` gets a schema validation error from Zod (not a silent empty result), or the type is not offered at all.

## Out of scope
- Actually implementing npm/pypi/web-scrape
