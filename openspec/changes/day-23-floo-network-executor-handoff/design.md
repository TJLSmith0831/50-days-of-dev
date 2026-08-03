## Context

This change is the second of four sequential OpenSpec changes for Floo Network, building directly on `day-23-floo-network-core`'s project/thread/session data model and inert mode-selection toggle. It makes go-mode real: detecting an installed coding-agent executor (`claude` or `codex`), spawning and driving it per its own distinct process architecture, and implementing the `/go` handoff that carries a spec-mode conversation into a live, write-enabled session.

Claude and Codex are architecturally different at the process level (D11): Claude supports one persistent process fed newline-delimited JSON over stdin with `--resume` for history carry-forward; Codex has no persistent-process mode — every turn after the first is a fresh `codex exec resume --last` invocation. This is treated as a genuine fork in the Rust process layer, not something to abstract behind one shared interface prematurely.

## Goals / Non-Goals

**Goals:**
- Detect `claude`/`codex` on PATH and surface a persistent, cached handoff-readiness status.
- Spawn, drive, and cleanly terminate both executor architectures.
- Implement `/go` (idle-gated, terminate+respawn with history carried forward) and `/propose` (skill invocation + change-name recording).
- Render executor-emitted events (text, reasoning, file edits, tool calls) as distinct UI elements in the chat pane once in pass-through mode.
- Detect and gracefully surface unexpected executor exit without losing conversation history.

**Non-Goals:**
- No Graphify or Browserbase integration (change 3).
- No code signing, auto-update, or installer (change 4).
- No changes to `mode-selection`'s existing write path from `day-23-floo-network-core` — this change only adds new behavior that *reacts* to a mode switch, via its own `mode-handoff` capability.
- No attempt to intercept individual tool calls inside either executor's own loop (per D6 — architecturally not possible with a full executor CLI).

## Decisions

**Executor detection: library-based PATH lookup, no shell invocation.** A `which`-crate-style cross-platform lookup for `claude` and `codex` binaries, run once at app startup as part of the preflight check, cached, and re-checked only if stale at actual `/go` time. Rejected checking on every `/go`: adds a synchronous delay to every handoff for a condition (uninstalled dependency) that essentially never changes mid-session.

**Two separate Rust executor adapters, not one shared abstraction.** Claude's adapter owns one persistent child process, writing ndjson to its stdin and reading streamed `stream-json` events from its stdout. Codex's adapter has no persistent process — each turn spawns `codex exec resume --last "<msg>" --json --sandbox <mode>` fresh and reads its JSONL output to completion. Both map their respective event schemas into one shared `ExecutorEvent` enum (`Text`, `Reasoning`, `FileEdit { path, diff }`, `ToolCall { command, output, exit_code }`, `Done`, `Crashed { exit_code }`) that the frontend consumes uniformly via a Tauri event channel — the fork stays contained to the two adapters and their parsers.

**Crash handling: detect, banner, revert to spec-mode, preserve history.** Either adapter emits `ExecutorEvent::Crashed` on unexpected process exit (non-zero code or stdout close without a clean `Done`). The harness shows an inline chat-pane banner, sets the thread's `currentMode` back to `spec` in `.meta.json`, and leaves the JSONL log untouched. Rejected silent auto-restart: if the crash was triggered by something in the conversation content itself, silent restart would crash-loop; surfacing it keeps the user in control and costs nothing since history is never at risk (append-only storage).

**Fake-executor test fixture: one configurable stub, not two.** A small script simulating both executors' invocation shapes (reads stdin for Claude-style, accepts CLI args for Codex-style), toggleable via env var/arg to either emit a canned successful event sequence or exit non-zero immediately. Used for D15 tier-2 integration tests covering process lifecycle, mode switching, history carry-forward, and the crash path above — without spawning a real `claude`/`codex` process or incurring API cost in tests.

**Build order: Claude's persistent-process adapter before Codex's per-turn adapter.** Claude's architecture (long-lived process, streamed ndjson parsing, `--resume` across permission-mode changes) is the harder, riskier unknown for this codebase; proving it out first against the fake-executor stub de-risks Codex's comparatively simpler per-turn request/response model built afterward.

## Risks / Trade-offs

- **[Risk] The two-executor architectural fork means every future behavior (crash handling, event parsing, history carry-forward) needs to be implemented and tested twice → [Mitigation]** Accepted as inherent to the underlying tools being genuinely different (D11), not a design choice this change could avoid; the shared `ExecutorEvent` enum contains the fork to the adapter layer so downstream UI/rendering code is written once.
- **[Risk] Codex's per-turn `resume --last` model has no persistent process to detect a "live" crash from between turns — a broken Codex install might only surface as a failure on the next turn, not immediately → [Mitigation]** Acceptable for v1; each `codex exec resume` invocation's own exit code still triggers the same `Crashed` event path when it fails, just one turn later than Claude's immediate detection.
- **[Risk] Caching the preflight/detection result at startup means a mid-session `pnpm i -g @openai/codex` uninstall goes undetected until the next `/go`'s staleness check → [Mitigation]** Accepted; this is a rare manual action mid-session, and the re-check-on-`/go`-if-stale behavior (E3) already catches it before an actual handoff is attempted.
