## Context

This change is the third of four sequential OpenSpec changes for Floo Network. It adds two independent external integrations — Browserbase web search and Graphify code mapping — on top of change 1's project/thread/session model and change 2's executor handoff. Neither integration touches the executor's own tool loop (per D6, the harness can't hook into it); both instead inject results into the conversation as ordinary `role: "tool"` messages, reusing the same mechanism change 2 already established for `/go` and `/propose` payloads.

## Goals / Non-Goals

**Goals:**
- Let the user trigger a web search from chat and have citation-backed results reach the executor's context automatically.
- Let the user run Graphify against the active project and browse its output in a dedicated results pane.
- Auto-inject a bounded Graphify report summary into the thread so the executor stays aware of the codebase map without manual copy-paste.

**Non-Goals:**
- No executor-initiated tool calls to either service (no MCP integration) — both are harness-triggered only.
- No fetching/rendering of raw page content from search results (Browserbase's Fetch endpoint) — search returns citations only, per D9.
- No embedding Graphify — it always runs as a separate shelled-out process, per the existing "Graphify runs in its own process" constraint.
- No distribution/packaging (change 4).

## Decisions

**Injection mechanism: `role: "tool"` message via the existing JSONL append path, not a new context channel.** Both `/search`'s citation list and Graphify's report summary are appended to the thread using change 1's `session-storage` capability exactly as-is — no new message type, no new storage format, no new executor-facing protocol. The next turn sent to the executor (via change 2's process-management) naturally includes them as part of conversation history.

**Browserbase: harness-side REST call, no SDK.** No official Rust SDK exists (per D9), so this is a raw HTTP client call with the `x-bb-api-key` header. Citation formatting happens harness-side before injection — the executor never sees a raw JSON response body, only the pre-formatted `[n] Title / URL / Published` list.

**Graphify: shell-out with disk-based output parsing.** `graphify extract <project-dir> --out <out-dir> --no-viz --code-only` is invoked as a child process; the harness reads `graph.json` and `GRAPH_REPORT.md` from `<out-dir>` after the process exits successfully, rather than parsing stdout (per D8, stdout is progress/cost text, not the machine-readable artifact).

**Report-summary injection: first 4000 characters, with a pointer to the full report.** The injected `role: "tool"` message includes a note that the complete `GRAPH_REPORT.md` and explorable `graph.json` are available in the results pane, so truncation doesn't silently hide detail — it just keeps a single run from dominating the thread's context window.

**Build order: `web-search` before `graphify-integration`.** Browserbase's REST shape is small and fully verified (per D9); Graphify's shell-out surface has more unknowns (unverified full flag list, disk-based rather than typed output). Proving the injection-as-message pattern against the simpler, better-understood integration first de-risks reusing it for the messier one.

## Risks / Trade-offs

- **[Risk] Auto-injecting a Graphify summary after every run could flood a thread's context if the user re-runs Graphify frequently → [Mitigation]** Accepted for v1 given the 4000-char bound per run; revisit only if this proves disruptive in practice (e.g. add a user toggle to disable auto-injection).
- **[Risk] Graphify's full `extract` flag surface wasn't exhaustively verified (per D8's own open note) → [Mitigation]** The invocation used here (`--out --no-viz --code-only`) is the specific, verified safe subset; expanding to other flags (deep mode, incremental) should re-confirm behavior with `graphify extract --help` before wiring up those UI toggles.
- **[Risk] No official Rust SDK for Browserbase means hand-rolled HTTP error handling (429/503/etc. per D9) → [Mitigation]** Implement the documented exponential-backoff recommendation for 429/503 directly; the API's low realistic call volume for a personal harness (1,000/month free tier) makes this a low-frequency concern.
