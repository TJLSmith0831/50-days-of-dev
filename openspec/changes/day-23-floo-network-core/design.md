## Context

Floo Network is a cross-machine (personal laptop / work laptop) desktop agent harness built with Rust + Tauri and a React frontend. This change is the first of four sequential OpenSpec changes (`day-23-floo-network-core` → `-executor-handoff` → `-integrations` → `-distribution`) and establishes the foundation the other three build on: durable project/thread/session state, note-taking, and the mode-selection UI chrome. No executor process (`claude`/`codex`) is spawned anywhere in this change — that begins in `day-23-floo-network-executor-handoff`.

Constraints inherited from the project's always-load docs (`day-23-floo-network/AGENTS.md`, `CLAUDE.md`): session storage must live outside any target repo; the harness never writes inside a target project except user-authored notes; session history is append-only, never mutated in place.

## Goals / Non-Goals

**Goals:**
- Persist projects (canonical root path → SHA-256 hash → `~/.floo-network/projects/<hash>/`) and let the user add/switch between them.
- Persist threads within a project (ULID-identified, `.meta.json` sidecar) and let the user create/list/switch/rename them.
- Persist chat/tool history as append-only JSONL (`{seq, ts, role, mode, content}`), fsync per write, tolerant of torn trailing writes on read.
- Deliver end-to-end note-taking: ⌘N/button → command bar → immediate write → Edit/Preview markdown pane.
- Deliver a real, persisted spec/go mode toggle per thread with no process behavior behind it yet.
- Stand up the Tauri + React shell (React, `react-diff-viewer-continued`, `@uiw/react-md-editor`) all of the above render into.

**Non-Goals:**
- No executor spawning, process management, or permission-mode wiring (change 2).
- No Graphify shell-out or Browserbase REST calls — placeholder UI only where relevant (change 3).
- No code signing, auto-update, or installer — run via `pnpm tauri dev` (change 4).
- No multi-user or cloud-sync support (out of scope for the whole project).
- No modification of, or reference to, any existing OpenSpec capability spec, including the 7 stale specs left over from the unrelated, never-built `coding-agent-repl-harness` exploration.

## Decisions

**Session storage: JSONL over SQLite or an embedded KV store.** One append-only file per thread at `~/.floo-network/projects/<project-hash>/threads/<thread-id>.jsonl`. Rejected SQLite: its transactional/query power isn't worth migration-schema overhead for a single-process desktop app with no concurrent writers. Rejected `sled` (embedded KV): weaker inspection tooling than plain JSONL, which is human-greppable/diffable for debugging. Append-only becomes structural (no UPDATE operation exists) rather than convention-enforced.

**Thread IDs: ULID over random UUID.** ULIDs are lexicographically sortable by creation time, so `ls` on a `threads/` directory already orders threads chronologically from the filename alone — no need to open files to sort by creation time.

**Project identity: canonical absolute root path, hashed with SHA-256 hex for the on-disk key.** Collision resistance is irrelevant at this scale; SHA-256 is chosen over a faster non-cryptographic hash (e.g. FNV) purely for ecosystem ubiquity (every language/tool has a SHA-256 implementation on hand, reducing dependency surface).

**Tauri command surface: invoke commands + one event channel, no REST/HTTP layer.** Request/response operations (`list_projects`, `add_project`, `create_thread`, `list_threads`, `append_message`, `read_thread`, `create_note`, `list_notes`, `read_note`) are `#[tauri::command]` invoke calls; a single `thread-updated` event channel covers backend-initiated pushes to the frontend (e.g. a filesystem-level change invoke didn't originate). Rejected a REST/HTTP layer: unnecessary transport complexity for a single-process desktop app where Tauri's IPC already bridges Rust and the webview.

**Note creation: no approval gate.** ⌘N/button → command bar → typed filename → Enter writes the file immediately and opens it in the Edit/Preview pane. Rejected an intermediate Create/Cancel confirmation card (present in an earlier iteration of this design): note creation is a harness UI flow, not a model tool call, so there is no `create_note` tool invocation for an approval gate to guard — the typed filename and Enter keypress already are the user's confirmation. A gate here would ask the user to confirm their own keystroke.

**Mode-selection toggle: real persistence, no process behavior.** Flipping spec/go updates the thread's `currentMode` in `.meta.json` and appends a `role: "tool"` marker message to the thread's JSONL log, using schema this change already defines — it does not spawn or terminate any process. Rejected a purely visual/unwired toggle: real persistence now means `day-23-floo-network-executor-handoff` builds process lifecycle on top of already-tested mode-write behavior instead of building the mode-write path and the harder process-spawning work simultaneously.

**Corrupt JSONL handling: silent-to-user, logged to a new harness-wide log file.** A trailing line that fails to parse (torn write from an unclean shutdown) is dropped from the rendered thread and logged to `~/.floo-network/harness.log` with thread ID and byte offset — no toast or banner. Torn writes are an expected, non-fatal byproduct of crashes/force-quits, not something requiring in-the-moment user action; the log exists for the rare case a data-loss report needs debugging after the fact.

## Risks / Trade-offs

- **[Risk] JSONL has no built-in integrity check beyond per-line JSON parse success — a torn write could in principle leave a syntactically valid but semantically wrong line (e.g. truncated mid-value in a way that still parses) → [Mitigation]** Out of scope for this change; the corrupt-line handling above only covers unparseable lines. Not designed against further here.
- **[Risk] SHA-256 project-hash collisions are not truly checked for, only assumed astronomically unlikely → [Mitigation]** Acceptable given the small realistic number of projects any one user registers (tens, not millions); revisit only if this assumption is ever observed to fail.
- **[Risk] The mode toggle writing real state before an executor exists means change 2 inherits an existing `.meta.json`/JSONL contract it must not break → [Mitigation]** `day-23-floo-network-executor-handoff`'s own decision log should explicitly re-verify the `currentMode`/`role: "tool"` marker schema before extending it, rather than assuming it fits new needs unchanged.
- **[Risk] No REST/HTTP layer means all frontend↔backend communication is Tauri-IPC-specific, which could complicate a future non-Tauri frontend (e.g. web version) → [Mitigation]** Not a goal for this project (personal, desktop-only per the map's out-of-scope section); accepted as a permanent architectural choice, not a temporary shortcut.
