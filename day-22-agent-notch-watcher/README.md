# Day 22: Agent Notch Watcher (macOS Notch HUD)

A native macOS HUD, in Rust, that **docks into the MacBook camera notch** and streams AI agent
activity: current agent, status, session token quota, and locally-running agent processes.
7.4 MB release binary (`cargo build --release`, measured), `eframe`/`egui` + AppKit + Axum.

The shape is the point: square top corners, rounded bottom, flush at `y: 0`, laid out in the two
shoulders either side of the physical cutout — so it reads as *the notch got wider*, not as a
window floating over the desktop.

## What it shows

**Collapsed** (notch height, ~486×32pt on a 14" MBP)
- Status dot (pulsing) + agent name in the brand accent, on the left shoulder
- Status text + chevron on the right shoulder
- The bottom edge is the session-token gauge — visible without expanding, red past 90%

**Expanded** (click anywhere on the bar)
- `ACTIVITY` — the current step description
- `SESSION` — tokens used / limit / %, spend, and reset countdown
- `LOCAL AGENTS` — top 3 detected agent processes with CPU and RSS

## Glow modes

Set per-event via `glow_setting`. Controls the accent stroke and the gauge, never the legibility.

| Value | Behaviour |
|---|---|
| `max` | Full breathing accent — reads well on video |
| `subtle` | Same curve, ~⅓ the amplitude |
| `off` | Steady clean glass outline, zero pulse |

The pulse never reaches 0 alpha — a HUD that blinks fully out reads as a crash, not as a pulse.

## Quick start

```bash
cargo test
```

```bash
cargo run --bin agent-notch-watcher
```

Demo sequence, in a second terminal:

```bash
cargo run --bin simulate
```

## HTTP API

```bash
curl -X POST http://127.0.0.1:8765/event \
  -H "Content-Type: application/json" \
  -d '{"agent_type":"anthropic","status":"thinking","step_description":"Evaluating retrieval context...","tokens_used":76500,"glow_setting":"max"}'
```

`GET /state` returns the full current state. `agent_type`, `tokens_used` and `glow_setting` are
optional; `status` and `step_description` are required. Crossing 90% of the token limit
auto-escalates status to `quotawarning`.

## What was broken, and why

The first cut floated in the middle of the screen. Four separate causes, all fixed:

1. **No window position was ever set**, so macOS centred it. Now `NotchGeometry::dock_position`
   computes top-centre and the app sends `ViewportCommand::OuterPosition` on every shape change.
2. **`with_always_on_top` is not enough to reach the notch.** It gives `NSFloatingWindowLevel`
   (3); the menu bar sits at 24, so a window at `y: 0` renders *behind* the notch strip. The
   window level is now raised to `NSStatusWindowLevel + 1` via `objc2`.
3. **The window was a fixed 440×240 transparent box** with a small pill drawn inside it — so the
   invisible margin swallowed clicks meant for other apps. The window is now sized to its content.
4. **The brand badge picked `processes.first()`**, but `sysinfo` iterates a `HashMap` and the scan
   matches bare `node`/`python` — so a stray node process hijacked the badge at random. Detected
   processes are now sorted so identified agents sort first.

Verified on a 14" MacBook Pro: notch measured at 186×32pt, HUD docked at `x=513 y=0 486×32`
collapsed and `x=433 y=0 646×208` expanded, at window layer 26 (menu bar is 24).

## Notes

- On a Mac **without** a notch, `NSScreen::auxiliaryTopLeftArea` is zero-sized and the HUD falls
  back to treating the menu bar as the notch. It then covers the centre of the menu bar — usually
  empty space between the menus and the status items, but it is a real tradeoff.
- Runs as an `Accessory` app: no Dock icon, no app-switcher entry, visible on all Spaces.
- No `.app` bundle — it's a bare binary, so it won't appear in screenshot allowlists.
