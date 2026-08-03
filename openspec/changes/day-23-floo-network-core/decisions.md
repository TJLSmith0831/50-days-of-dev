# day-23-floo-network-core — Decision Log

Change 1 of 4 (per D14): project/thread/session data model, Tauri+React
shell, mode selection UI. No executor spawning — that's change 2
(`day-23-floo-network-executor-handoff`).

Full cross-cutting decision history lives at
`openspec/explore/day-23-floo-network.md` (D1–D17). This file carries
forward only the D-numbers this change draws on, plus this change's own
proposal/design/task-level decisions. Don't re-litigate a carried-forward
D-number here — amend it at the source if it turns out wrong.

## Carried forward from the shared log

- **D1** — day-23 is completely unrelated to the 7 stale `coding-agent-repl-harness` capability specs; this change does not reference, modify, or formally remove them. It authors its own capability set from scratch (see C3). Modified Capabilities section stays empty.
- **D3** — React + `react-diff-viewer-continued` + `@uiw/react-md-editor`. (Diff viewer isn't exercised until change 2/3, but the dependency is installed now as part of the shell.)
- **D4** — JSONL session storage, `{seq, ts, role, mode, content}`, append+fsync per message.
- **D5** — project identity (SHA-256 of canonical root path), `~/.floo-network/projects.json` + `projects/<hash>/project.json` + `threads/<ulid>.jsonl` + `.meta.json` sidecar.
- **D10** — note-creation UX (⌘N / sidebar button → command bar → immediate write + open in Edit/Preview pane, no approval card). Notes storage location is this change's scope even though the full note-taking polish may extend into change 3.
- **D14** — this is change 1 of 4; scope stops at data model + shell + mode selection, no executor process spawning.
- **D15** — testing tiers: `cargo test` unit tests for pure logic (project hashing, JSONL parsing, path resolution), fake-executor integration tests (not exercised yet — no executor in this change), Playwright E2E for critical UI flows relevant to this change (mode toggle, note creation, project/thread switching).
- **D17** — distribution/packaging is an explicit non-goal for this change.

## C1: What does "done" look like for this change?
- **Decision**: `pnpm tauri dev` opens a window; user can add a project (root path picker), create/switch threads within it, see the mode toggle (spec/go) in the UI even though go-mode does nothing yet, create a note via ⌘N and see it in the Edit/Preview pane — and all of that survives an app restart (reads back correctly from `~/.floo-network/`). Chat pane can display messages but nothing generates them — no executor, no LLM calls at all in this change.
- **Why**: Defines the concrete handoff point to change 2 — data model + shell + UI chrome all working and durable, with the executor boundary left completely untouched so change 2 has a clean seam to build on.
- **Source**: recommended-accepted

## C2: Non-goals for this change beyond D17?
- **Decision**: No executor spawning at all (change 2's scope, per D14). No Graphify or Browserbase integration — placeholder tabs/panes are fine, but no actual shell-out or REST calls (change 3's scope). No multi-user/cloud sync (already a whole-project non-goal per map.md, restated here for this change's proposal.md).
- **Why**: Keeps grill-apply from drifting into change 2/3 territory while implementing change 1; the placeholder-UI allowance for Graphify/Browserbase means the shell doesn't need later rework to add tabs, just to wire them up.
- **Source**: user

## C3: What new capabilities does this change introduce?
- **Decision**: Five — `project-management` (root-path hashing, global index, add/switch project), `thread-management` (create/list/switch/rename threads, `.meta.json` sidecar), `session-storage` (JSONL append/read, corrupt-line handling), `note-taking` (⌘N → command bar → write → Edit/Preview pane), `mode-selection` (spec/go toggle UI state, no executor wiring yet). Each becomes its own `openspec/specs/<name>/spec.md`.
- **Why**: Kept project and thread as separate capabilities rather than merged, since they have distinct requirement sets (project identity/hashing vs. thread lifecycle/mode-per-message) even though threads always live inside a project — separate specs make each independently reviewable and each maps cleanly to one of D15's testable tiers.
- **Source**: recommended-accepted

## C4: What's the Tauri command surface between the Rust backend and React frontend?
- **Decision**: Standard Tauri `#[tauri::command]` invoke calls for request/response operations — `list_projects`, `add_project`, `create_thread`, `list_threads`, `append_message`, `read_thread`, `create_note`, `list_notes`, `read_note` — called from React like async functions. One Tauri event channel (`thread-updated`) for backend-initiated pushes back to the frontend. No REST/HTTP layer.
- **Why**: Tauri's IPC is the only transport a single-process desktop app needs; invoke covers request-driven CRUD, the one event channel covers the one case (backend-side filesystem change) invoke can't push for.
- **Source**: recommended-accepted

## C5: How does the mode-selection UI represent spec/go before any executor exists?
- **Decision**: The toggle is fully functional as UI state — flipping it updates the thread's `currentMode` in `.meta.json` (D5) and appends a `role: "tool"` marker message to the thread's JSONL log (D4's existing schema already supports this). It does not spawn or terminate any process, since no executor exists until change 2.
- **Why**: Real persistence now means change 2 builds executor process lifecycle on top of already-tested mode-write behavior, rather than starting the mode-write path from zero alongside the harder executor-spawning work.
- **Source**: recommended-accepted

## C6: How is a corrupt/torn trailing JSONL line surfaced?
- **Decision**: Logged to a new rotating log file at `~/.floo-network/harness.log` (thread ID + byte offset), silent to the user — the UI renders the thread normally from its good lines, no toast or banner.
- **Why**: Torn writes are an expected byproduct of unclean shutdowns (crash, force-quit), not a user-actionable error in the moment; the log file exists so a rare data-loss report can be debugged after the fact without cluttering the UI for a background/non-fatal condition.
- **Source**: user

## C7: What order do the task groups build in, and what's riskiest to front-load?
- **Decision**: 1) Tauri+React scaffold (new stack combo for this repo — riskiest tooling unknown, done first). 2) `session-storage` (JSONL append/read/fsync/corrupt-line handling — foundational, everything else depends on it). 3) `project-management` (depends only on scaffold). 4) `thread-management` (depends on project-management + session-storage). 5) `note-taking` and `mode-selection` in parallel (both depend on thread-management, independent of each other). 6) Playwright E2E + final wiring/polish once all pieces exist to test against.
- **Why**: Front-loads the two highest-risk/highest-leverage pieces (unfamiliar tooling, foundational data format) before anything else can be blocked by surprises in either.
- **Source**: user

