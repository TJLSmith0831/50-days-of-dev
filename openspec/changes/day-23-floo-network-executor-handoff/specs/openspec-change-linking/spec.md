## ADDED Requirements

### Requirement: Invoke grill-propose via /propose
The system SHALL, on the user typing `/propose` in a spec-mode thread, send `/grill-propose` (Claude) or `$grill-propose` (Codex) as a skill invocation to the running spec-mode executor.

#### Scenario: User runs /propose
- **WHEN** the user types `/propose` in an active spec-mode thread
- **THEN** the system sends the corresponding skill-invocation string to the running executor

### Requirement: Record the resulting OpenSpec change name
The system SHALL, when `grill-propose` succeeds in creating an OpenSpec change, record that change's name in the thread's `.meta.json` under `openSpecChangeName`.

#### Scenario: Successful proposal
- **WHEN** `grill-propose` completes and an OpenSpec change now exists for the thread's work
- **THEN** the system writes that change's name into the thread's `.meta.json` `openSpecChangeName` field

### Requirement: Preflight readiness check before handoff
The system SHALL verify, before offering `/grill-apply`-based handoff, that the detected executor's environment has `grill-apply` installed (`~/.claude/skills/grill-apply` for Claude, `~/.agents/skills/grill-apply` for Codex) and `openspec` on PATH, and warn (not silently fail) if either is missing.

#### Scenario: Environment ready
- **WHEN** both `grill-apply` and `openspec` are present for the detected executor
- **THEN** the system's persistent status indicator shows the handoff as ready

#### Scenario: Environment not ready
- **WHEN** either `grill-apply` or `openspec` is missing for the detected executor
- **THEN** the system's status indicator warns the user before they attempt a change-linked `/go`
