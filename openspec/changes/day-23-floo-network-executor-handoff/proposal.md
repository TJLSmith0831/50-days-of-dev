## Why

`day-23-floo-network-core` established durable project/thread/session state and a spec/go mode toggle with no process behind it. This change makes that toggle real: detecting and driving the actual `claude`/`codex` executor, and building the `/go` handoff that lets a spec-mode conversation become a live, write-enabled coding session without losing context.

## What Changes

- Detect `claude`/`codex` on PATH at app startup (prefer `claude` if both present, warn and stay chat-only if neither).
- Run a one-time-per-session preflight check (grill-apply skill installed, `openspec` on PATH, Ponytail installed) and surface its status persistently in the UI; re-check on `/go` if stale.
- Spawn and manage the executor process per its own architecture: Claude as one persistent stdin-stream process (`--print --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>`); Codex as a fresh `codex exec resume --last "<msg>" --json --sandbox <mode>` invocation per turn.
- Implement `/go`: idle-only gating, terminate the spec-mode executor, spawn a fresh go-mode executor via `--resume <session-id> --permission-mode acceptEdits` (Claude) / `--sandbox workspace-write` (Codex) with history carried forward — no summarization call.
- Implement `/propose`: invoke `grill-propose` as a skill in the running spec-mode executor; on success, record the resulting OpenSpec change name in the thread's `.meta.json` (`openSpecChangeName`).
- Once live, make the chat pane a thin pass-through to the executor process, rendering its structured events (text, reasoning, file edits as diffs, tool calls) as distinct UI elements via a shared internal event type.
- Handle unexpected executor exit: banner in the chat pane, thread mode reverts to `spec`, history preserved.
- Switching back to spec-mode terminates the live executor (no backgrounding); a later `/go` always starts fresh.

## Capabilities

### New Capabilities

- `executor-detection`: find `claude`/`codex` on PATH, preference and fallback rules, feeds the preflight check.
- `executor-process-management`: spawn/terminate/parse-events for each executor's distinct process architecture (Claude persistent stdin-stream vs. Codex per-turn `resume`), plus crash detection.
- `mode-handoff`: `/go` trigger (command + button), idle-only gating, terminate+respawn with carried-forward history, switch-back-to-spec-mode termination.
- `openspec-change-linking`: `/propose` triggers `grill-propose` in-executor and records the resulting change name on the thread.

### Modified Capabilities

None. `mode-selection` (from `day-23-floo-network-core`) is not modified — its write path (persisting `currentMode` + JSONL marker) is untouched. The behavior of *acting* on a switch to `go` mode is new behavior owned entirely by this change's own `mode-handoff` capability, not a change to `mode-selection`'s existing requirements. (Also: `day-23-floo-network-core` has not yet been applied/archived, so `mode-selection` doesn't exist in `openspec/specs/` yet to modify against.)

## Impact

- New Rust process-management code: two executor adapters (Claude persistent-process, Codex per-turn), a shared internal event enum, and per-executor event parsers.
- New on-disk state: `~/.floo-network/harness.log` gains crash/preflight entries (log file itself already introduced by change 1).
- New per-machine setup dependency surface this change assumes but doesn't install: `grill-apply` skill (`~/.claude/skills/` for Claude, `~/.agents/skills/` for Codex), `openspec` on PATH, Ponytail plugin — all checked, none installed by the harness.
- Test fixtures gain a fake-executor stub script for integration testing (D15 tier 2), avoiding real API cost in tests.
- No Graphify or Browserbase calls (change 3). No distribution/packaging (change 4).
