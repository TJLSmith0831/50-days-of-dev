# Day 23 — Floo Network — Decision Log

Cross-machine agent harness (Rust + Tauri, TypeScript frontend): one executor
(Claude Code or Codex CLI) drives both spec-mode (read-only/plan) and go-mode
(write-enabled), with project threads, session history, and Graphify code
maps as first-class concepts. See `day-23-floo-network/AGENTS.md` and
`CLAUDE.md` for the always-load context this log must not contradict.

## D1: Do the 7 stale capability specs (agent-loop, session-management, tool-system, claude-code-handoff, context-management, grilling-integration, repl-interface) from the archived `2026-07-17-coding-agent-repl-harness` change conflict with this change?
- **Decision**: That Python/Ollama/SQLite/Rich-REPL design was never built — it's a fully abandoned direction. Day 23 is completely separate from those specs, not a replacement or descendant of them: no OpenSpec-formal supersession/removal, no Modified Capabilities entries referencing them, no framing of day-23's capabilities as "the replacement for" any of the 7. Day-23 changes simply author their own capability set from scratch and never reference the old 7 at all. Whether/when to clean up the stale specs as dead housekeeping is a separate, later, out-of-band decision — not something any day-23 change does as part of its own scope.
- **Why**: User corrected the initial framing — treating them as a formal replacement relationship (even via a REMOVED delta) would wrongly imply lineage/continuity between an abandoned exploratory design and day-23, when in fact they're just unrelated. Not touching them at all is the accurate representation.
- **Source**: user (revised after initial framing was corrected)

## D2: Is "Ponytail" part of the handoff invocation the harness makes?
- **Decision**: No. Ponytail (github.com/DietrichGebert/ponytail) is a minimal-code ruleset plugin installed inside Claude Code/Codex via their own plugin managers — a one-time per-machine setup, not a binary the harness invokes. The harness only checks the detected executor has it installed before handoff and warns if missing.
- **Why**: Avoids the harness trying to manage another program's plugin system, which it has no mechanism to do.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/01-ponytail-vs-grill-apply.md)

## D3: What frontend framework and component libraries render the Tauri UI?
- **Decision**: React, with `react-diff-viewer-continued` (code diff view) and `@uiw/react-md-editor` (notes edit+preview). Chat pane is a plain scrollable list, no library. Vite and state management are grill-apply implementation details, not gated here.
- **Why**: React has the deepest ecosystem for the diff-view and markdown-editor components this UI specifically needs, vs. thinner Svelte/Solid equivalents that would mean more custom-build work.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/02-frontend-stack.md)

## D4: What's the session history storage format?
- **Decision**: JSONL, one file per thread, at `~/.floo-network/projects/<project-hash>/threads/<thread-id>.jsonl`. Record shape: `{seq, ts, role, mode, content}` — `seq` monotonic per-thread integer, `role` is `user | assistant | system | tool`, `mode` is `spec | go`. Append the line + fsync after every message. A trailing line that fails to parse on read is treated as a torn write (dropped, logged, not fatal).
- **Why**: Append-only is structural (no UPDATE operation exists) rather than convention-enforced; no schema-migration story needed; human-greppable/diffable. SQLite's transactional power isn't worth the overhead for a single-process desktop app with no concurrent writers.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/03-session-storage-schema.md)

## D5: How are projects and threads identified and persisted?
- **Decision**: A Project is identified by the canonical absolute root path; on-disk key is its SHA-256 hex digest. Global index at `~/.floo-network/projects.json` (hash → root/displayName/timestamps). Each project gets `~/.floo-network/projects/<hash>/project.json` + `threads/`. A Thread is a ULID, not locked to one mode (mode recorded per-message in the JSONL), with a `.meta.json` sidecar (`id, projectHash, title, createdAt, updatedAt, currentMode, openSpecChangeName`).
- **Why**: SHA-256 gives a stable, collision-irrelevant on-disk key from a path; ULID thread IDs make `ls` order threads by creation time with no file reads. `openSpecChangeName` on the sidecar gives `/go` a direct thread-to-change link (see D12) instead of re-deriving it.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/04-project-thread-data-model.md)

