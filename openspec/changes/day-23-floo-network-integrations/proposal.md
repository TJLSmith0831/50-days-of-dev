## Why

Floo Network's spec-mode is meant to support codebase understanding (Graphify code maps) alongside the grill-explore/grill-propose workflow already wired up in change 2. This change adds that, giving the executor codebase-map summaries as first-class context.

Web search was originally in this change's scope (a Browserbase `/search` integration) and has been **dropped** — see I5. Both executors have web search built in, so a harness-side search integration would only duplicate a tool the executor already reaches for on its own.

## What Changes

- Add a Graphify results pane: target-scope picker, run/re-run with incremental/deep-mode toggles, rendered `GRAPH_REPORT.md` and explorable `graph.json`, and a query surface (`graphify query/path/explain`).
- After each successful Graphify run, auto-inject a truncated (4000-char) `GRAPH_REPORT.md` summary into the active thread as a `role: "tool"` message.

## Capabilities

### New Capabilities

- `graphify-integration`: Graphify CLI shell-out, results pane, report-summary injection.

### Removed from this change

- `web-search`: dropped entirely per I5 — no Browserbase integration, no `/search` command, no `BROWSERBASE_API_KEY` handling. The executor's own web search covers the need.

### Modified Capabilities

None.

## Impact

- New Rust process-shell-out code for Graphify (`graphify extract ...`), parsing `graph.json`/`GRAPH_REPORT.md` from disk.
- New frontend: a Graphify results pane (report view, graph summary, query surface).
- Injected results are written as `role: "tool"` messages into existing thread JSONL logs (change 1's `session-storage` capability) — no new storage format.
- No new HTTP client, no network calls, no secrets handling anywhere in this change.
- No modification to executor-process-management (change 2) — injected messages flow through the same "harness writes a message, it's part of what the executor sees next turn" mechanism already used for `/go`/`/propose`.
- Depends on change 1 (project/thread/session model) and change 2 (a live executor to eventually read the injected context) both being built first.
- `graphify` is not installed on this machine and is not published under that name on pip or npm, so this change ships implemented and unit-tested but **not verified against a real Graphify run** (see I6).
