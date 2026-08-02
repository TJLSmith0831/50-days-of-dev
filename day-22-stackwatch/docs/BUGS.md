# Known bugs & rough edges

Tracked from the architecture review on 2026-08-02. Update status as items close.

## Open

_All three below are explicitly **out of scope for `day22-notch-launch-ux-fixes`** (see that
change's D7): none of them is visible in a demo recording — a comment-only invariant, duplicated
match arms, and a background simulator binary's JSON shape. They matter to a future contributor._

### 2. Lock-order inversion risk between permission paths is undocumented-in-code
`handle_permission_request` and `resolve_permission_channel` (`main.rs:61–91`) both acquire
`state` then `channels` locks — same order today, so no deadlock yet — but the invariant lives
only in a comment (`main.rs:67–69`), not in a test. A future edit to either function that
reorders the locks deadlocks silently; `cargo test`'s 20 tests are all on pure `AppState`/
`NotchGeometry` logic and wouldn't catch it.

### 3. Duplicated agent-name → AgentType classification, already drifted
`lib.rs::match_agent_type_from_name` (190–203) and `tailer.rs::parse_jsonl_line` (110–120)
independently match agent binary names to `AgentType`. They've already diverged by one branch
(a `"claude"` alias present in tailer.rs's match, absent from lib.rs's). Touches ADR-0003
(single `UniversalJsonlTailer`, no per-agent adapters) — worth reopening since this is the
drift that ADR set out to prevent.

### 4. simulate.rs hand-writes JSON instead of serializing real types
`simulate.rs` builds `/event`, `/permission/request`, `/session/launch` bodies as raw
`serde_json::json!` literals rather than serializing `lib.rs::AgentEvent`/`PermissionRequest`.
A required field added to either struct keeps `simulate.rs` compiling while it silently sends
malformed JSON — the demo breaks at runtime instead of at build time.

### 5. The terminal grid's painted output has never been looked at
`row_segments` (run coalescing, wide glyphs, inverse video) is unit-tested, `check_term` proves
the VT parser receives and renders real TUI output, and `CGWindowListCopyWindowInfo` proves the
window sizes correctly. But no human or agent has seen the terminal pane drawn on a screen —
screen-recording permission was denied for the whole build (`screencapture` → "could not create
image from display"), and the computer-use MCP cannot enumerate an `LSUIElement` app, so
synthetic clicks and screenshots were both unavailable. Colour fidelity, cursor placement and
grid alignment are inferred from tests, not observed. First person with a display should open a
session terminal and check.

## Resolved

Closed by `day22-notch-launch-ux-fixes` (2026-08-02):

### 1. Session-launch spawn errors are silently swallowed (x2)
Both copies collapsed into one `lib.rs::launch_session()`; the HTTP handler and the egui Spawn
button are now thin callers. A failed spawn sets `AgentStatus::Error` on the session, keeps its
tab (red), and queues a "Kill it / Later" prompt card.

### Detection listed things that were not agents (2026-08-02)
`scan_system_agents` matched the substrings `python` and `node`, so a Python helper and
`CursorUIViewService` appeared under `LOCAL AGENTS` — each with a Kill button. Replaced with an
exact, case-insensitive allowlist (`is_agent_cli`). Two further passes came out of running it:
forked workers are dropped by parenthood, and same-name-same-parent siblings collapse (Devin's
app spawns two `devin` helpers under one non-agent parent), with pid 1 exempt because `launchd`
parents everything.

### The launch form's "initial prompt" field (2026-08-02)
Removed. It could open a session but never answer the agent's first follow-up question. Sessions
now spawn into a real PTY with an interactive terminal in the drawer, so the first message is
just the first thing you type. `SessionLaunchPayload` drops the field; serde ignores it, so
older callers still posting `initial_prompt` keep launching.

### UX rough edges found in the first-time-user sweep
- **No way to quit** — the app is an AppKit `Accessory` (no Dock icon, no ⌘Q), so `Ctrl+C` in the
  launching terminal was the only exit. Now: right-click the notch → Quit.
- **Tab strip overflowed silently** — now horizontally scrollable, with the Launch button pinned.
- **Prompt cards hid their queue** — both the permission and launch-failure cards now show
  "+N more waiting".
- **Launch form required exact recall** — Cmd is a dropdown over `AgentType` (Custom keeps free
  text); Dir gets a native folder picker beside the still-editable text field.
- **A fake seeded `claude-default` session** masked what "nothing running" looks like — removed;
  the HUD now starts genuinely empty and renders a real empty state in both header and drawer.
- **Passive sessions clobbered each other** — the tailer registers one session per detected log
  file instead of overwriting shared top-level state, so two concurrent agents get two tabs.

### Found during the live test drive (2026-08-02)
- **Token gauge looked frozen** — the transcript lookup returned whichever token-ish key it hit
  first (per-message `output_tokens`, a few hundred), not the session's context fill. Now sums
  the whole `usage` block; the limit starts per-agent and grows to 1M if exceeded.
- **`LOCAL AGENTS` showed three "Claude" rows** — one desktop app plus twelve Electron helper
  subprocesses matched the name scan. Helpers/renderers/plugins are skipped and names deduped.
- **The Cmd dropdown was transparent** — `window_fill` was set transparent along with
  `panel_fill`; only the panel needs it.
- **`ACTIVITY` deleted** — unreadable at 10pt, and its unbounded height overran the rows below.

### Found in the button audit (2026-08-02)
- **The Spawn button never worked** (pre-existing, inherited from the original duplicated
  launch code). The tokio runtime lived on a worker thread while the handler ran on the egui
  main thread, so `tokio::spawn` panicked with "must be called from the context of a Tokio 1.x
  runtime". `main` now owns the runtime and the app holds a `Handle`.
- **The folder picker hung the app.** `rfd::FileDialog` (sync) runs `NSOpenPanel::runModal`,
  spinning a nested native run loop from inside winit's event callback — reentrancy, beachball,
  no panel. Now uses `rfd::AsyncFileDialog` with a shared result slot.
- **Right-click Quit could never render when collapsed.** An egui context menu is an `Area`
  clipped to the viewport; collapsed, that's 32pt tall. A `Quit` button now lives in the drawer.

### The folder picker, second cut (2026-08-02)
- **The picker still spun forever, for a different reason.** The async fix removed the nested
  run loop but not the hang. `rfd`'s macOS async path has no "no parent" mode: it asks
  `NSApp` for a window (`mainWindow`, else `windows[0]`) and presents the panel with
  `beginSheetModalForWindow:` — so the folder panel becomes a *sheet on the 386×32 borderless
  notch window*. That sheet is window-modal, and the HUD is a non-activating
  `NSStatusWindowLevel+1` window in an `Accessory` app: clicking the HUD gives its window
  focus without ever making the *app* active. Instrumented state at the moment of the hang was
  `NSApp.isActive=false`, HUD `key=false sheet=true`, panel `isSheet=true key=false` — a panel
  that is on screen and cannot be typed into or clicked, over a HUD the sheet has blocked.
  Hence the permanent spinning-wait cursor. Fix: `notch::activate_app()`
  (`NSApp activateIgnoringOtherApps:`) immediately before presenting.
  Regression check: `cargo run --bin check_picker` — brings Finder forward to force the
  background-app state, fires the picker unattended, asserts the panel comes up key.
  6/6 red with `NO_FIX=1`, 6/6 green with the fix.
- **Watch for:** on one cold run, `[NSOpenPanel openPanel]` returned nil and `rfd` dereferenced
  it (`panel_ffi.rs:50`), aborting the whole process with a non-unwinding panic — not catchable
  from our side. Seen once in ~25 launches, only on a binary's first-ever run. Not reproduced
  since; noted here rather than chased.
