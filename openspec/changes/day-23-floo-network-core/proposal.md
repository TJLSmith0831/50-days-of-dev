## Why

Floo Network (day 23 of the 50-days-of-dev challenge) needs a durable, cross-machine (personal + work laptop) desktop harness that carries multiple projects and conversation threads, before any executor handoff logic can be built on top of it. This change delivers that foundation — data model, Tauri+React shell, and UI chrome — as an independently buildable, independently testable slice.

## What Changes

- Add project registration and switching: canonical root-path identity, SHA-256-hex on-disk key, global `~/.floo-network/projects.json` index.
- Add thread lifecycle within a project: ULID-identified threads, create/list/switch/rename, `.meta.json` sidecar (title, timestamps, current mode, `openSpecChangeName` placeholder for future changes).
- Add JSONL session storage: append-only `{seq, ts, role, mode, content}` records per thread, fsync per write, corrupt-trailing-line handling on read.
- Add note-taking UX: ⌘N or sidebar button → command bar → immediate write (no approval gate) → opens in a two-tab Edit/Preview markdown pane.
- Add the spec/go mode-selection UI: a toggle reflecting the thread's current mode, with no executor behind it yet — go-mode is visually present but functionally inert until change 2.
- Scaffold the Tauri + React application shell (React, `react-diff-viewer-continued`, `@uiw/react-md-editor`) that the above render into.

## Capabilities

### New Capabilities

- `project-management`: canonical-path project identity, SHA-256 on-disk hashing, global project index, add/switch active project.
- `thread-management`: thread create/list/switch/rename within a project, `.meta.json` sidecar schema and lifecycle.
- `session-storage`: JSONL append-only message log format, per-message fsync, corrupt-line handling on read.
- `note-taking`: end-to-end note creation flow (⌘N/button → command bar → write → Edit/Preview pane) and subsequent auto-saving hand-edits.
- `mode-selection`: spec/go toggle UI state per thread, independent of any executor process.

### Modified Capabilities

None. This change does not reference, modify, or formally remove any existing spec, including the 7 stale capabilities left over from the unrelated, never-built `coding-agent-repl-harness` exploration.

## Impact

- New Rust + Tauri backend and TypeScript/React frontend under `day-23-floo-network/` — no existing code in this repo is modified.
- New runtime dependency surface: Tauri, React, `react-diff-viewer-continued`, `@uiw/react-md-editor`, plus Rust crates for SHA-256 hashing, ULID generation, and JSON(L) serialization.
- New on-disk state outside the repo: `~/.floo-network/` (projects index, per-project directories, thread JSONL logs and sidecars). Nothing written inside any target project repo except user-authored notes (per `note-taking`).
- No executor (`claude`/`codex`) process is spawned by this change — chat pane can render messages but nothing in this change generates them.
- No network calls in this change (Graphify/Browserbase integration is change 3, `day-23-floo-network-integrations`).
- No distribution/packaging in this change (change 4, `day-23-floo-network-distribution`) — run via `pnpm tauri dev` only.
