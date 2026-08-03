## ADDED Requirements

### Requirement: Spawn a Claude executor as a persistent process
The system SHALL spawn Claude as one persistent child process using `claude --print --input-format stream-json --output-format stream-json --include-partial-messages --permission-mode <mode>` with `cwd` set to the project root, communicating over stdin/stdout as newline-delimited JSON.

#### Scenario: Starting a Claude session
- **WHEN** the harness spawns a Claude executor for a project
- **THEN** the process is launched with `cwd` set to that project's root and remains alive across multiple user turns until explicitly terminated

### Requirement: Spawn a Codex executor per turn
The system SHALL invoke Codex fresh for each turn: the first turn as `codex exec "<prompt>" --json --sandbox <mode> -C <project-root>`, and every subsequent turn as `codex exec resume --last "<message>" --json --sandbox <mode>`.

#### Scenario: First Codex turn
- **WHEN** the harness starts a new Codex session
- **THEN** it invokes `codex exec` with the initial prompt and `-C <project-root>`

#### Scenario: Subsequent Codex turns
- **WHEN** the user sends a message in an existing Codex session
- **THEN** the harness spawns a new `codex exec resume --last` process for that single turn, not a persistent process

### Requirement: Map executor output into a shared event type
The system SHALL parse each executor's own event schema (Claude's `stream-json`, Codex's `item.started`/`item.completed`) into one shared `ExecutorEvent` type (`Text`, `Reasoning`, `FileEdit`, `ToolCall`, `Done`, `Crashed`) before forwarding to the frontend.

#### Scenario: Claude event mapping
- **WHEN** the Claude process emits a `stream-json` event
- **THEN** the system maps it into the corresponding `ExecutorEvent` variant

#### Scenario: Codex event mapping
- **WHEN** a `codex exec` invocation emits an `item.started`/`item.completed` event
- **THEN** the system maps it into the corresponding `ExecutorEvent` variant

### Requirement: Detect and surface unexpected executor exit
The system SHALL detect unexpected termination of either executor (non-zero exit code, or stdout closing without a `Done` event) and emit an `ExecutorEvent::Crashed`.

#### Scenario: Claude process dies mid-session
- **WHEN** the persistent Claude process exits unexpectedly
- **THEN** the system emits `Crashed` with the process's exit code

#### Scenario: Codex turn fails
- **WHEN** a `codex exec resume --last` invocation exits non-zero
- **THEN** the system emits `Crashed` with that invocation's exit code

### Requirement: Terminate the live executor on mode switch back to spec-mode
The system SHALL terminate the live executor process (not background or detach it) when the user switches a thread back to spec-mode.

#### Scenario: Switching back to spec-mode
- **WHEN** the user switches an active go-mode thread back to spec-mode
- **THEN** the system terminates the live executor process entirely; a later `/go` starts a completely fresh executor session
