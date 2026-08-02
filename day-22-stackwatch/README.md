# Day 22: StackWatch (macOS Notch HUD)

A native macOS HUD, in Rust, that **docks into the MacBook camera notch** and manages your AI
coding agents from there: which ones are running, how much context they've burned, and — for
sessions it launched — a **real interactive terminal** you type into without leaving the notch.

Think [herdr](https://betterstack.com/community/guides/ai/herdr-ai-agent/), collapsed into the
Dynamic Island. Same idea (one place to spawn, watch, and talk to every agent), different
surface: herdr is a terminal multiplexer you live inside, StackWatch is a strip of dead screen
real estate you glance at.

`eframe`/`egui` + AppKit + Axum + `portable-pty`/`vt100`. 42 tests.

The shape is the point: square top corners, rounded bottom, flush at `y: 0`, laid out in the two
shoulders either side of the physical cutout — so it reads as *the notch got wider*, not as a
window floating over the desktop.

## Three states

**Collapsed** — 386×32pt, the notch strip itself
- Status dot (pulsing) + the agent's brand mark on the left shoulder
- Status text on the right shoulder
- The bottom edge is the context gauge — visible without expanding, red past 90%

Deliberately narrow: the bar shares the strip with your menu-bar extras, and every point
of shoulder is a point of their icons covered.

**Drawer** — 606×382pt, click the bar
- Session tabs + `🚀 + Launch`, and any pending permission / launch-failure prompt
- `CONTEXT` — tokens used / context window / %
- `LOCAL AGENTS` — agent CLIs running anywhere on the machine, with CPU, RSS, and Kill
- `ACTIVITY` — one row per session; rows marked `▸` have a live terminal, click to open it

**Terminal** — 900×652pt, click a `▸` row
- The session's actual PTY, rendered from a VT100 parser at ~100×30
- Everything you type goes to the agent: arrows, Tab, `^C`, paste, the lot

### Launched vs. detected

Two kinds of agent show up, and the difference is not cosmetic:

| | Where it came from | You get |
|---|---|---|
| **ACTIVITY** | StackWatch launched it | Full interactive terminal |
| **LOCAL AGENTS** | Already running (your iTerm, Warp, an app) | Monitor + Kill |

A process's controlling terminal belongs to whoever opened it — macOS gives no way for another
process to take it over. So a `claude` you started in iTerm can be watched and killed from the
notch, but not typed into. Launch it from the notch instead and you get the terminal.

### What it deliberately doesn't show

Plan usage — the 5-hour window, weekly limit, and credit spend. Those aren't anywhere on disk;
Claude Code reads them off `anthropic-ratelimit-unified-*` response headers per request.
`CONTEXT` is the one usage number a transcript actually reports, and it matches Claude Code's own
"Context window" row exactly. A plausible-looking guess next to it would be worse than nothing —
the same reason there's no seeded demo session.

Brand marks are from [svgl.app](https://svgl.app) (`assets/logos/`, dark variants).
Logos are the trademarks of their respective owners.

## Which agents it detects

Exact binary-name match, case-insensitive, against a fixed list:

```
claude  codex  cursor-agent  devin  gemini  ollama
aider   amp    opencode      goose  copilot crush  qoder
```

One list drives both detection and the launcher dropdown (filtered to what's installed).

**Not substring matching.** The previous version matched `python` and `node` as substrings, so a
stray Python helper and `CursorUIViewService` showed up as "agents" with a Kill button beside
them. Every agent CLI worth naming is either a common English word or a common runtime, so
substrings can't be made safe here.

**One row per session, not per process.** Agents fork workers with the same name. Two rules
collapse them: a child of a detected agent belongs to that agent, and two same-named processes
under one non-agent parent are one agent's helpers. `launchd` (pid 1) is exempt from the second
rule — it parents every GUI app and adopts every orphan, so a shared parent of 1 means nothing.
Two `claude` sessions in two terminal tabs have different parents and stay two rows.

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
cargo run --bin stackwatch
```

Install it properly as `StackWatch.app` in `/Applications`:

```bash
CODESIGN_ID="StackWatch Dev" ./package.sh
```

`CODESIGN_ID` matters more than it looks. macOS keys TCC permissions to a bundle's
designated requirement, and for an ad-hoc signature that requirement is the cdhash — a
hash of the code — so every rebuild is a new app as far as the system is concerned and
every permission has to be granted again. With a stable identity the requirement becomes
bundle id plus certificate, and grants survive rebuilds. `package.sh` documents how to
create the self-signed identity; it does not need to be trusted.

It starts **empty** — "No agent / Not running", no token gauge. That's intended, not a bug: the
HUD reports what's actually running, and on a cold start nothing is. Sessions appear two ways.

**Launch from the notch** (this is the one with a terminal). Click the bar → `🚀 + Launch` →
pick an agent from the dropdown, `📁` to browse for a working directory, `Spawn`. The drawer
grows into the terminal panel with the agent already running in it — type your first message
there. The dropdown lists only the CLIs actually installed here (probed at startup across `PATH`
plus the usual nvm/homebrew/cargo locations); `Custom…` takes a free-text command. Launches
resolve to an absolute path and get a full `PATH` passed through, so this works from a `.app`
bundle with no shell environment. If a spawn fails, the tab turns red and a card offers
**Kill it** / **Later**.

**Or just use your agents and let it find them.** Open Claude Code in one project and run a
request, then open Antigravity and run one. Each gets its own tab (the tailer registers one
session per detected log file under `~/.claude/projects`, `~/.gemini/brain`, `~/.cursor/logs`,
`~/.aider`), and the collapsed header follows whichever agent moved most recently — regardless
of which tab is selected. Only writes made *after* the HUD starts count; it never replays
history.

**Clicking anywhere outside collapses it** back to the notch. Nothing is killed — the PTY keeps
running and the session is still in `ACTIVITY` when you open the drawer again.

**To quit:** `Quit` in the drawer or the terminal toolbar. There's no Dock icon or ⌘Q — it's an
AppKit `Accessory` app by design.

Scripted demo (synthetic events, no real agent needed), in a second terminal:

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

`POST /session/launch` takes `{agent_command, working_directory}` and spawns the agent in a PTY.

`POST /ui` opens a pane from outside the app — `{"mode":"collapsed"|"drawer"|"terminal",
"session_id":"..."}`. StackWatch is an `LSUIElement` app with no menu bar and no Dock tile, so
there is nothing for AppleScript or the accessibility APIs to drive; this is the scriptable
surface. It also lets an agent bring its own session to the front.

## Verification

No screen-recording permission was available while building this, so nothing here rests on
looking at a screenshot:

```bash
cargo run --bin check_term      # spawns `top` and the real `claude` in a PTY, asserts they paint
cargo run --bin check_picker    # folder-picker regression check, ~9s
```

`check_term` is the one that matters. A unit test on `echo` output proves nothing about whether
Claude Code renders: a TUI switches to the alternate screen, hides the cursor, addresses cells
directly and repaints in place. `top` exercises exactly those sequences and its `q` key proves
input flows the other way. Measured: `top` paints 29 non-blank rows and quits on `q`; the real
`claude` paints its trust prompt through the parser.

Window geometry was verified with `CGWindowListCopyWindowInfo`, which needs no TCC grant —
collapsed `386×32 at (563,0)`, drawer `606×382 at (453,0)`, terminal `900×652 at (306,0)`, all at
window layer 26 (the menu bar is 24).

What is **not** verified: the painted pixels of the terminal grid — colours, cursor, alignment.
The run-coalescing, wide-glyph handling and inverse-video logic behind it are unit-tested
(`row_segments`), but no one has looked at it on a screen.

## What was broken, and why

The first cut floated in the middle of the screen. Four separate causes, all fixed:

1. **No window position was ever set**, so macOS centred it. Now `NotchGeometry::dock_position`
   computes top-centre and the app sends `ViewportCommand::OuterPosition` on every shape change.
2. **`with_always_on_top` is not enough to reach the notch.** It gives `NSFloatingWindowLevel`
   (3); the menu bar sits at 24, so a window at `y: 0` renders *behind* the notch strip. The
   window level is now raised to `NSStatusWindowLevel + 1` via `objc2`.
3. **The window was a fixed 440×240 transparent box** with a small pill drawn inside it — so the
   invisible margin swallowed clicks meant for other apps. The window is now sized to its content.
4. **The brand badge picked `processes.first()`**, but `sysinfo` iterates a `HashMap` — so a
   stray node process hijacked the badge at random. Detection is now an allowlist, sorted by pid.

## Notes

- On a Mac **without** a notch, `NSScreen::auxiliaryTopLeftArea` is zero-sized and the HUD falls
  back to treating the menu bar as the notch. It then covers the centre of the menu bar — usually
  empty space between the menus and the status items, but it is a real tradeoff.
- Runs as an `Accessory` app: no Dock icon, no app-switcher entry, visible on all Spaces.
- Only sessions StackWatch launched get a terminal. See "Launched vs. detected" above.
