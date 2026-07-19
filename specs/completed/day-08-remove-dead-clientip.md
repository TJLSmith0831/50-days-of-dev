<!-- Status: Completed 2026-07-19 -->
# Spec: Day-08 Remove Dead `clientIp` Parameter

## Problem
`createServerInstance(clientIp?, apiKey?)` in `src/index.ts:9` accepts `clientIp`, threads it through both tool handlers into `searchSources` and `fetchDocs`, where both functions accept it as a parameter and then never use it. `main()` calls `createServerInstance()` with no arguments anyway.

## Goal
Delete the dead parameter at every layer.

## File changes
- `src/index.ts` — remove `clientIp?` from `createServerInstance` signature and both `searchSources`/`fetchDocs` call sites
- `src/lib/api.ts` — remove `clientIp?: string` from both function signatures

## Success criterion
Zero references to `clientIp` in the codebase. TypeScript compiles clean.

## Out of scope
- Adding real rate-limiting (that would re-introduce the parameter with an implementation)
