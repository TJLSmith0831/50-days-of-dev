# Day 22 Notch Watcher — Session-Launch Collapse & Ship Pass

## D1: launch_session() lives as a free async function in lib.rs, not an AppState method
- **Decision**: `launch_session(shared_state: &SharedState, payload: &SessionLaunchPayload) -> ...` is a free async function, not `impl AppState`.
- **Why**: AppState methods in this codebase are synchronous mutations taken under the mutex; the notch UI's render loop (`main.rs` `update()`, ~60fps) locks the same mutex every frame. A method holding the lock across `Command::spawn()`'s await would stall the HUD. The free function locks only for `register_session`, releases, then spawns.
- **Source**: user (accepted from recommendation)

## D2: AgentStatus gets a distinct Error variant/color, not reused QuotaWarning styling
- **Decision**: New `AgentStatus::Error` with its own color (darker red, `rgb(200,40,40)`, distinct from the `WARN` coral already used for QuotaWarning) and its own label ("Launch failed").
- **Why**: "Session running low on tokens, still working" (QuotaWarning) and "this session never started" (Error) are different situations for the person watching the notch; identical styling makes them indistinguishable at a glance.
- **Source**: user

## D3: Failed sessions stay in the tab bar — no auto-removal
- **Decision**: A session that fails to launch keeps its tab, marked red/"Launch failed", rather than vanishing.
- **Why**: A vanishing tab loses the record of what was attempted and why it failed, with no path to retry. Visible + dismissible beats silent + gone.
- **Source**: user

## D4: Failure prompt reuses the existing Interactive Permission Prompt card pattern
- **Decision**: Add `pending_launch_failures: Vec<FailedLaunch>` to AppState alongside `pending_permissions`, rendered as a card mirroring the existing Approve/Deny permission card (`main.rs:424-459`), with two actions: "Kill it" (removes the session from `sessions` entirely) / "Later" (dismisses only the prompt queue entry — the tab stays red for the user to deal with whenever).
- **Why**: Structurally the same shape as the existing urgent-decision card (CONTEXT.md's "Interactive Permission Prompt"); reusing it is visual consistency for the user and one rendering path (leverage) in code instead of two.
- **Source**: user

## D5: /session/launch stays HTTP 200 on failure, with a status field in the body
- **Decision**: On spawn failure, the endpoint still returns `200 OK`, with `"status": "failed"` and a reason in the JSON body — not a non-2xx status code.
- **Why**: Matches every other handler in this codebase (`handle_post_event`, `handle_permission_request` always return 200 with outcome in the body); both real callers (egui button, `simulate.rs`) already read the body, not the status code, so this is the smaller, idiom-consistent diff.
- **Source**: user (accepted from recommendation)

## D6: Technical/failure-handling implementation details are delegated, not further interviewed
- **Decision**: User invoked ponytail (lazy-but-correct) mode and handed remaining low-level implementation choices (exact error type shape, method names, etc.) to be decided at build time rather than grilled further — but implementation is paused for now; user wants to keep exploring/scoping before writing code.
- **Why**: User wants to protect their attention for UI/UX and bug-hunting, and get the day-of-dev project to a finished, recordable state — not referee every Rust-level implementation detail.
- **Source**: user

## D7: Scope for "finished, recordable" — ship visible fixes, defer the invisible ones
- **Decision**: In scope for this pass: the session-launch collapse (D1-D5) + a UX sweep for non-intuitive commands. Out of scope, stays tracked-but-deferred in docs/BUGS.md: the other 3 bugs (lock-order test, duplicated agent-type classification, simulate.rs JSON drift).
- **Why**: Those 3 don't show up in a demo recording (comment-only invariant, duplicated match arms, a background simulator binary's JSON shape) — they matter to a future contributor, not to what's on camera. The session-launch flow (click Spawn, see success/failure) is directly what gets recorded.
- **Source**: user

