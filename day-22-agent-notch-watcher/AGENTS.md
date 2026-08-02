# Day 22 — Agent Notch Watcher — AGENTS.md
Native macOS HUD that docks into the hardware camera notch and streams AI agent activity, session quota, and locally-running agent processes.

## Stack
Rust · `eframe`/`egui` (painter-only UI) · `objc2`/AppKit (window level + notch geometry) · Axum · `sysinfo`

## Commands (verified 2026-08-02)
- Test: `cargo test` (20 tests, lib only — UI/AppKit is verified by running)
- Run App: `cargo run --bin agent-notch-watcher`
- Run Simulator: `cargo run --bin simulate`

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
- `objc2*` deps are pinned to the exact versions `winit 0.30` already pulls in, so they add no
  extra compile time. Bumping `eframe` may bump `winit` and desync them.
- `NSScreen::auxiliaryTopLeftArea` is zero-sized on Macs without a notch → falls back to treating
  the menu bar as the notch, so the HUD still docks sanely on external displays.
- Verify window docking without a screenshot: `CGWindowListCopyWindowInfo` reports bounds and
  layer (see `critiques/` notes). Screen-recording permission is often unavailable to agents.
- Local HTTP server on `127.0.0.1:8765` accepts events from any CLI, script, or curl payload.
