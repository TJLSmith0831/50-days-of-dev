## ADDED Requirements

### Requirement: Register a project by root path
The system SHALL identify a project by the canonical absolute path of its root directory and derive its on-disk key as the lowercase SHA-256 hex digest of that path.

#### Scenario: Adding a new project
- **WHEN** the user picks a directory that has not been registered before
- **THEN** the system creates `~/.floo-network/projects/<sha256-hex>/project.json` with `root`, `displayName` (defaulting to the directory basename), `createdAt`, and `lastAccessedAt`, and adds an entry to the global index

#### Scenario: Adding an already-registered project
- **WHEN** the user picks a directory whose canonical path already has an entry in the global index
- **THEN** the system reuses the existing project directory and updates `lastAccessedAt`, without creating a duplicate entry

### Requirement: Maintain a global project index
The system SHALL maintain a single global index file at `~/.floo-network/projects.json` mapping each project's hash to its root path, display name, and timestamps.

#### Scenario: Listing known projects
- **WHEN** the user opens the project picker
- **THEN** the system reads `projects.json` and lists every registered project by display name

### Requirement: Switch the active project
The system SHALL allow the user to change which registered project is active in the current harness window.

#### Scenario: Switching projects
- **WHEN** the user selects a different project from the project list
- **THEN** the system makes that project's threads visible and updates `lastAccessedAt` for the newly active project

### Requirement: Edit a project's display name
The system SHALL allow the user to rename a project's display name without changing its identity (root path / hash).

#### Scenario: Renaming a project
- **WHEN** the user edits the display name for a registered project
- **THEN** the system updates `displayName` in that project's `project.json` and the global index, leaving `root` and the project hash unchanged
