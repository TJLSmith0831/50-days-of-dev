## 1. Scaffold

- [x] 1.1 Initialize the Tauri + React project under `day-23-floo-network/` (Vite/React template), with `day-23-floo-network/package.json` (`"private": true`, `start` script) and `AGENTS.md`/`CLAUDE.md` commands updated if they drift from what actually works
- [x] 1.2 Add frontend dependencies: `react-diff-viewer-continued`, `@uiw/react-md-editor`
- [x] 1.3 Add Rust crate dependencies for SHA-256 hashing, ULID generation, and JSON(L) serialization
- [x] 1.4 Verify `pnpm install && pnpm tauri dev` opens an empty window (`cargo test` with no tests yet passes trivially)

## 2. Session storage

- [x] 2.1 Implement JSONL append: write `{seq, ts, role, mode, content}` + newline, fsync before returning (per `session-storage` spec)
- [x] 2.2 Implement JSONL read: parse line by line in `seq` order
- [x] 2.3 Implement torn-trailing-line handling: drop unparseable final line, log thread ID + byte offset to `~/.floo-network/harness.log`, return remaining messages
- [x] 2.4 `cargo test` unit tests: append-then-read round trip, monotonic `seq` ordering, torn-trailing-line recovery (per D15 tier 1)

## 3. Project management

- [x] 3.1 Implement canonical-path resolution + SHA-256 hex project hashing
- [x] 3.2 Implement `~/.floo-network/projects.json` global index read/write (add project, list projects)
- [x] 3.3 Implement `add_project`, `list_projects` Tauri commands (per design.md's command surface)
- [x] 3.4 Implement display-name rename (updates `project.json` + global index, leaves hash unchanged)
- [x] 3.5 `cargo test` unit tests: path→hash determinism, duplicate-add reuses existing entry, rename leaves identity unchanged (per D15 tier 1)
- [x] 3.6 Frontend: project picker (add/switch/rename), wired to the commands above

## 4. Thread management

- [x] 4.1 Implement ULID thread creation with `.meta.json` sidecar (`currentMode: "spec"`, `openSpecChangeName: null` on creation) and empty `.jsonl` log
- [x] 4.2 Implement thread listing (read all `.meta.json` sidecars for the active project)
- [x] 4.3 Implement thread rename (title + `updatedAt`)
- [x] 4.4 Implement `create_thread`, `list_threads`, `append_message`, `read_thread` Tauri commands (per design.md's command surface), wiring session-storage (§2) underneath
- [x] 4.5 `cargo test` unit tests: thread creation produces valid sidecar + empty log, listing reflects sidecars accurately
- [x] 4.6 Frontend: thread list/switch/rename UI, chat pane rendering messages read via `read_thread` (no message generation in this change)

## 5. Note-taking

- [x] 5.1 Implement `create_note`, `list_notes`, `read_note` Tauri commands
- [x] 5.2 Frontend: ⌘N shortcut + sidebar "Create note" button opening the command bar
- [x] 5.3 Frontend: command bar filename input → Enter writes immediately (no approval step) → opens in two-tab Edit/Preview pane (`@uiw/react-md-editor`)
- [x] 5.4 Frontend: auto-save on hand-edits to an already-created note, no re-prompt

## 6. Mode selection

- [x] 6.1 Implement mode-toggle write path: update `.meta.json` `currentMode` + append `role: "tool"` marker message to the thread's JSONL log (per `mode-selection` spec)
- [x] 6.2 `cargo test` unit test: toggling mode updates sidecar and appends exactly one marker message, no process spawn side effects
- [x] 6.3 Frontend: spec/go toggle UI per thread, wired to the mode-toggle command, reflecting `currentMode` on load

## 7. Integration and end-to-end verification

- [x] 7.1 Fire up `pnpm tauri dev` and manually walk the full flow: add project → create thread → toggle mode → create note → edit note → restart app → confirm everything persisted correctly
- [x] 7.2 Tauri MCP E2E (per C9): mode toggle persists across a reload
- [x] 7.3 Tauri MCP E2E (per C9): note creation flow (⌘N → type name → Enter → note appears, opens in editor)
- [x] 7.4 Tauri MCP E2E (per C9): chat send/receive rendering (send a message via `append_message`, confirm it renders in the pane after `read_thread`)
- [x] 7.5 Confirm `openspec/changes/day-23-floo-network-core` `openspec status` shows all tasks complete before archiving