## D6: How is tool-use permission (read/write/edit/bash/web-search) enforced per mode?
- **Decision**: Enforcement is the executor's own built-in permission system — `--permission-mode` (Claude) / `--sandbox` (Codex) — not a harness-side tool dispatcher. Spec-mode launches the executor read-only/plan; go-mode launches it write-enabled. The harness cannot intercept individual tool calls inside the executor's own loop; its role is choosing the launch flag and scoping `cwd` to the project root, nothing finer-grained.
- **Why**: With a full executor CLI, the executor owns its internal tool loop end to end — this is a structural loss of the fine-grained custom control the earlier Gemma-based Ollama design had (that design intercepted every tool call itself), not a chosen tradeoff.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/05-tool-permission-architecture.md)
- **Open question carried to grill-apply**: whether executor-level hooks (Claude Code hooks, Codex plugins) can restore a fine-grained `create_note`-style gate or bash allowlist, or whether v1 accepts the executor's native permission system as sufficient.

## D7: What's the exact `/go` (spec-mode → go-mode) handoff mechanism?
- **Decision**: `/go` in chat or a UI button, both calling one handoff function. No spec-readiness precondition — only gate is idle state (no switch while a call is in flight). On `/go`: terminate the spec-mode executor process, spawn a fresh go-mode executor with conversation history carried forward (no summarization call). If the thread's `.meta.json` has a recorded OpenSpec change name (D12), the first go-mode message is `/grill-apply <name>` / `$grill-apply <name>`; otherwise the executor just continues the conversation. Once live, the harness UI becomes a thin pass-through wrapper to the executor process. Switching back to spec-mode terminates the live executor (no backgrounding); a later `/go` always starts fresh.
- **Why**: The executor already holds full thread context, so a fresh process with history carried forward is simpler and more faithful than the old task-brief-seeding approach designed around a model with no native session concept.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/06-spec-go-handoff-signal.md, amended by issues/14-openspec-change-detection.md)

## D8: What's the Graphify CLI integration shape?
- **Decision**: Shell out, don't embed. `graphify extract <project-dir> --out <out-dir> --no-viz --code-only` for a safe key-less JSON-only run (installed via `uv tool install graphifyy`). Code-only AST runs need no API key; semantic mode needs one of Anthropic/OpenAI/Gemini/Moonshot/Ollama backend keys, independent of the harness's own executor choice. Primary machine-readable artifact is `graph.json` (NetworkX node-link) on disk, not stdout. UI needs: target-scope picker, run/re-run + incremental/code-only/deep-mode toggles, results view rendering `GRAPH_REPORT.md` + explorable `graph.json`, and an optional query surface (`graphify query/path/explain`).
- **Why**: Matches the existing "Graphify runs in its own process" constraint (CLAUDE.md) — verified from public docs (README, `__main__.py`, graphify.net reference), not fabricated.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/07-graphify-integration-interface.md)
- **Note**: full `extract` flag list not exhaustively verified — confirm with `graphify extract --help` before implementing.

## D9: What's the Browserbase web-search integration shape?
- **Decision**: `POST https://api.browserbase.com/v1/search {query, numResults}` with `x-bb-api-key` header, key from `BROWSERBASE_API_KEY` in `.env`. Response is link+title+light-metadata only (no synthesized answer, no snippet text) — no official Rust SDK, so this is a raw REST call from the Tauri/Rust backend. Forward only structured metadata to the executor as a numbered `[n]` citation list; never raw HTML or a synthesized answer. If excerpted content is ever needed, that's a separate explicit Fetch-endpoint call, clearly labeled as unverified fetched content.
- **Why**: The API shape itself enforces "citations, not answers" — it has no answer-synthesis feature to accidentally leak past the boundary.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/08-browserbase-integration.md)

