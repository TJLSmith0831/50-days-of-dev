## Context

`day-22-agent-notch-watcher` is a Rust/eframe/egui macOS HUD that docks into the camera notch, tracking AI agent sessions via a local HTTP listener (`127.0.0.1:8765`) and a file tailer. An architecture review (2026-08-02) found session-launch logic duplicated across the HTTP handler and the egui "Spawn" button (`main.rs:93-128`, `main.rs:399-414`), both silently swallowing spawn errors. A follow-up UX sweep, done specifically because the user is recording a demo shortly, found five more dead ends: no quit affordance, unbounded tab/prompt overflow, a launch form requiring exact command/path recall, and a fake seeded session masking what "nothing running" should look like — which turned out to leak into the collapsed header too, not just the tab strip.

`AppState` (`lib.rs:271-281`) is the single source of truth, shared via `Arc<Mutex<AppState>>` and cloned once per egui frame (~60fps) and once per HTTP request. Two independent write paths feed it today: `POST /event` → `apply_event` (mutates top-level `agent_type`/`status`/`step_description`/`session_limit` fields directly, used by `simulate.rs` and real agent hooks) and `register_session`/`select_session` (mutates the `sessions` HashMap + `active_session_id`, used by session launch/tab-click). These two paths are currently independent — the collapsed header reads only the top-level fields, the tab strip reads only `sessions`.

## Goals / Non-Goals

**Goals:**
- One implementation of "launch a session," used by both the HTTP handler and the egui button.
- Every launch failure is visible in the UI — no `let _ = ...` swallowing.
- The HUD (header AND drawer) has a real, load-bearing "no sessions running" state, not a fake placeholder.
- Launching a session doesn't require the user to recall an exact binary name or type a directory path from memory.
- Session tabs and prompt-card queues never silently overflow.
- Add a way to quit the app without a terminal.

**Non-Goals (deferred, tracked in `docs/BUGS.md`):**
- Adding a regression test for the lock-order-inversion risk between `handle_permission_request`/`resolve_permission_channel`.
- De-duplicating agent-name classification between `lib.rs::match_agent_type_from_name` and `tailer.rs::parse_jsonl_line`.
- Making `simulate.rs` serialize real `lib.rs` types instead of hand-written `json!` literals.
- None of the above are visible in a demo recording; all three are explicitly out of scope for this change.

## Decisions

### 1. `launch_session()` — free async function in `lib.rs`, not an `AppState` method
```rust
pub async fn launch_session(shared_state: &SharedState, payload: &SessionLaunchPayload) -> (String, Option<String>)
```
Returns `(session_id, None)` on success, `(session_id, Some(reason))` on spawn failure — `tokio::process::Command::spawn()` fails synchronously (bad binary/path), so the failure is known before the function returns; no polling needed. Internally: mint `session_id`, lock only to call `register_session`, release, spawn. On `Err`, lock again to call `mark_session_failed(session_id, reason)` before returning.

**Why a free function, not `impl AppState`:** every existing `AppState` method is a synchronous mutation taken under the mutex; the egui render loop locks the same mutex every frame (~60fps). A method holding the lock across `Command::spawn()`'s await would stall the HUD on every launch. **Alternative considered:** a method that only synchronously validates+registers, returning a value the caller then spawns from — rejected because it splits one operation across two call sites again, recreating the exact duplication this change removes.

Both call sites (`handle_session_launch` in `main.rs`, the egui "Spawn" button closure) become ~3-line wrappers around this call.

