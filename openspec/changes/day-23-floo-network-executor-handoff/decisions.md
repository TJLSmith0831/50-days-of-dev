# day-23-floo-network-executor-handoff — Decision Log

Change 2 of 4 (per D14): the spec/go mode handoff and dual-executor process
management. Depends on change 1 (`day-23-floo-network-core`)'s data model
(project/thread/session storage, mode-selection persistence) already
existing and working.

Full cross-cutting decision history: `openspec/explore/day-23-floo-network.md` (D1–D17).

## Carried forward from the shared log

- **D1** — unrelated to the 7 stale specs; no reference to them.
- **D2** — Ponytail is a per-machine plugin install, checked (not installed) by the harness before handoff.
- **D6** — enforcement is the executor's own `--permission-mode`/`--sandbox`, not a harness-side tool dispatcher; harness only picks the launch flag and scopes `cwd`.
- **D7** — `/go` mechanics: idle-only gate, terminate+respawn with history carried forward, thin pass-through UI once live, terminate (not background) on switch back to spec-mode.
- **D11** — exact CLI invocations: Claude persistent stdin-stream process (`--print --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>`); Codex per-turn `codex exec ... --json --sandbox <mode> -C <root>` then `codex exec resume --last "<msg>" --json` per turn — two separate Rust adapters, not one shared code path. Codex skill path is `~/.agents/skills/grill-apply` (separate from Claude's `~/.claude/skills/grill-apply`, confirmed NOT yet present on this machine).
- **D12** — `/propose` triggers `grill-propose` as a skill invocation in the running spec-mode executor; harness records the resulting change name in the thread's `.meta.json` (`openSpecChangeName`) the moment it succeeds; `/go` checks that field directly.
- **D13** — Claude history carry-forward via `claude --resume <session-id> --permission-mode <new-mode>`, verified hands-on to carry full prior context and apply the new permission mode.
- **D15** — testing tiers: `cargo test` unit tests for pure logic; fake-executor integration tests (a stub binary echoing canned stream-json/JSONL) exercise process lifecycle, mode switching, and history carry-forward without a real executor — this is the change where that tier is actually built and used. Playwright E2E for critical UI flows relevant to this change (mode switch with a live pass-through, executor crash banner).
- **D16** — go-mode Claude launch value is `acceptEdits`; Codex equivalent is `--sandbox workspace-write`.
- **D17** — distribution/packaging is a non-goal.

## E1: What new capabilities does this change introduce?
- **Decision**: Four — `executor-detection` (find `claude`/`codex` on PATH, prefer claude if both present, warn and stay chat-only if neither), `executor-process-management` (spawn/terminate per-executor: Claude's persistent stdin-stream process, Codex's per-turn `resume --last` invocations), `mode-handoff` (`/go` command + button, idle-only gating, terminate+respawn with carried-forward history), `openspec-change-linking` (`/propose` triggers `grill-propose` in-executor, records `openSpecChangeName`).
- **Why**: Each maps to a distinct, independently testable concern per D15's tiers — detection is a pure filesystem/PATH check, process-management is the Rust process layer, mode-handoff is the user-facing trigger/gating logic, change-linking is the thread-metadata bookkeeping around `/propose`.
- **Source**: recommended-accepted

## E2: What happens when the executor process crashes or exits unexpectedly mid-session in go-mode?
- **Decision**: The harness detects the dead process (non-zero exit or stdout close), shows an inline banner in the chat pane ("executor process ended unexpectedly"), switches the thread's `currentMode` back to `spec`, and leaves the JSONL history intact. The user can inspect what happened and manually `/go` again.
- **Why**: Silent auto-restart risks a crash loop if the conversation content itself triggered the crash; surfacing and falling back to spec-mode keeps the user in control without losing any history (append-only JSONL means nothing is lost either way).
- **Source**: recommended-accepted

## E3: When does the handoff-readiness preflight check (grill-apply installed, openspec on PATH, Ponytail installed) run?
- **Decision**: Once at app startup (fast filesystem/PATH checks, no subprocess needed per D11), cached, shown as a persistent status indicator in the UI. Re-checked right before an actual `/go` if the cached result is stale (older than the current app session), so a mid-session environment change isn't silently missed.
- **Why**: Avoids adding a synchronous delay to every `/go` while still catching the realistic failure mode (something got uninstalled since the app launched).
- **Source**: recommended-accepted

## E4: How does the chat pane render executor-emitted structured events once in go-mode pass-through?
- **Decision**: Parsed into distinct UI elements per event type via the per-executor event parser already required by D11: text/reasoning as chat bubbles, file-edit events as diffs via `react-diff-viewer-continued`, bash/tool-call events as collapsible command+output blocks. Requires mapping each executor's own event schema (Claude's `stream-json`, Codex's `item.started`/`item.completed`) into one common internal event type the UI consumes.
- **Why**: Matches why D3 chose `react-diff-viewer-continued` specifically — a raw text stream would leave that dependency unused and lose the readability a structured diff view gives for reviewing go-mode edits.
- **Source**: recommended-accepted

## E5: What's the common internal event type both executor parsers map into?
- **Decision**: A shared Rust enum, e.g. `ExecutorEvent::{Text(String), Reasoning(String), FileEdit { path, diff }, ToolCall { command, output, exit_code }, Done, Crashed { exit_code } }`. Each executor's own parser (Claude's `stream-json`, Codex's `item.started`/`item.completed`) maps its schema into this enum; the frontend only ever consumes this one type via the Tauri event channel.
- **Why**: Keeps the two-executor architectural fork (D11) contained to the parsing layer — everything downstream (UI rendering per E4, crash handling per E2) works against one shape regardless of which executor is live.
- **Source**: recommended-accepted

## E6: How does executor detection work mechanically?
- **Decision**: A Rust `which`-crate-style cross-platform PATH lookup for `claude` and `codex` binaries at app startup (part of the E3 preflight check), tolerant of aliases/PATH variations per AGENTS.md's existing gotcha. No shell invocation, no version parsing required for detection itself (version comes into play only in D11's per-machine capability checks).
- **Why**: A library-based PATH lookup avoids spawning a shell just to check binary presence, and matches the "fast filesystem/PATH check, no subprocess needed" framing already used for the Ponytail/openspec checks in D11/E3.
- **Source**: recommended-accepted

