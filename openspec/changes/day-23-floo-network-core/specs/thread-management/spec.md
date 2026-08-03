## ADDED Requirements

### Requirement: Create a thread within a project
The system SHALL create a new thread identified by a ULID, scoped to exactly one project, with a `.meta.json` sidecar containing `id`, `projectHash`, `title`, `createdAt`, `updatedAt`, `currentMode`, and `openSpecChangeName` (initialized to `null`).

#### Scenario: Creating a new thread
- **WHEN** the user creates a new thread inside the active project
- **THEN** the system generates a ULID, creates `~/.floo-network/projects/<project-hash>/threads/<ulid>.meta.json` with `currentMode` defaulted to `spec` and `openSpecChangeName` set to `null`, and creates the empty `<ulid>.jsonl` session log

### Requirement: List threads for a project
The system SHALL list all threads belonging to the active project by reading their `.meta.json` sidecars.

#### Scenario: Viewing the thread list
- **WHEN** the user views the active project's thread list
- **THEN** the system reads every `threads/*.meta.json` sidecar for that project and displays each thread's title, current mode, and last-updated time

### Requirement: Switch the active thread
The system SHALL allow the user to select which thread within the active project is currently displayed.

#### Scenario: Switching threads
- **WHEN** the user selects a different thread from the thread list
- **THEN** the system loads that thread's session history (per the session-storage capability) and displays it

### Requirement: Rename a thread
The system SHALL allow the user to edit a thread's title without changing its identity (ULID).

#### Scenario: Renaming a thread
- **WHEN** the user edits a thread's title
- **THEN** the system updates `title` and `updatedAt` in that thread's `.meta.json` sidecar