### 2. Failure surfacing: `AgentStatus::Error` + `FailedLaunch` prompt queue
- New variant `AgentStatus::Error`, color `Color32::from_rgb(200, 40, 40)` (distinct from `WARN`'s coral, used for `QuotaWarning`), label `"Launch failed"`.
- New struct `FailedLaunch { session_id: String, agent_name: String, reason: String }`, stored in `AppState.pending_launch_failures: Vec<FailedLaunch>` alongside the existing `pending_permissions: Vec<PermissionRequest>`.
- `AppState::mark_session_failed(&mut self, session_id: &str, reason: &str)`: sets that session's `status = AgentStatus::Error`, `step_description = format!("Failed to launch: {reason}")`, pushes a `FailedLaunch` entry.
- Failed sessions stay in `sessions` (visible, red tab) — never auto-removed.
- New card in the expanded drawer, structurally mirroring the existing Interactive Permission Prompt card (`main.rs:424-459`): renders `pending_launch_failures.first()`, two buttons — **"Kill it"** calls `AppState::remove_session(session_id)` (removes from `sessions` and the failure queue; if it was `active_session_id`, falls back per Decision 4); **"Later"** just removes the entry from `pending_launch_failures` (session tab stays, still red, reachable anytime).
- Both the permission-prompt card and the launch-failure card gain a `"+{n-1} more waiting"` line when their respective queue's `.len() > 1`.

**Alternative considered:** a toast/popup notification instead of a persistent card — rejected, doesn't fit the existing egui immediate-mode painter architecture (no toast system exists) and a card is one rendering path shared with the already-proven permission-prompt pattern.

### 3. `active_session_id: Option<String>`, no fake seeded session
- `AppState.active_session_id` changes from `String` to `Option<String>`.
- `AppState::default()` no longer seeds a `"claude-default"` session; `sessions` starts empty, `active_session_id` starts `None`.
- Top-level fields (`agent_type`, `status`, `step_description`, `session_limit`) that `select_session` currently copies from the active session must also reflect "no session": when `active_session_id` is `None`, the collapsed header shows a neutral/dim state — status dot dimmed, label `"No agent running"`, no gauge drawn (the bottom-edge token gauge segment is simply not painted). This is the header-level fix from Decision 5 below, folded in here since both stem from the same `Option<String>` change.
- **Kill/dismiss fallback** (`remove_session`): if the removed session was active, activate any one remaining session (`sessions.keys().next()`) if any exist; if `sessions` is now empty, `active_session_id = None`.
- `POST /event` (`apply_event`) is unaffected in shape — it still mutates top-level fields directly for agents that only speak the event protocol (no session concept). This means top-level fields can be non-empty via `/event` even with zero entries in `sessions`; the "no session" header render gates specifically on `sessions.is_empty()`, not on the top-level fields' default-ness — an agent pushing raw `/event` data without ever going through `launch_session`/tailer registration is still a legitimate signal the HUD should show something is happening. **Open question, flagged below** — see Open Questions.

**Alternative considered:** keep `active_session_id: String` with `""` as the sentinel for "none" — rejected, `Option<String>` makes "no active session" a compiler-checked state instead of a magic-string convention, and this codebase already leans on Rust's exhaustive-match guarantees elsewhere (`AgentStatus` rendering).

### 4. Launch form: `AgentType` dropdown + native folder picker
- Replace the free-text "Cmd:" `TextEdit` with an `egui::ComboBox` over `AgentType` variants, using the existing `label_of()` display names. Selecting `Custom` reveals a free-text field for anything not in the enum (npm-installed CLIs, forks, etc.).
- `AgentType -> command` mapping (new, `lib.rs`): `Anthropic -> "claude"`, `Gemini -> "gemini"`, `OpenAi -> "codex"`, `Ollama -> "ollama"`. Chosen to match the substrings `match_agent_type_from_name` (`lib.rs:190-203`) already classifies back to each type, so a dropdown-launched session round-trips through the same classifier without mismatch.
- Add `rfd = "0.14"` (or latest 0.1x) to `Cargo.toml`. "Dir:" field gets a **"Browse…"** button beside the existing editable text field, calling `rfd::FileDialog::new().pick_folder()` and writing the result into `launch_dir`. Text field stays editable for users who want to paste a path directly.

**Why `rfd` over hand-rolled `NSOpenPanel` FFI:** `objc2-app-kit` is already a dependency, but it doesn't currently enable the `NSOpenPanel` class, and wiring a native-quality folder picker through raw `objc2` bindings is real unsafe boilerplate for something a 3-line, well-maintained crate call already solves. This is the one new dependency in the change; everything else reuses existing types/crates.

### 5. Notch control affordances
- **Quit**: right-click on the notch (`ui.interact` region already exists at `main.rs:560-561` for the click-to-expand header hit-test) gains an egui `context_menu` with a single "Quit" item calling `std::process::exit(0)`. No confirmation dialog — matches the app's overall low-ceremony interaction style (single-click expand/collapse, single-click Approve/Deny).
- **Tab strip overflow**: wrap the session-tab `ui.horizontal` (`main.rs:362-380`) in `egui::ScrollArea::horizontal().max_width(wrap)` so any number of sessions stays reachable by scroll instead of clipping or crowding out the "🚀 + Launch" button.

### 6. Passive multi-session tracking — tailer registers a tab per detected file
Discovered during design drafting, not part of the original architecture review: the user's actual demo plan (open Claude Code, run a request; open Antigravity, run a request; watch the HUD track both) doesn't work with the tailer as it stands. `start_universal_tailer` (`tailer.rs:173-201`) already iterates multiple files (`scan_log_directories`: `~/.claude/projects/*`, `~/.cursor/logs`, `~/.gemini/brain`, `~/.aider`), but every event from every file calls `apply_event`, clobbering one shared set of top-level `AppState` fields — two real concurrent agents fight over one header with no separate tabs.

- **Session identity**: `session_id` = the file's path (already the stable key in `file_offsets`, no new scheme needed). `agent_type` = derived from which top-level source directory the file lives under — a small path→`AgentType` lookup placed next to `scan_log_directories`, *not* derived from file content. `agent_name` (tab label) = a static string per source dir ("Claude Code", "Antigravity", "Cursor", "Aider").
  **Why location, not content:** `parse_jsonl_line` only sets `agent_type` when the JSON line itself carries an `"agent_type"` key (`tailer.rs:110-120`); real transcript lines from Claude Code/Antigravity never do (they use `role`/`type`). Location is the only reliable signal, and keeping it a second, independent classifier (not reusing the content-based one) avoids compounding the already-deferred duplicated-classification bug (`docs/BUGS.md` #3).
- **Tailer loop change**: for each tailed file, on parsing a new event, call `register_session(&file_path, source_agent_type, &source_label)` (or update the existing entry if already registered) instead of `apply_event` directly on top-level state. The per-session `AgentEvent` data (status, step_description, tokens) still needs to land somewhere per-session — extend `SessionState` to carry the same fields `apply_event` currently writes to top-level `AppState`, and add a `SessionState::apply_event`-equivalent update path.
- **No auto-expiry**: a passively-tracked tab never disappears or reverts to Idle when its file stops updating — there's no process handle, so there's no clean "ended" signal, only "stopped changing" (which needs an arbitrary timeout guess, risking a tab flipping mid-demo just because an agent paused). The existing "Kill it" action (Decision 2) is reused as the only removal path — no second mechanism.
- **Header focus rule**: the collapsed header (single status dot/label/gauge) auto-follows whichever session most recently reported activity — via `/event` or a tailer update — regardless of which tab is clicked. Clicking a tab still independently drives what the *expanded drawer* shows via `select_session`; the two are decoupled. Requires a `last_updated` marker (e.g. a monotonic counter or `Instant`, not wall-clock — the codebase already avoids `SystemTime` where ordering-only comparison is needed, e.g. token math) added to `SessionState`, since it doesn't have one today.

**Alternative considered:** keep the tailer as global-state-only and let the Launch button be the only way to get a tab — rejected, this is the user's actual demo plan and the tailer's whole purpose (ADR-0001's "Passive Auto-Discovery") is to make the HUD track sessions the user didn't explicitly launch through it.

## Risks / Trade-offs

- **[Risk]** Changing `AppState::default()` to start empty removes the only guaranteed-non-empty session state; any code that implicitly assumed `sessions`/`active_session_id` are always populated (existing tests in `tests.rs` asserting `AgentStatus::Idle`/the default session at minimum) will break. → **Mitigation**: audit all `AppState` field reads during implementation; update `tests.rs` to assert the new empty default explicitly, add one test asserting the header renders the empty state at zero sessions.
- **[Risk]** `/event`-only agents (via `simulate.rs` or real hook integrations) never touch `sessions` at all — under the new header logic gated on `sessions.is_empty()`, an `/event`-only integration could show a populated header with zero session tabs, which may look inconsistent on camera. → **Mitigation**: flagged as an open question below; likely fine to leave as-is since `/event`-only usage is a distinct, real integration path (ADR-0001's "Active Hook Integration"), not a bug — but worth a quick manual check before recording.
- **[Risk]** `rfd`'s folder-picker dialog blocks the calling thread while open (typical native-dialog behavior) — if called from the egui UI thread synchronously, this would freeze HUD repaints while the picker is open. → **Resolved at implementation (see D20)**: the proposed mitigation (background thread) does not work — `NSOpenPanel` is a native modal that `rfd` dispatches to and blocks on the *main* thread no matter which thread calls it, so the HUD pauses either way. Called synchronously on the UI thread; accepted as normal modal-dialog behavior.
- **[Risk]** Removing the seeded demo session changes what `cargo run --bin agent-notch-watcher` shows on a bare run with no simulator/hooks attached — a "boring" empty HUD is the correct honest state per D13, but is a behavior change worth calling out in the README's Quick Start so a future contributor doesn't file a "HUD shows nothing" bug report against intended behavior.
- **[Risk]** Two agents writing to their log files in the same ~1.5s tailer poll interval could both update in the same loop iteration — since each now maps to a distinct `session_id` (its file path), this is naturally fine (two separate `register_session`/update calls, no shared-state race beyond the existing single `Mutex<AppState>` lock per update) — flagged here only to confirm no new race is introduced by the per-file registration change.
- **[Risk]** `file_offsets.entry(path).or_insert(0)` (`tailer.rs:180`) seeds every newly-seen file at offset 0 — on cold start, the tailer replays a file's *entire* historical content, not just new writes. With per-file session registration (Decision 6), this means every old Claude Code project directory with any transcript ever written would spawn a permanent tab the first time the app runs — flooding the tab strip with dormant history instead of showing only what's actually active. → **Mitigation**: seed `file_offsets` to the file's *current length* (not `0`) the first time a file is seen, so the tailer only reads new writes going forward — standard `tail -f` semantics, matching ADR-0001's intent of tracking *active* sessions. This is a correctness fix to the existing tailer, needed regardless of per-file registration, but only becomes user-visible (as spurious tabs) once registration is added.

## Migration Plan

No persisted external state (no DB, no config file) — this is a source-level change to a single binary pair. Steps:
1. Land `lib.rs` changes (types, `launch_session`, `AppState` methods) — compiles standalone, `tests.rs` updated in the same pass since the type changes (`Option<String>`, new `AgentStatus` variant) are compiler-enforced breaking changes.
2. Land `main.rs` changes (HTTP handler collapse, egui launch form, tab scroll, prompt cards, quit menu, header empty state).
3. Add `rfd` to `Cargo.toml`, verify `cargo build` picks it up cleanly.
4. Manual verification pass (see tasks.md) — no automated UI test harness exists for the AppKit/egui layer (per `AGENTS.md`: "UI/AppKit is verified by running").
5. Update `README.md` Quick Start / `docs/BUGS.md` to reflect the 3 deferred items and the new empty-cold-start behavior.

No rollback complexity — this is a single local dev binary, not a deployed service; reverting is `git revert`.

## Open Questions

- Should the collapsed header's empty-state gate on `sessions.is_empty()` specifically, or on "no session AND no recent `/event` activity"? Current design gates on `sessions` only, leaving `/event`-only integrations (e.g. `simulate.rs`, real Claude Code hooks per ADR-0001) able to populate the header without a session tab existing. Flagged in Risks above — not blocking, but worth a manual check during implementation before recording.