## D10: What's the note-creation UX end to end?
- **Decision**: `⌘N` or a sidebar "Create note" button opens a floating command bar; user types a filename; pressing Enter writes the file immediately (resolved under the project's notes location per D5) and opens it directly in the two-tab Edit/Preview markdown pane. No intermediate Create/Cancel approval card. Subsequent hand-edits to an already-created note auto-save without re-prompting.
- **Why**: Superseding an earlier amendment (ticket 10 originally inserted an approval card to satisfy what it read as ticket 05's synchronous-approval requirement for a `create_note` tool call). Ticket 05's final answer establishes note creation is a harness UI flow, not a model tool call — there is no `create_note` tool for an approval gate to guard, so the typed filename + Enter already is the user's own confirmation. Inserting a card would gate the user against their own keystroke.
- **Source**: recommended-accepted (this session, correcting issues/10-note-taking-ux.md's amendment against issues/05-tool-permission-architecture.md's final answer)
- **Follow-up**: `day-23-floo-network/CLAUDE.md:21` and `AGENTS.md:21` still say "the user confirms before any write" — stale phrasing to correct when those files are next touched, not part of this change's scope.

## D11: What's the exact executor-handoff CLI invocation?
- **Decision**: Claude: `claude --print --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>`, spawned with `cwd=<project-root>`, one persistent process fed ndjson over stdin (`--include-partial-messages` for token-level streaming). Codex: `codex exec "<prompt>" --json --sandbox <read-only|workspace-write> -C <project-root>` for the first turn; every subsequent turn is a **new process**, `codex exec resume --last "<message>" --json` (or `resume <SESSION_ID>`) — no persistent stdin pipe. This is a real architectural fork requiring two separate Rust adapters, not one shared code path. Handoff spec is passed as the first message content: `/grill-apply <name>` (Claude) / `$grill-apply <name>` (Codex) if a change exists (D12), else the carried-forward conversation directly.
- **Why**: Verified hands-on on this machine (`claude --help`, `codex exec --help`); Codex has no persistent-process equivalent to Claude's stdin-streaming mode, so the pass-through wrapper (D7) must be implemented differently per executor.
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/11-executor-handoff-invocation.md)
- **Per-machine preflight needed**: `grill-apply` skill installed (`~/.claude/skills/grill-apply` for Claude; **separately** `~/.agents/skills/grill-apply` for Codex — confirmed NOT yet present on this machine for Codex), `openspec` on PATH, Ponytail installed (D2) — one combined "is this machine handoff-ready" check.

## D12: How does the harness know whether a formal OpenSpec change exists for a thread at `/go` time?
- **Decision**: Spec-mode always works toward a formal OpenSpec change via the full grill methodology (explore → propose → apply → archive) — an OpenSpec change is the intended end-state of every spec-mode thread that reaches `/go`, not an optional artifact. Both `/grill-explore` and `/grill-propose` are skill invocations in the same spec-mode executor (no separate delegation — the executor is the only model in both modes). The user triggers `/propose` explicitly (separate from `/go`); the moment it succeeds, the harness records the change name in the thread's `.meta.json` (`openSpecChangeName`, D5). At `/go`, the harness checks that field directly — present → `/grill-apply <name>`; absent → plain carried-forward conversation. No `openspec list --json` searching, no naming convention, no staleness risk (the field is only ever set by this thread's own `/propose` call).
- **Why**: The harness already knows because it was the one running the executor when `/propose` succeeded — deriving it later by search would be strictly worse and riskier (could attach a stale/unrelated change).
- **Source**: grill-explore (.scratch/day-23-floo-network/issues/14-openspec-change-detection.md)

## D13: Does Claude Code support carrying conversation history across a `/go` permission-mode switch without a summarization call?
- **Decision**: Yes — `claude --resume <session-id> --permission-mode <new-mode>` both resumes full prior-turn context AND applies the new permission mode to the resumed process. Verified hands-on this session: spawned a session in `--permission-mode plan`, asked it to say a word; resumed the same session ID with `--permission-mode acceptEdits`, asked what word it said and to write it to a file — it recalled the word correctly and successfully wrote the file (proving both history carry-forward and the new permission mode taking effect). `/go` for Claude is therefore `claude --resume <session-id> --permission-mode <go-mode-value>`, not a raw respawn with manually replayed history.
- **Why**: Closes the one open question D11/ticket 11 flagged as unresolved. Also surfaces a correction to D11: `--permission-mode`'s valid values are `acceptEdits | auto | bypassPermissions | manual | dontAsk | plan` — **`default` is not a valid value**, contradicting ticket 11's `<plan|default>` notation. Spec-mode = `plan` stands; go-mode's exact value among the write-enabling options is not yet decided (see open items).
- **Source**: verified hands-on (this session, `claude --help` + live resume test)

