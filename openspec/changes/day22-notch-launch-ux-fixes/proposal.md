## Why

Day 22's notch HUD has a working core loop but real problems block calling it finished: session-launch is implemented twice (main.rs:93-128 and main.rs:399-414) with spawn errors silently swallowed in both copies; a first-time-user pass surfaced five UX dead ends (no quit affordance, tab/prompt overflow with no indicator, a launch form that requires typing exact binary names and paths from memory, and a fake seeded demo session masking what "no session running" should look like); and the planned demo — open Claude Code, run a request, then open Antigravity, run a request, watch the HUD track both — doesn't work today, because passively-detected sessions never get their own tab. This needs closing out now because the user is recording a demo of this project shortly.

## What Changes

- Collapse the duplicated session-launch implementation into one `launch_session()` free function in `lib.rs`; both the HTTP handler and the egui "Spawn" button become thin callers.
- Surface spawn failures instead of swallowing them: new `AgentStatus::Error` (distinct color from `QuotaWarning`), a launch-failure prompt card (reusing the existing Interactive Permission Prompt pattern) with "Kill it" / "Later" actions, failed sessions stay visible in the tab bar.
- **BREAKING**: `AppState::default()` no longer seeds a fake `"claude-default"` demo session — the HUD now starts with zero sessions and renders a genuine "no session" empty state when nothing is running. `active_session_id` becomes optional; killing the last remaining session returns to this same empty state (falls back to any other remaining session first).
- Session tab strip becomes horizontally scrollable instead of silently overflowing.
- Permission-prompt and launch-failure prompt cards gain a "+N more waiting" line when their queue holds more than one item.
- Launch form: the "Cmd" field becomes a dropdown over the existing `AgentType` variants (Custom keeps free text); the "Dir" field gains a native folder-picker "Browse…" button (new `rfd` dependency) alongside the existing editable text field.
- Add a right-click → "Quit" context menu on the notch (no in-app way to exit previously existed).
- `/session/launch` HTTP response stays `200 OK` on failure, with `"status": "failed"` + a reason in the body, matching every other handler's convention in this codebase.
- **Passive multi-session tracking**: the tailer (`start_universal_tailer`) registers a session tab per detected file/source directory instead of only mutating shared top-level fields — real Claude Code and Antigravity sessions running simultaneously each get their own tab. Session identity for these: `session_id` = file path, `agent_type` = derived from source directory (not file content), `agent_name` = a static label per source. Passively-tracked tabs never auto-expire (no process handle to detect "ended," only "stopped changing"). The collapsed header auto-follows whichever session most recently reported activity, independent of which tab is clicked/selected.

Out of scope for this change (tracked, deferred — see `day-22-agent-notch-watcher/docs/BUGS.md`): the untested lock-order-inversion risk between `handle_permission_request`/`resolve_permission_channel`, duplicated agent-name classification between `lib.rs` and `tailer.rs`, and `simulate.rs` hand-writing JSON instead of serializing real `lib.rs` types. None of these are visible in a demo recording.

## Capabilities

### New Capabilities
- `session-launch`: launching, failing, and dismissing an agent session from the notch HUD — one collapsed implementation, visible failure states, no-fake-session empty state, dropdown/folder-picker launch form.
- `notch-controls`: general HUD interaction chrome not specific to launching a session — quit affordance, tab-strip overflow scrolling, prompt-card queue indicators.
- `passive-session-tracking`: the tailer registering a session tab per detected agent (Claude Code, Antigravity, Cursor, Aider) instead of clobbering shared state, plus the collapsed header's most-recently-updated-session focus rule.

### Modified Capabilities
- None — no existing `openspec/specs/` capability covers this project (day-22 has no prior specs registered).

## Impact

- **Code**: `day-22-agent-notch-watcher/src/lib.rs` (AppState shape, `launch_session`, `AgentStatus::Error`, empty-session handling, `SessionState.last_updated`), `src/main.rs` (HTTP handler, egui launch form, tab strip, prompt cards, quit menu, header most-recent-session logic), `src/tailer.rs` (per-file session registration, source-directory → AgentType lookup), `src/tests.rs` (existing tests asserting the seeded default session need updating).
- **Dependencies**: adds `rfd` (native folder picker) to `Cargo.toml`.
- **Docs**: `docs/BUGS.md` gets the 3 deferred items marked explicitly out-of-scope-for-this-change; `README.md`'s Quick Start likely needs a quit-command mention removed/updated once the in-app Quit exists, and its demo instructions updated to describe the real two-agent flow instead of (or alongside) `simulate.rs`.
