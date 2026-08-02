# Day 22 — StackWatch — AGENTS.md
Native macOS HUD that docks into the hardware camera notch: manages AI agent CLIs (spawn, watch,
kill) and gives sessions it launched a real interactive terminal in the drawer. The
dynamic-island take on `herdr`. Ships as `StackWatch.app`; crate is still `stackwatch`.

## Stack
Rust · `eframe`/`egui` (painter-only UI) · `objc2`/AppKit (window level + notch geometry) · Axum · `sysinfo` · `portable-pty` + `vt100` (session terminals)

## Commands (verified 2026-08-02)
- Test: `cargo test` (42: 38 lib + 4 bin — the egui/AppKit paint pass itself is verified by running)
- Run App: `cargo run --bin stackwatch`
- Package + install: `./package.sh` → `/Applications/StackWatch.app` (`--no-install` for `dist/` only)
- Run Simulator: `cargo run --bin simulate`
- Terminal check: `cargo run --bin check_term` (spawns `top` + real `claude` in a PTY, exit 0/1)
- Folder-picker regression check: `cargo run --bin check_picker` (unattended, ~9s, exit 0/1/2)
- Drive the UI without a mouse: `curl -XPOST :8765/ui -d '{"mode":"terminal","session_id":"..."}'`

## Concept
The camera notch is dead screen real estate. This is a "Dynamic Island" for agents: a bar that
is square at the top and rounded at the bottom, so it reads as *the notch got wider* rather than
as a floating window. Content is laid out in the two shoulders either side of the physical
cutout; clicking drops a drawer.

## Gotchas
- **The window must be positioned explicitly.** With no `with_position`, macOS centres it and the
  HUD floats mid-screen. `NotchGeometry::dock_position` computes top-centre; `main.rs` sends
  `ViewportCommand::OuterPosition` whenever the collapsed/expanded shape changes.
- **`with_always_on_top` is not enough.** It gives `NSFloatingWindowLevel` (3); the menu bar sits
  at 24, so a window at `y: 0` renders *behind* the notch strip. `notch.rs` raises the level to
  `NSStatusWindowLevel + 1` (26) via `objc2`.
- **The window is sized to its content.** A fixed oversized transparent window swallows clicks
  meant for whatever is underneath it.
- **Activate the app before opening any AppKit panel.** An `Accessory` app never activates by
  itself, and clicking a status-level window focuses the window without activating the *app*.
  `NSOpenPanel` (via `rfd`) is presented as a sheet on the HUD; a sheet whose app is inactive
  can't become key, so it renders as a dead panel over a window-modal HUD — a permanent
  beachball. `notch::activate_app()` first. See `docs/BUGS.md`.
- `objc2*` deps are pinned to the exact versions `winit 0.30` already pulls in, so they add no
  extra compile time. Bumping `eframe` may bump `winit` and desync them.
- `NSScreen::auxiliaryTopLeftArea` is zero-sized on Macs without a notch → falls back to treating
  the menu bar as the notch, so the HUD still docks sanely on external displays.
- Verify window docking without a screenshot: `CGWindowListCopyWindowInfo` reports bounds and
  layer (see `critiques/` notes). Screen-recording permission is often unavailable to agents —
  `screencapture` fails with "could not create image from display", and the computer-use MCP
  cannot even *enumerate* an `LSUIElement` app, so neither screenshots nor synthetic clicks are
  available. `POST /ui` exists to drive the panes instead; use it plus `swiftc` +
  `CGWindowListCopyWindowInfo` for geometry.
- Local HTTP server on `127.0.0.1:8765` accepts events from any CLI, script, or curl payload.
- **Terminals only exist for sessions StackWatch launched.** A process's controlling terminal
  belongs to whoever opened it; there is no macOS API to adopt another process's tty. Detected
  (externally-started) agents are monitor + kill only. Don't "fix" this — it isn't a bug.
- **Detection is an exact allowlist, never substring.** Substring matching on `node`/`python` is
  what put `CursorUIViewService` in the agent list with a Kill button. See `is_agent_cli`.
- `top_level_agents` exempts pid 1 from the same-name-same-parent collapse: `launchd` parents
  every GUI app and adopts every orphan, so two agents sharing parent 1 are unrelated.
- The slave PTY fd **must** be dropped after `spawn_command`. Holding it open means the master
  never sees EOF, so a dead session reads as live forever and its terminal never reaps.
- Spawned agents get an explicit `TERM=xterm-256color` and a full `PATH`. Without the former the
  CLI renders no TUI at all; without the latter an agent launched from the `.app` can't find
  `git`/`node`/`rg` and fails in ways that look like the agent is broken.
