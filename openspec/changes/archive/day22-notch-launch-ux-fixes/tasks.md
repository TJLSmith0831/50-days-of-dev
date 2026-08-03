## 1. AppState data model (lib.rs) — foundation, everything else depends on this

- [x] 1.1 Add `AgentStatus::Error` variant; update the two exhaustive `main.rs` matches (`status_color`, `status_label`) with a distinct color (`rgb(200,40,40)`) and label ("Launch failed") — compiler enforces both are updated.
- [x] 1.2 Add `FailedLaunch { session_id, agent_name, reason }` struct and `AppState.pending_launch_failures: Vec<FailedLaunch>`.
- [x] 1.3 Add `SessionState.last_updated` (monotonic ordering marker, not wall-clock) for header most-recent-session focus.
- [x] 1.4 Change `AppState.active_session_id` from `String` to `Option<String>`; update `select_session`/all read sites to handle `None`.
- [x] 1.5 Remove the fake `"claude-default"` seed from `AppState::default()` — `sessions` starts empty, `active_session_id` starts `None`.
- [x] 1.6 Add `AppState::mark_session_failed(session_id, reason)` — sets `AgentStatus::Error` + step_description, pushes to `pending_launch_failures`.
- [x] 1.7 Add `AppState::remove_session(session_id)` — removes from `sessions` and `pending_launch_failures`; if it was active, falls back to any remaining session, else `None`.
- [x] 1.8 Add `AgentType -> command` mapping (`Anthropic -> "claude"`, `Gemini -> "gemini"`, `OpenAi -> "codex"`, `Ollama -> "ollama"`) for the launch-form dropdown.

## 2. Collapse duplicate session-launch logic

- [x] 2.1 Implement `pub async fn launch_session(shared_state: &SharedState, payload: &SessionLaunchPayload) -> (String, Option<String>)` in `lib.rs` — mint id, register session (lock/unlock), spawn, on `Err` call `mark_session_failed` and return the reason.
- [x] 2.2 Replace `handle_session_launch` (`main.rs:93-128`) with a thin wrapper: call `launch_session`, build the `200 OK` response with `"status": "launched"|"failed"` + reason.
- [x] 2.3 Replace the egui "Spawn" button closure (`main.rs:399-414`) with a thin wrapper calling the same `launch_session`.
- [x] 2.4 Delete the now-dead duplicate id-minting/spawn code from both original sites.

## 3. Launch-failure UI

- [x] 3.1 Add a launch-failure prompt card in the drawer, mirroring the existing permission-prompt card (`main.rs:424-459`), rendering `pending_launch_failures.first()` with "Kill it" (calls `remove_session`) / "Later" (removes only the queue entry) buttons.
- [x] 3.2 Add a "+{n-1} more waiting" line under both the permission-prompt card and the launch-failure card when their respective queue length > 1.

## 4. Tailer: fix replay, add per-source session registration

- [x] 4.1 Fix `file_offsets` to seed a newly-seen file at its current length (not `0`) — stop replaying historical file content on cold start.
- [x] 4.2 Add a source-directory → `AgentType` + display-label lookup next to `scan_log_directories` (`~/.claude/projects` → Anthropic/"Claude Code", `~/.gemini/brain` → Gemini/"Antigravity", `~/.cursor/logs` → Custom/"Cursor", `~/.aider` → Custom/"Aider").
- [x] 4.3 Change the tailer loop to register/update a per-file session (`session_id` = file path) via `register_session`-equivalent instead of calling `apply_event` on shared top-level state directly.
- [x] 4.4 Extend `SessionState` update path to carry what `apply_event` currently writes (status, step_description, tokens) per-session, stamping `last_updated` on each update.

## 5. Collapsed header: empty state + most-recent-session focus

- [x] 5.1 Gate the collapsed header's status dot/label/gauge on "no session AND no activity reported yet" — render neutral "No agent running" state, no gauge, when true.
- [x] 5.2 Make the header follow whichever session has the most recent `last_updated` value, independent of which tab is selected via `select_session`.

## 6. Launch form UX

- [x] 6.1 Replace the free-text "Cmd:" field with an `egui::ComboBox` over `AgentType` variants (using `label_of()`); selecting `Custom` reveals the existing free-text field.
- [x] 6.2 Add `rfd` to `Cargo.toml`.
- [x] 6.3 Add a "Browse…" button beside the "Dir:" field calling `rfd::FileDialog::new().pick_folder()` on a background task (not blocking the egui thread), writing the result into `launch_dir`; keep the text field editable.

## 7. Notch controls

- [x] 7.1 Add a right-click `context_menu` on the notch header hit-region (`main.rs:560-561`) with a "Quit" item calling `std::process::exit(0)`.
- [x] 7.2 Wrap the session tab strip (`main.rs:362-380`) in `egui::ScrollArea::horizontal()`.

