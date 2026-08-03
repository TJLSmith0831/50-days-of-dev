## ADDED Requirements

### Requirement: Detect installed executors on PATH
The system SHALL check for `claude` and `codex` binaries on PATH using a library-based lookup, tolerant of aliases and PATH variations, without spawning a shell.

#### Scenario: Both executors present
- **WHEN** both `claude` and `codex` are found on PATH
- **THEN** the system selects `claude` as the active executor

#### Scenario: Only one executor present
- **WHEN** exactly one of `claude` or `codex` is found on PATH
- **THEN** the system selects that executor as the active one

#### Scenario: Neither executor present
- **WHEN** neither `claude` nor `codex` is found on PATH
- **THEN** the system warns the user and operates in chat-only mode, with `/go` unavailable

### Requirement: Cache detection result with staleness re-check
The system SHALL run executor detection once at app startup, cache the result, and re-run it if the cached result is older than the current app session at the moment `/go` is invoked.

#### Scenario: Startup detection
- **WHEN** the harness launches
- **THEN** the system performs detection once and caches the result for the session

#### Scenario: Re-check on stale cache at handoff time
- **WHEN** the user invokes `/go` and the cached detection result predates the current app session
- **THEN** the system re-runs detection before proceeding with the handoff
