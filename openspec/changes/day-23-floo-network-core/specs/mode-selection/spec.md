## ADDED Requirements

### Requirement: Toggle a thread's mode between spec and go
The system SHALL provide a per-thread toggle between `spec` mode and `go` mode.

#### Scenario: Switching a thread to go mode
- **WHEN** the user flips the mode toggle for a thread currently in `spec` mode
- **THEN** the system updates `currentMode` to `go` in that thread's `.meta.json` sidecar and appends a `role: "tool"` marker message with `mode: "go"` to the thread's session log

#### Scenario: Switching a thread back to spec mode
- **WHEN** the user flips the mode toggle for a thread currently in `go` mode
- **THEN** the system updates `currentMode` to `spec` in that thread's `.meta.json` sidecar and appends a `role: "tool"` marker message with `mode: "spec"` to the thread's session log

### Requirement: No process behavior on mode switch
The system SHALL NOT spawn, terminate, or otherwise manage any executor process as a result of a mode toggle in this change.

#### Scenario: Flipping the toggle with no executor present
- **WHEN** the user flips the mode toggle
- **THEN** the system persists the mode change per the requirement above and performs no process spawn, terminate, or IPC beyond that persistence