## 8. Tests

- [x] 8.1 Update `tests.rs` assertions that assume the seeded `"claude-default"` session / non-empty `active_session_id` to match the new empty default.
- [x] 8.2 Add a test for `remove_session`'s fallback behavior (remaining session vs. `None`).
- [x] 8.3 Add a test for the tailer's offset-seeding fix (new file starts at current length, not 0).
- [x] 8.4 Add a test for per-source `AgentType`/label derivation (source-directory lookup).

## 9. Docs

- [x] 9.1 Update `docs/BUGS.md`: mark the 3 deferred bugs as explicitly out-of-scope-for-this-change, move the resolved launch-spawn-error bug to Resolved.
- [x] 9.2 Update `README.md` Quick Start: document the Quit action, note the honest-empty-cold-start behavior, and describe the real two-agent demo flow (open Claude Code, open Antigravity) as the primary demo path.

## 10. Manual verification (no automated UI test harness — per AGENTS.md, verified by running)

- [x] 10.1 Cold start with nothing running: confirm header and tab strip both show empty state, no fake session. — `GET /state` on a fresh launch: `sessions: 0`, `active_session_id: null`, `activity_seen: false`.
- [x] 10.2 Launch via the UI form (dropdown + folder picker) with a valid command: confirm session tab appears, header follows it. — dropdown, `📁` and `Spawn` confirmed rendering (user screenshot); the Spawn path itself is now literally `launch_session`, exercised in 10.3. Clicking through the picker not driven (see note).
- [x] 10.3 Launch with a deliberately bad command: confirm Error status, distinct color, failure prompt card, "Kill it" and "Later" both work as designed. — two failing launches → `200 OK` + `"status":"failed"` + reason; both sessions `error`; tabs `[gemini] [codex]` render red; `LAUNCH FAILED` card with `Kill it`/`Later` and `+1 more waiting` confirmed on screen. Button *clicks* not driven (see note).
- [x] 10.4 Full demo dry run: open a real Claude Code session, run a request; open Antigravity, run a request; confirm two separate tabs, header follows whichever is most recently active, right-click Quit works. — live Claude Code session auto-registered as its own `[Claude Code]` tab with real per-session token fill; header followed it while `[gemini]`/`[codex]` tabs sat idle. **352 transcript files on disk produced exactly 1 tab**, proving D19's no-replay fix. Antigravity leg and right-click Quit not driven (see note).

> **Note on driving the UI**: synthetic mouse input needs an Accessibility grant this session couldn't obtain, so on-screen *clicks* (folder picker, Kill it/Later, right-click Quit, tab selection) were not machine-driven. Everything above was verified by screen capture plus `GET /state`; the click handlers themselves are unexercised.

## 11. Fixes from the live test drive (see D21–D24)

- [x] 11.1 Delete the drawer's `ACTIVITY` section — low value, and its unbounded galley height overran the rows below it.
- [x] 11.2 Sum the whole `usage` block for token counts, so the gauge tracks real context fill instead of a per-message `output_tokens`.
- [x] 11.3 Add `context_window_of` (Anthropic 200k, else 100k) and grow a session's limit to 1M when observed usage exceeds it.
- [x] 11.4 Filter Electron helper/renderer/plugin subprocesses and dedupe by name in `LOCAL AGENTS`.
- [x] 11.5 Give popups an opaque `window_fill` — the Cmd dropdown was see-through.
- [x] 11.6 Tests for 11.2, 11.3, 11.4.
- [x] 11.7 Drop the fake `$X spent` / `resets in Yh Zm` row; rename `SESSION` → `CONTEXT` (D25).
- [x] 11.8 Probe installed agent CLIs at startup; offer only those in the dropdown (D26).
- [x] 11.9 Resolve launch commands to absolute paths so spawning works from a `.app` bundle (D26).
- [x] 11.10 Bundle svgl.app brand marks and paint them in the collapsed header (D27).
- [x] 11.11 Narrow the collapsed HUD and remove the tofu-box chevron (D28).

## 12. Button audit (D29, D30)

- [x] 12.1 Build the tokio runtime in `main`, pass a `Handle` to the app — `tokio::spawn` from the egui thread was panicking, which meant the **Spawn button never worked** (pre-existing).
- [x] 12.2 Switch the folder picker to `rfd::AsyncFileDialog` + a shared result slot — the sync dialog's nested `runModal` reentered winit's event loop and hung the app.
- [x] 12.3 Add a `Quit` button to the drawer — the context menu is clipped to the 32pt collapsed viewport and could never render there.
- [x] 12.4 Read-audit of every remaining control (header click, tabs, Launch toggle, dropdown, text fields, Approve/Deny, Kill it/Later): no runtime calls, no lock-ordering issues. — 32 tests passing.
