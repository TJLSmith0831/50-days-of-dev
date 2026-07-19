<!-- Status: Completed 2026-07-19 -->
# Spec: Day-08 Round-Trip Demo Client

## Problem
The day's stated deliverable is "a successful round-trip: client asks, server responds with the right docs chunk." No client exists. `pnpm start` runs the server and hangs. The deliverable is unmet.

## Goal
A runnable demo that proves the MCP server works end-to-end.

## Scope
- New file: `src/client.ts`
- New `package.json` script: `"demo": "tsx src/client.ts"`

## Behavior
1. Spawn `node dist/index.js` as a child process (stdio transport).
2. Connect to it using `@modelcontextprotocol/client` + `StdioClientTransport`.
3. Call `resolve-docs-source` with a hardcoded query (e.g. `"modelcontextprotocol sdk"`).
4. Take the first result's `sourceId`.
5. Call `get-docs-content` with that `sourceId` and `topic: "installation"`.
6. Print the returned text to stdout.
7. Disconnect and exit 0.

## Success criterion
`pnpm demo` runs, prints a non-empty docs chunk, exits 0.

## Out of scope
- Error retry logic
- Multiple queries
- Interactive input