## D8: Add a right-click → "Quit" affordance on the notch
- **Decision**: The app currently has zero in-app way to quit (no Dock icon, no app-switcher entry — it's an `Accessory` app by design; confirmed no "quit"/"exit" reference anywhere in src/*.rs, README.md, or AGENTS.md). Add a right-click context menu on the notch with a "Quit" item.
- **Why**: Without this, the only way to stop the app is `Ctrl+C` in the launching terminal or `killall` — a dead end if demoed from a backgrounded/packaged run. First concrete UX gap found in the non-intuitive-commands sweep.
- **Source**: user

## D9: Session tab strip gets horizontal scroll, not a capped "+N more"
- **Decision**: The tab strip (`main.rs:362-380`) renders sessions in a plain `ui.horizontal` inside a fixed-width allocated rect — no wrap, no scroll, no overflow indicator. Fix: wrap the tab strip in an egui horizontal `ScrollArea` rather than capping to the last N tabs.
- **Why**: Directly hits the flow being recorded — demoing launch success/failure means testing several launches back-to-back (default session + a few test launches per D2-D5), which will overflow the ~646pt expanded width. A capped "+N more" hides sessions with no way to reach them; scroll keeps every tab reachable.
- **Source**: user

## D10: Active-session fallback on kill — any remaining session, else None (no forced placeholder)
- **Decision**: When "Kill it" removes the active session: if other sessions remain, activate any one of them. If none remain, `active_session_id` becomes empty/None — the app does NOT recreate a fake `"claude-default"` placeholder session just to have something active. "No active session" must be a real, renderable state, not papered over.
- **Why**: Forcing a fake default session after the user explicitly killed everything lies about app state — there is no agent running, the UI shouldn't pretend there is. This changes `AppState::default()`'s current behavior (currently always seeds one `"claude-default"` session) and `select_session`'s assumption that `active_session_id` always resolves.
- **Source**: user
- **Follow-on**: `AppState`'s top-level `agent_type`/`status`/`step_description`/`session_limit` fields currently mirror whatever the active session is (see `select_session`, `lib.rs:346`) — with zero sessions, these need a defined empty/idle rendering, and the collapsed-notch header (`label_of(&s.agent_type)`, `status_label(&s.status)`) needs a "no session" display path it doesn't have today.

## D11: Launch form — Cmd becomes a dropdown, Dir gets a native "Browse…" button
- **Decision**: Friction diagnosed to 3 causes (typing exact binary name, typing full directory path, no visible in-UI guidance) — not the extra click to reveal the form. Fixes:
  - **Cmd field**: replace free-text with a dropdown over the existing `AgentType` variants (Anthropic/Gemini/OpenAi/Ollama/Custom, already has `label_of()` display names) — no typos possible. `Custom` keeps a free-text fallback for anything not in the enum.
  - **Dir field**: add a "Browse…" button next to the existing text field that opens a native folder picker via the new `rfd` crate (`rfd::FileDialog::new().pick_folder()`, ~3 lines) — text field stays editable for paste-a-path users.
- **Why**: No lightweight native-picker path exists in the AppKit bindings already installed (`objc2-app-kit`) without hand-writing `NSOpenPanel` FFI boilerplate — `rfd` replaces hand-rolled FFI, not hand-rolled logic, so it earns the new dependency. The Cmd dropdown needs no new dependency at all, just reuses `AgentType`.
- **Why (dropdown over free text)**: eliminates "did I type the binary name right" entirely — the failure mode this whole session-launch collapse (D1-D5) was built to handle only becomes visible if the user gets the command right in the first place; if the command is always valid-by-construction (except Custom), fewer people ever see the failure path.
- **Source**: user
- **Follow-on (undecided)**: need an `AgentType -> actual launch command` mapping (e.g. Anthropic -> "claude") somewhere — doesn't exist today (`match_agent_type_from_name` only goes name->type, not the reverse). Implementation detail, not re-grilled per ponytail scope (D6).

## D12: Prompt cards (permission + launch-failure) get a "+N more waiting" line
- **Decision**: Both the permission-prompt card and the new launch-failure prompt card (D4) only render `.first()` of their respective queues (`main.rs:424`) with no indicator anything else is queued. Add a small "+N more waiting" line under each card when its queue has more than one item.
- **Why**: Same shape as D9's tab-overflow gap — a queued-but-invisible item is a silent UX dead-end. Cheap addition (a length check + one text line), no new interaction needed since items still resolve one at a time.
- **Source**: user

## D13: No fake seeded session on cold start — the HUD opens genuinely empty if nothing is running
- **Decision**: `AppState::default()` must NOT seed a fake `"claude-default"` demo session (currently hardcodes 74,200/100,000 tokens, "Idle - Awaiting task..."). On load, if no real agent sessions exist (nothing launched, nothing detected by the tailer/process scan), the HUD renders the "no session" empty state from D10 — not a placeholder.
- **Why**: User rejected the recommendation to keep the fake session for recording purposes — the empty state must be the honest default, not just a reachable edge case.
- **Source**: user
- **Follow-on**: this removes the only code path that currently guarantees `active_session_id`/`sessions` are non-empty, so D10's "no session" rendering (collapsed-notch header, drawer) is now load-bearing from first paint, not just a post-kill edge case. Existing tests asserting `AgentStatus::Idle` / the default session (e.g. `tests.rs:7`) will need updating to match the new empty default.

## D14: AgentType -> launch command mapping for the Cmd dropdown (D11)
- **Decision**: `Anthropic -> "claude"`, `Gemini -> "gemini"`, `OpenAi -> "codex"`, `Ollama -> "ollama"`, `Custom -> free-text field shown instead of a fixed command`.
- **Why**: Matches the substring conventions `match_agent_type_from_name` (`lib.rs:190-203`) already uses to classify these binaries back to a type, so picking a dropdown entry and launching it round-trips through the same classifier without a mismatch.
- **Source**: recommended-accepted (codebase-informed, lib.rs:190-203)
- **AMENDED at implementation (2026-08-02)**: the round-trip premise was false for one entry — `match_agent_type_from_name` matched `openai`/`gpt`/`chatgpt` but **not** `codex`, so an OpenAI dropdown pick classified back as `Custom` (purple "Agent" tab instead of the OpenAI accent). Caught by `test_command_of_round_trips_through_the_name_classifier`. Fix: added `codex` to the OpenAi branch of `match_agent_type_from_name` rather than changing the command to `openai` (no such binary exists; `codex` is the real OpenAI CLI). The decision's command mapping is unchanged; the classifier now actually satisfies its stated rationale, and a test enforces the round-trip for every non-`Custom` variant.

## D15: Collapsed header also renders the empty state, not just the tab strip
- **Decision**: The always-visible collapsed header (status dot, agent label, status text, token gauge — `main.rs:305-343`) must show a genuine empty state ("No agent running", dim/neutral dot, no gauge) when `sessions` is empty, not just the expanded drawer's tab row.
- **Why**: Drafting design.md surfaced that the header reads separate top-level `AppState` fields (`agent_type`/`status`/`step_description`/`session_limit`) independently of the `sessions` map — removing the seeded session (D13) alone only empties the tab strip, leaving the header showing fake "Claude — Ready" data. User confirmed "no sessions should appear in the HUD" means the whole HUD, including the header.
- **Source**: user

## SCOPE EXPANSION (during design.md drafting): passive multi-session tracking

Discovered while drafting design.md, not part of the original architecture review. User's actual demo plan is: open Claude Code, run a request; open Antigravity, run a request; watch the HUD track both simultaneously. Traced `start_universal_tailer` (`tailer.rs:173-201`): it watches multiple files (one per source dir: `~/.claude/projects/*`, `~/.cursor/logs`, `~/.gemini/brain`, `~/.aider`) but every event from every file calls `apply_event`, which writes into the SAME single top-level `AppState` fields — no per-file/per-session tab is ever created for passively-detected sessions (only `register_session`, used by the Launch button, creates a tab). Two real concurrent agents would fight over one shared header with no separate tabs. This is now explicitly in scope for this change.

## D16: Passive session identity — session_id = file path, agent_type = source directory, agent_name = static label per source
- **Decision**: For sessions discovered via the tailer (not launched via the HUD), `session_id` = the file's path (already the stable unique key in `file_offsets`); `agent_type` = derived from which top-level directory the file lives under (`~/.claude/projects/` → Anthropic, `~/.gemini/brain/` → Gemini, `~/.cursor/logs` → Custom, `~/.aider` → Custom) via a small path→type lookup next to `scan_log_directories`; `agent_name` (tab label) = a static label per source dir ("Claude Code", "Antigravity", "Cursor", "Aider") rather than parsed from JSONL content.
- **Why**: `parse_jsonl_line` only sets `agent_type` when the JSON line itself has an `"agent_type"` key (`tailer.rs:110-120`) — real Claude Code/Antigravity transcript lines never do (they use `role`/`type`), so file location is the only reliable signal. Deriving type from location (not content) is a second, independent classifier from the existing content-based one — deliberately not reusing/duplicating the already-deferred content-classification logic (bug #3 in docs/BUGS.md).
- **Source**: user

## D17: Passively-tracked sessions never auto-expire
- **Decision**: A tab created from tailer-detected activity never automatically disappears or reverts to Idle when its file stops updating. No staleness timeout/heuristic. Same "Kill it" action (D4) is the only way to remove it, reused rather than inventing a second removal mechanism.
- **Why**: There's no process handle for a passively-detected session (only a file), so there's no clean "it exited" signal — only "it stopped changing," which needs a timeout guess (30s? 5 min?) that risks flipping a tab to "ended" mid-demo just because the agent paused to think.
- **Source**: user

## D18: Collapsed header follows the most-recently-updated session
- **Decision**: With multiple sessions active, the always-visible collapsed header (status dot, agent label, status text, gauge) auto-follows whichever session most recently reported activity — via either `/event` or a tailer-detected file update. Clicking a tab (`select_session`) still independently controls what the *expanded drawer* shows in detail; it does not need to also drive the header.
- **Why**: For the planned demo (open Claude Code, run a request; open Antigravity, run a request), the header visibly reacting to whichever agent just did something is the point of the shot — no manual tab-clicking needed to "follow" the action.
- **Source**: user
- **Follow-on**: needs a `last_updated` timestamp (or equivalent ordering signal) per `SessionState` so "most recent" is determinable — doesn't exist on `SessionState` today (`lib.rs:250-259`). Implementation detail, left to grill-apply per D6.

## D19: Tailer seeds new files at their current length, not offset 0 (skip historical replay)
- **Decision**: `file_offsets` seeds a newly-seen file's offset to its current length on first sight, not `0`. The tailer only reads new writes going forward (standard `tail -f` semantics), never replaying a file's full history.
- **Why**: Found while writing design.md — with per-file session registration (D16), replaying full history on cold start (today's behavior, `tailer.rs:180`, `.or_insert(0)`) would spawn a permanent tab for every old, dormant Claude Code project directory the first time the app runs, flooding the tab strip with history instead of showing only what's actually active.
- **Source**: recommended-accepted (technical/correctness, delegated per D6)

## D20: the folder picker runs synchronously on the UI thread (amends design.md's Risks mitigation)
- **Decision**: `rfd::FileDialog::new().pick_folder()` is called directly in the egui button handler, not on a background thread/task as design.md's Risks section proposed.
- **Why**: the mitigation was written against a premise that doesn't hold. `NSOpenPanel` is a *native modal* — on macOS `rfd` dispatches it to the main thread and blocks there regardless of which thread calls it, so moving the call off the UI thread does not keep the HUD repainting; it only adds a cross-thread write-back path for the result and a dispatch-deadlock risk if the main runloop stalls. The HUD pausing while a modal folder picker is open is normal, expected behavior in every egui app, and the user is looking at the picker, not the notch.
- **Source**: recommended-accepted (technical, delegated per D6)

## D21: ACTIVITY section deleted from the drawer
- **Decision**: The `ACTIVITY` block (section header + the current session's `step_description` galley) is removed from the expanded drawer entirely. `step_description` is still tracked in state and served by `GET /state`; it just isn't painted.
- **Why**: Seen live during the test drive — "Nobody is going to read that tiny text." It was 10pt monospace of raw transcript text, and its galley height was unbounded while the layout advanced `y` by a fixed 24pt, so a long or multi-line step description overran the SESSION and LOCAL AGENTS rows below it. Deleting the section fixes the overflow bug and the value problem in one move.
- **Source**: user (observed live, 2026-08-02)

## D22: token gauge measures real context fill, and grows its own denominator
- **Decision**: Two changes to token accounting for passively-tracked sessions. (a) `parse_jsonl_line` sums a transcript line's whole `usage` block (`input_tokens + cache_creation_input_tokens + cache_read_input_tokens + output_tokens`) when one is present, falling back to the old single-key search otherwise. (b) A session's `token_limit` starts at a per-agent context window (`context_window_of`: Anthropic 200k, everything else 100k) and jumps to 1,000,000 if observed usage ever exceeds it.
- **Why**: Reported live — "Session isn't updating for my subscription based Claude Code session." The old `find_u64` over `["tokens_used","tokens","output_tokens","input_tokens"]` returned whichever key it reached first depth-first, in practice the per-message `output_tokens` (a few hundred), so the gauge jittered between ~200 and ~600 and looked frozen. Real measured context fill on the live session was 223,285 tokens — which also proved the flat 100k limit wrong, and then the 200k assumption wrong (this session is on a larger tier). Rather than hard-code a window the transcript never states, the limit grows to the next real tier so the gauge never pins at a false 100%.
- **Source**: user-reported symptom, recommended-accepted fix

## D23: LOCAL AGENTS lists one row per agent, not per OS process
- **Decision**: `scan_system_agents` skips processes whose name contains `helper`/`renderer`/`plugin`/`gpu`/`crashpad`, and `update_detected_processes` keeps only the first (lowest-pid) process of each distinct name.
- **Why**: Reported live — "I don't believe I have three local claude agents running." The scan was returning 39 processes: one Claude desktop app plus twelve of its Electron helper subprocesses, four forked `claude` workers, and a dozen bare `node`/`python` matches. The top-3 display showed `Claude`, `Claude Helper`, `Claude Helper` — three rows for one app. Now shows `Claude`, `claude`, `ollama`.
- **Source**: user (observed live, 2026-08-02)

## D24: popup surfaces get an opaque fill
- **Decision**: `Visuals::window_fill` is set to the HUD's `CARD` color (with a `TRACK` stroke) instead of `Color32::TRANSPARENT`; only `panel_fill` stays transparent.
- **Why**: Reported live — "this dropdown shouldn't be transparent haha." Both fills were set transparent to let the hand-painted notch card show through, but `window_fill` is also what egui paints popup frames with, so the new Cmd dropdown rendered as a ghost with the launch-failure card legible straight through it. `panel_fill` alone is what the HUD's own transparency actually needs.
- **Source**: user (observed live, 2026-08-02)

## D25: the drawer shows CONTEXT fill; plan/5-hour usage is not shown at all
- **Decision**: The `SESSION` block is renamed `CONTEXT` and shows only context-window fill. The `$X spent` / `resets in Yh Zm` row is deleted. The HUD does not display 5-hour, weekly, or credit usage.
- **Why**: Reported live — "the Session usage doesn't match what I'm actually seeing… I'm talking session usage ie hitting my 5 hour rate limit." Two separate problems. (a) The `$0.14 spent` and `resets in 2h 14m` were `SessionLimit::default()` constants that no code path ever updated — hardcoded fiction, the same failure D13 removed from the seeded session. (b) The real 5-hour/weekly numbers are genuinely unobtainable locally: they aren't in the transcripts (only a `usage` block per message), aren't cached under `~/.claude` (`.credentials.json` holds a `rateLimitTier` string and nothing live), and there's no `claude usage` subcommand to shell out to. Claude Code reads them from `anthropic-ratelimit-unified-*` response headers at request time. Verified rather than assumed. Context fill is the one usage number a transcript does report — and the HUD's 22.3% matched Claude Code's own "Context window 215.9k / 1.0M (22%)" panel exactly.
- **Rejected**: (1) polling the Anthropic API with the OAuth token out of `.credentials.json` — real numbers, but undocumented endpoint, uses stored credentials, and a request per poll; (2) a locally-computed rolling 5-hour token sum across tailed transcripts — no credentials and genuinely useful, but a proxy that would not match the server-side percentage, so a HUD claiming "60%" next to Claude Code's different 60% is worse than showing nothing.
- **Source**: user (chose "ship context % only" over both alternatives, 2026-08-02)

## D26: launch form offers only CLIs installed here, launched by absolute path (amends D11/D14)
- **Decision**: At startup the app probes for `KNOWN_AGENT_CLIS` (`claude`, `devin`, `gemini`, `codex`, `ollama`, `cursor-agent`, `aider`) and the Cmd dropdown lists only the ones found, plus a `Custom…` free-text fallback. Probing searches `PATH` **plus** `/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`, `~/.bun/bin`, `~/.cargo/bin`, `~/.volta/bin` and every `~/.nvm/versions/node/*/bin`. Launches spawn the resolved **absolute path**, not the bare name. Supersedes D14's static `AgentType → command` mapping; `command_of` is deleted.
- **Why**: Asked for directly — "Don't offer spawning agents that don't exist on the machine." Offering `gemini` on a machine without it converts a dropdown pick into a guaranteed launch failure, which is exactly the friction D11 set out to remove. Tracing it surfaced a second, worse bug: a `.app`-bundled or Finder-launched HUD inherits the bare system `PATH`, not the user's shell `PATH` — so `Command::new("claude")` fails to spawn even though `claude` is installed (under nvm, in this case). Absolute-path resolution fixes the dropdown and the `POST /session/launch` path at once, in one function both callers already route through.
- **Note**: Devin is offered but has no `AgentType` variant, so it renders as `Custom` (purple, labelled "Agent"). Adding a branded variant is a ~5-line follow-up, not done here.
- **Source**: user

## D27: brand marks from svgl.app replace the agent name in the collapsed header
- **Decision**: The collapsed header paints the agent's brand logo (15×15) where `label_of()`'s text used to go. Assets live in `assets/logos/` — `anthropic`, `gemini`, `openai`, `ollama`, `cursor` — pulled from svgl.app, dark-background variants. `egui_extras` with the `svg` feature is added so `resvg` rasterizes them crisply at any scale. `AgentType::Custom` has no mark and falls back to the text label.
- **Why**: Asked for directly — "can you please include the icons from svgl.app… important to me from a UI perspective." It's also what the crate already promised: the package description says "brand logos". A logo reads at a glance in a 32pt strip in a way an 11.5pt word doesn't.
- **Trade-off**: one more dependency, and `resvg` is not small. Accepted because the mark scaling cleanly across notch geometries is the point; pre-rasterized PNGs would be lighter but lock in one size. Logos are third-party trademarks bundled for a personal demo project.
- **Source**: user

## D28: narrower collapsed HUD, no expand chevron
- **Decision**: Collapsed shoulder width drops 150 → 100 (expanded 230 → 210), and the `▴`/`▾` chevron is removed from the right shoulder.
- **Why**: Both reported live. The bar sits in the same strip as the macOS menu-bar extras and was covering them — "too wide and I can't see some stuff on my main bar." And the chevron was rendering as a tofu box (`□`): egui's default font has no glyph for `▴`/`▾`. Bundling a font for one arrow isn't worth it, and the whole bar is already the click target, so the affordance is redundant.
- **Source**: user (observed live, 2026-08-02)

## D29: the egui thread gets a tokio `Handle`; the folder picker uses the async dialog
- **Decision**: `main` builds the tokio runtime itself, spawns the HTTP server and tailer onto it, leaks it for the app's lifetime, and hands a `Handle` to `NotchWatcherApp`. Button handlers call `self.rt.spawn(...)`, never bare `tokio::spawn`. The Browse button uses `rfd::AsyncFileDialog` and writes its result into a shared slot the next frame drains, instead of `rfd::FileDialog` (sync).
- **Why**: Two crashes found by auditing the buttons on request. (1) **Spawn was dead** — the runtime lived on a worker thread while the handler ran on the egui main thread, so `tokio::spawn` panicked with "must be called from the context of a Tokio 1.x runtime". Pre-existing, inherited from the original duplicated launch code, and invisible until someone actually clicked it. (2) **Browse beachballed** — reported live. `rfd::FileDialog::pick_folder` runs `NSOpenPanel::runModal`, which spins a *nested* native run loop, and the handler is already executing inside winit's event callback; that reentrancy wedges the loop. `AsyncFileDialog` presents via a completion handler and leaves the loop turning.
- **Amends D20**, which was wrong on its central claim. D20 argued a background thread bought nothing because the modal blocks the main thread either way — true but irrelevant. The real failure isn't a stalled repaint, it's event-loop reentrancy, and the async dialog is the only thing that avoids it.
- **Source**: user ("Double check all buttons are functioning. Hitting the folder button causes it to hang")

## D30: Quit is a drawer button, not only a context menu (amends D8)
- **Decision**: The expanded drawer's tab row gains a right-aligned `Quit` button. The right-click context menu stays.
- **Why**: Found while auditing the buttons. An egui context menu is an `Area` clipped to the viewport, and the *collapsed* viewport is exactly 32pt tall — there is nowhere for the menu to draw. So D8's affordance silently did nothing in the one state the HUD spends most of its time in. The context menu still works with the drawer open; the button works always, and is discoverable without knowing to try a right-click.
- **Source**: recommended-accepted (correctness, found during the button audit)

## Open threads (not yet settled)
- Non-intuitive commands / UX rough edges catalogue: D8 (no quit affordance), D9 (tab overflow), D10 (no-session empty state), D11 (launch form friction), D12 (prompt-card queue indicator), D13 (honest empty cold-start), D15 (header empty state). Sweep looks complete for a first pass.
- Remaining technical shapes (LaunchError enum, FailedLaunch struct, exact method names, SessionState.last_updated) intentionally left to grill-apply/implementation time per D6 — not proposal-blocking.