## C8: Where under the project root do notes live?
- **Decision**: `<project-root>/notes/<name>.md`. The filename typed in the command bar is resolved relative to that directory, `.md` is appended when no extension is given, and any name whose path components aren't all plain names (`..`, absolute paths) is rejected outright.
- **Why**: `note-taking`'s spec says "a path under the active project's notes location" without naming one, and AGENTS.md only says notes are files inside the project root. A single `notes/` directory is the obvious reading and keeps note writes to one predictable, greppable place. The component check is a trust boundary, not a convenience — the harness must never write outside the project root, so a traversal-shaped name is an error rather than something to normalize.
- **Source**: recommended-accepted

## C9: How are the critical UI flows verified end-to-end?
- **Decision**: Drive the real running Tauri app through the Tauri MCP bridge (`tauri-plugin-mcp-bridge`, debug-only dependency, registered under `cfg(debug_assertions)`) instead of Playwright. This amends C7's step 6 and D15's tier-3 ("Playwright E2E") for this change and all later day-23 changes.
- **Why**: Playwright drives Chromium/Firefox/WebKit browsers, not the WKWebView that Tauri embeds on macOS, so a Playwright suite could only ever have tested the Vite dev server with `invoke` stubbed — the Rust backend, the actual thing at risk, would go unexercised. The MCP bridge drives the shipped binary with its real backend, which is strictly more coverage for less setup. Cost: these are agent-driven interactive checks, not a suite that reruns in CI — acceptable, since this repo has no CI by design and each day's entrypoint run is the check.
- **Source**: user

## C10: What happens when a message is appended after a torn write?
- **Decision**: Before appending, if the log is non-empty and does not end in a newline, write the missing newline first, so the new message starts its own line.
- **Why**: Found while implementing §2 — the torn-line recovery test showed that appending onto a file whose last line was truncated mid-write concatenated the new message onto the broken one, producing a single unparseable line and silently losing the *new* message too. C6 covers dropping a torn line on read; it does not cover the write path turning one lost message into two. Closing the line off first bounds the damage to the one message that was already lost.
- **Source**: recommended-accepted

## C11: Rename uses the note command bar, because `window.prompt` does nothing in Tauri
- **Decision**: Project rename and thread rename open the same floating command bar that ⌘N uses, prefilled with the current name. The bar is now driven by one piece of state (`{ label, value, submit }`) with three callers — new note, rename project, rename thread — instead of a boolean plus two `prompt()` calls.
- **Why**: Found by finally exercising the flows. Both Rename buttons were **dead**: `window.prompt` exists in Tauri's WKWebView but returns `null` immediately without ever showing a dialog, so `if (!name?.trim()) return;` swallowed every rename. Tasks 3.6 and 4.6 claimed these flows worked; the Rust commands were unit-tested and correct, but nothing in the UI could reach them. This is the failure mode unit tests can't see and a screenshot won't either — the button looks fine, it just does nothing. Reusing the command bar was also the smaller diff than adding a modal: one state field replaced a boolean, and the note flow got prefill support for free.
- **Source**: recommended-accepted

## Open items for this change (to grill)

(none)