## D14: Is this one OpenSpec change or split into sequential changes?
- **Decision**: Split into three sequential changes:
  1. **`day-23-floo-network-core`** — project/thread/session data model (D4, D5), Tauri+React shell (D3), mode selection UI. No executor spawning yet.
  2. **`day-23-floo-network-executor-handoff`** — the spec/go mode handoff and dual-executor process management (D6, D7, D11, D12, D13).
  3. **`day-23-floo-network-integrations`** — Graphify + Browserbase (D8, D9).
  This decision log stays the shared source for all three; each change gets its own `decisions.md` scoped to its slice once created, referencing D-numbers here rather than re-litigating them.
  **Amendment (post-hoc, after change 1's own grill-propose pass):** D10 (note-taking UX) ended up fully absorbed into change 1's own `note-taking` capability rather than deferred to change 3 — change 1's grilling reached far enough to spec and task it completely. Change 3's actual scope is Graphify + Browserbase only.
- **Why**: A single change spanning Rust process management, React UI, and two REST integrations would force grill-apply to sequence wildly different subsystems in one pass. Three independently buildable/testable slices let each land and verify before the next depends on it.
- **Source**: recommended-accepted

## D15: What's the testing boundary for the Rust/Tauri app across all three changes?
- **Decision**: Three tiers. (1) `cargo test` unit tests for pure logic — project hashing (D5), JSONL parsing/append (D4), path resolution. (2) Integration tests spawn a fake/stub executor binary (a tiny script echoing canned stream-json/JSONL) instead of a real `claude`/`codex` process, to deterministically test process lifecycle, mode switching (D7), and history carry-forward (D13) without hitting a real executor or API costs. (3) Playwright E2E against the Tauri webview for critical UI flows — mode switch, note creation (D10), chat send/receive.
- **Why**: Unit + fake-executor integration covers the Rust process/data logic deterministically and cheaply; Playwright adds real coverage for the flows that are actually risky to get wrong in a GUI (the user chose this over skipping E2E, accepting the extra setup/maintenance cost for a solo 1-2hr/day project).
- **Source**: user
- **Applies to**: all three changes (D14) — each change's tasks.md should specify which tier(s) its tasks are verified at, per `/tdd`.

## D16: What exact `--permission-mode` value does go-mode launch Claude with?
- **Decision**: `acceptEdits`. Auto-accepts file edits/writes but still prompts for genuinely risky operations (e.g. bash commands outside a safe set) — not a full bypass.
- **Why**: Matches ticket 05's original framing of go-mode as "write-enabled, governed by Claude Code's own edit/write approvals," not an unrestricted mode. Given D6 already establishes the harness has no tool-call-level backstop of its own, `bypassPermissions` would remove Claude Code's own safety net entirely with nothing behind it.
- **Source**: recommended-accepted
- **Codex equivalent**: `--sandbox workspace-write` (already settled in D11/ticket 11 — no change needed there).

## D17: How is distribution/packaging (code signing, auto-update, cross-laptop sync) handled?
- **Decision**: Treated as its own fourth OpenSpec change (`day-23-floo-network-distribution`), sequenced after the other three land and the harness works end to end — not folded into changes 1–3, and not silently left unspecified. Grilling for that change's actual content (signing approach, update mechanism, cross-laptop binary/config movement) happens when that change is proposed, not here — changes 1–3 should state it as an explicit non-goal in their own proposal.md so scope doesn't creep.
- **Why**: The user chose to treat this as real, sequenced scope rather than silent deferral, but grilling its specifics now would front-load decisions (e.g. code signing approach) that depend on how changes 1–3 actually turn out — same reasoning as D14's phase split.
- **Source**: user

## Open items (not yet resolved)

(none — all cross-cutting decisions are resolved; each of the four changes gets its own proposal/design/task-level grilling in its own `grill-propose` pass once its `openspec new change` directory exists)