## E7: What does the fake-executor test stub need to simulate?
- **Decision**: A small script checked into test fixtures that reads stdin (mimicking Claude's stdin-stream protocol) or accepts CLI args (mimicking Codex's `exec`/`resume` invocation), and can be configured via env var or arg to: (a) echo back a canned `stream-json`/JSONL response sequence for a normal turn, or (b) exit non-zero immediately to simulate a crash (exercising E2's crash-handling path). Used by D15 tier 2 integration tests for process lifecycle, mode switching, and history carry-forward.
- **Why**: One configurable stub covers both the happy-path and crash-path integration tests without needing two separate fixtures, and exercises the real process-spawn/pipe code paths without any real API cost or executor dependency in CI.
- **Source**: recommended-accepted

## E8: What order do the task groups build in, and what's riskiest to front-load?
- **Decision**: 1) `executor-detection` (independent, no dependencies, needed by everything else to know which adapter to use). 2) Fake-executor test stub (E7) — built early so process-management work below can be tested against it immediately rather than only against real, costly executor calls. 3) `executor-process-management` for Claude (persistent stdin-stream — riskiest: novel long-lived-process-plus-ndjson-parsing architecture for this codebase) before Codex (per-turn `resume` — simpler request/response shape once Claude's harder case is proven out). 4) `mode-handoff` (`/go` trigger, idle gating, terminate+respawn), depends on process-management existing for both executors. 5) `openspec-change-linking` (`/propose` handling), independent of process-management, can build in parallel with §4. 6) Crash handling (E2) and event rendering (E4/E5) wired into the chat pane once process-management emits real events. 7) Playwright E2E once the full pass-through loop works end to end.
- **Why**: Claude's persistent-process architecture is the harder, riskier half of D11's "real architectural fork" — proving it out first (against the fake-executor stub, not a costly real process) de-risks Codex's comparatively simpler per-turn model built afterward.
- **Source**: recommended-accepted

## E9: `--verbose` is mandatory alongside `--output-format stream-json` — D11's flag list was incomplete
- **Decision**: The Claude spawn command is `claude --print --verbose --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>`. `--verbose` is added to D11's list.
- **Why**: Verified hands-on against Claude Code 2.1.220 while implementing §3: without it the CLI refuses to start, printing `Error: When using --print, --output-format=stream-json requires --verbose`. D11 recorded the flags from documentation and missed this constraint; every spawn would have failed immediately.
- **Source**: recommended-accepted

## E10: Claude's session id is chosen by the harness, not parsed out of the stream
- **Decision**: Generate a v4 UUID up front and pass `--session-id <uuid>` on first spawn; the handoff then uses `--resume <same-uuid> --permission-mode acceptEdits`. Verified hands-on: the resumed process reports the same `session_id`, carries the full prior conversation, and applies the new permission mode.
- **Why**: D13 assumed the id had to be read back out of `system/init` before a resume was possible, which would have made the handoff depend on parsing at least one event correctly. Setting the id makes the handle known before the process even starts, so the handoff has nothing to parse and nothing to race.
- **Source**: recommended-accepted

## E11: The executor session id is persisted on the thread sidecar
- **Decision**: `ThreadMeta` gains `executorSessionId: string | null` (serde `default`, so change 1's existing sidecars still parse). It is written whenever a session starts, read back when `/go` needs to resume, and cleared on `Crashed`.
- **Why**: Found by testing the real handoff: with the id held only in memory, restarting the app silently broke `/go`'s carry-forward — the go-mode executor answered "this is the first message in our conversation" while the full history sat in the JSONL right next to it. Since the whole point of `/go` is continuing a conversation, an id that dies with the process makes the feature quietly wrong rather than obviously broken. Clearing it on crash is the self-heal: resuming a session the executor no longer has fails exactly the same way every time otherwise. This is the schema extension change 1's design.md warned to re-verify before making — additive only, so no change-1 requirement is affected.
- **Source**: recommended-accepted

## E12: A tool call and its result are two events, not one
- **Decision**: `ExecutorEvent` carries `ToolCall { id, name, command }` and `ToolResult { id, output, is_error }` separately, instead of E5's single `ToolCall { command, output, exit_code }`. The frontend pairs them by `id`.
- **Why**: Both executors emit the invocation and its output as separate events, necessarily — the output does not exist yet when the call starts. Merging them in the adapter would mean withholding the command from the UI until the tool finished, so a long-running build would show nothing at all while it ran. Two events let the command render immediately with a "running…" state.
- **Source**: recommended-accepted

## E13: `FileEdit` carries before/after text, not a precomputed diff
- **Decision**: `FileEdit { id, path, before, after }` rather than E5's `FileEdit { path, diff }`. For `Write`, `before` is read off disk at parse time (the event arrives before the write lands, so the file still holds its prior content); for `Edit` it is the tool's own `old_string`/`new_string`.
- **Why**: `react-diff-viewer-continued` (D3) computes and renders the diff itself from two strings. Producing unified-diff text in Rust only to have the viewer parse it back would be strictly more code and lossier.
- **Source**: recommended-accepted

## E14: Reasoning events are not persisted
- **Decision**: `Text`, `ToolCall`, `ToolResult`, `FileEdit` and crashes are appended to the thread's JSONL; `Reasoning` is streamed to the UI and then dropped. Structured events are stored as their own JSON under `role: "tool"`, so a reloaded thread re-renders the same diffs and tool blocks a live one shows.
- **Why**: Reasoning is both the largest and the least re-readable part of a transcript; persisting it would dominate the log while adding little to what a user revisits. Storing the other events as JSON (rather than flattened text) is what keeps reload fidelity — anything that fails to parse, like change 1's mode-switch markers, still renders as plain text.
- **Source**: recommended-accepted

## E15: A persistent executor ending is always a crash, whatever the last turn did
- **Decision**: For Claude, stdout closing while the harness is not deliberately stopping is a `Crashed`, full stop. Only Codex — where a per-turn process ending is normal — uses the "bad exit code or no `Done`" test.
- **Why**: Found while testing the crash path. The original shared condition asked whether the *last turn* had reached `Done`, which is true for an idle session — so a Claude process killed while idle (OOM, a stray `pkill`) reported nothing at all, and the failure would only have surfaced as the user's next message vanishing into a dead pipe.
- **Source**: recommended-accepted

## E16: Codex's adapter is written but unverified
- **Decision**: The Codex adapter and its event parser ship implemented and covered by the fake-executor stub, but have never been run against a real `codex`. A `ponytail:` comment on `parse_codex_line` records this.
- **Why**: Claiming it works would be a claim not run — the event schema is written from Codex's documented `item.started`/`item.completed` shape, not from observed output, which is exactly how D11's Claude flag list ended up missing `--verbose`.
- **AMENDED**: this entry originally said "`codex` is not installed on this machine", which was **false**. Codex CLI 0.146.0 is installed at `~/.nvm/versions/node/v24.16.0/bin/codex`; I asserted its absence without ever running `command -v codex`. The conclusion (adapter unverified) stands, but the reason does not: verifying it is now a cheap thing to do, not a blocked one. Found when the Codex integration test started spending 20s and intermittently failing — it guarded on `find_on_path("codex").is_none()` and, codex being present all along, was spawning the *real* binary.
- **Source**: recommended-accepted

## E18: The Codex adapter must use the detected binary path, not the name `codex`
- **Decision**: `Session` carries the `bin` path detection resolved, and the per-turn Codex spawn uses it instead of `Command::new("codex")`.
- **Why**: A real bug, surfaced by the flaky test above. Detection resolves a full path and the adapter threw it away, looking the name up again through whatever `PATH` the process happened to have — the same class of failure as E17, and it also made the adapter impossible to point at the fake-executor stub, so the test was spending real Codex invocations. The integration test now runs against the stub and asserts the actual event sequence (ToolCall → Text → Done, then idle) rather than merely that some event arrived.
- **Source**: recommended-accepted

## E17: Detection falls back to the login shell's PATH
- **Decision**: `find_on_path` first searches the inherited `PATH`; if that misses, it resolves the login shell's PATH once (`$SHELL -lic 'printf %s "$PATH"'`, cached in a `OnceLock`) and searches that. E6's "no shell invocation" still holds for the common case — the shell only runs after a direct lookup has already failed.
- **Why**: Found while verifying the packaged app. A GUI app launched from Finder, the Dock or Spotlight inherits launchd's minimal `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`), not the shell's — so `claude`, which lives under `~/.nvm/versions/node/<v>/bin` here, is invisible. Confirmed by running the detection test under that PATH: `claude on the inherited PATH: false`, and with the fallback it resolves to the real nvm binary. Without this, the installed app would silently sit in chat-only mode and report "no executor found on PATH" while the user's terminal finds `claude` fine — the single worst failure mode for this project, since the whole harness is an executor front-end. It only bit the installed build; launching from a terminal (as every earlier verification did) inherits the full PATH and hides the bug entirely.
- **Source**: recommended-accepted

## E19: The crash reaction lives in `executor::on_crash`, not in the Tauri sink
- **Decision**: `on_crash(home, hash, thread_id)` owns reverting the thread to spec mode and clearing `executorSessionId`; `AppSink::emit` calls it. Covered by `a_crash_reverts_the_thread_and_clears_its_session`, written red-first.
- **Why**: Task 5.7 asked for exactly this test and I had marked the task complete without one — the logic sat inside `AppSink::emit`, which needs a Tauri `AppHandle` and so could not be exercised from `cargo test` at all. Extracting it is the smaller shape anyway: the sink becomes a two-line wrapper, and the test guards the path production actually runs instead of a re-implementation of it. The test also pins the part that is easy to regress silently — that history survives, since append-only storage is the only reason a crash is safe to recover from at all.
- **Source**: recommended-accepted

## E20: Codex's spawn and failure path, verified against the real CLI
- **Decision**: `codex exec` is invoked with `--skip-git-repo-check` and `stdin` set to null, and `parse_codex_line` now handles `turn.failed`, top-level `error` events, and `item.completed` items of type `error`.
- **Why**: E16 said the adapter was unverified; running the real Codex CLI 0.146.0 found three defects it was hiding, none of which the fake-executor stub could have caught because the stub only ever emitted the happy path I imagined.
  - **`codex exec` refuses to run outside a git repository** ("Not inside a trusted directory and --skip-git-repo-check was not specified"). The harness registers projects by path and has never required them to be git repos, so on a non-git project *every* Codex turn failed at spawn.
  - **`codex exec` reads stdin**, and the adapter left stdin inherited — a turn could block on a terminal that will never send anything.
  - **A failing turn emits `turn.failed`, never `turn.completed`.** The parser recognised only the latter, so a failed turn produced no terminal event at all: `busy` stayed true forever, the composer stayed disabled, and the user was given no reason why. Errors also arrive as their own top-level `error` events and as `item.completed` items with `type: "error"` carrying `message` (not `text`), all of which were silently dropped.
  The regression test is built from output captured from the real CLI rather than a fixture I wrote, since a fixture I invented could only ever prove the parser matches my guess — which is exactly how these three got in.
- **Status**: the event *envelope*, the failure path, and the exact flag set are now verified against the real binary. The success-path item schemas (`agent_message`, `command_execution`, `file_change` field names) remain unverified, because this machine's Codex is not authenticated — the probe reached `thread.started`/`turn.started` and then failed on a 401.
- **Source**: recommended-accepted

## Open items for this change (to grill)

- Verify `parse_codex_line` against a real `codex` on the work laptop (per E16).
