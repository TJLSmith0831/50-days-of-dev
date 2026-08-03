## 1. Executor detection

- [x] 1.1 Implement PATH lookup for `claude`/`codex` (library-based, no shell) with claude-preferred/neither-found fallback rules
- [x] 1.2 Implement detection caching (once at startup) and staleness re-check triggered by `/go`
- [x] 1.3 `cargo test` unit tests: both present → claude selected, one present → that one selected, neither → chat-only warning

## 2. Fake-executor test fixture

- [x] 2.1 Write the configurable stub script (stdin-reading for Claude-style, arg-based for Codex-style), togglable to emit a canned success sequence or exit non-zero
- [x] 2.2 Verify the stub is invocable both ways (manual smoke test) before relying on it in §3–4's integration tests

## 3. Executor process management — Claude adapter

- [x] 3.1 Implement persistent-process spawn (`--print --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>`, `cwd=<project-root>`)
- [x] 3.2 Implement stdin ndjson writer and stdout `stream-json` reader/parser
- [x] 3.3 Map Claude's `stream-json` events into the shared `ExecutorEvent` enum
- [x] 3.4 Implement crash detection (non-zero exit / stdout close without `Done`) → `ExecutorEvent::Crashed`
- [x] 3.5 Implement `--resume <session-id> --permission-mode <mode>` for history-carried-forward mode switches
- [x] 3.6 Integration tests against the fake-executor stub (§2): normal turn, crash path, resume-with-new-permission-mode

## 4. Executor process management — Codex adapter

- [x] 4.1 Implement first-turn spawn (`codex exec "<prompt>" --json --sandbox <mode> -C <project-root>`)
- [x] 4.2 Implement per-turn `codex exec resume --last "<message>" --json --sandbox <mode>` invocation
- [x] 4.3 Map Codex's `item.started`/`item.completed` events into the shared `ExecutorEvent` enum
- [x] 4.4 Implement crash detection (non-zero exit per invocation) → `ExecutorEvent::Crashed`
- [x] 4.5 Integration tests against the fake-executor stub (§2): normal turn, crash path, multi-turn resume sequence

## 5. Mode handoff (/go)

- [x] 5.1 Implement `/go` chat command and UI button both calling one handoff function
- [x] 5.2 Implement idle-only gating (reject switch while a call is in flight, either direction)
- [x] 5.3 Implement handoff sequence: terminate spec-mode executor, spawn go-mode executor per §3/§4, check thread's `openSpecChangeName` and send `/grill-apply <name>` / plain conversation accordingly
- [x] 5.4 Implement pass-through wrapper: forward user input to the live executor, stream `ExecutorEvent`s back
- [x] 5.5 Implement switch-back-to-spec-mode termination (no backgrounding)
- [x] 5.6 Implement crash reaction: banner + `currentMode` revert to `spec` + preserved history, on `ExecutorEvent::Crashed`
- [ ] 5.7 `cargo test` unit tests: idle gating rejects mid-call switches, crash reaction updates `.meta.json` correctly — **partially done**: idle gating is covered at `executor::send` (`a_second_turn_is_rejected_while_the_first_is_in_flight`), but the crash reaction has no test because it lives in `AppSink::emit` and needs a Tauri `AppHandle`. Behaviour verified manually by killing a live executor; the missing coverage is item 1 of `day-23-floo-network/FOLLOW-UPS.md`.

## 6. OpenSpec change linking (/propose)

- [x] 6.1 Implement `/propose` command sending `/grill-propose` (Claude) or `$grill-propose` (Codex) to the running spec-mode executor
- [x] 6.2 Implement detection of `grill-propose` success and extraction of the resulting change name
- [x] 6.3 Implement writing `openSpecChangeName` to the thread's `.meta.json`
- [x] 6.4 Implement the handoff-readiness preflight check (`grill-apply` + `openspec` presence per executor) and persistent UI status indicator

## 7. Frontend: event rendering and pass-through UI

- [x] 7.1 Implement chat-pane rendering for `Text`/`Reasoning` events as chat bubbles
- [x] 7.2 Implement `FileEdit` event rendering via `react-diff-viewer-continued`
- [x] 7.3 Implement `ToolCall` event rendering as collapsible command+output blocks
- [x] 7.4 Implement the crash banner UI
- [x] 7.5 Implement the handoff-readiness status indicator UI (from §6.4)

## 8. End-to-end verification

- [x] 8.1 Manual walkthrough against a real installed executor: spec-mode chat → `/propose` → `/go` → live go-mode session → switch back to spec-mode
- [x] 8.2 Tauri MCP E2E (per C9 in change 1): mode switch triggers visible pass-through UI change
- [x] 8.3 Tauri MCP E2E (per C9 in change 1): crash banner appears and mode reverts — verified by killing the real executor process mid-session
- [x] 8.4 Confirm `openspec status` shows all tasks complete before archiving
