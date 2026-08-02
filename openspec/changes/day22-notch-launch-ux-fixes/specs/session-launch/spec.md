## ADDED Requirements

### Requirement: Unified launch behavior
The system SHALL apply identical session-registration and process-spawn behavior regardless of whether a launch was requested via the `POST /session/launch` HTTP endpoint or the notch UI's "Spawn" button.

#### Scenario: HTTP-initiated and UI-initiated launches behave identically
- **WHEN** a session is launched via `POST /session/launch` with a given agent command and working directory
- **AND** a session is launched via the notch UI's Spawn button with the same agent command and working directory
- **THEN** both launches register a session and attempt to spawn the process using the same behavior, including identical failure handling

### Requirement: Visible launch failure
The system SHALL mark a session's status as failed, distinct from other statuses, when its process fails to spawn — never silently discard the error.

#### Scenario: Spawn failure sets an Error status
- **WHEN** the command for a launched session fails to spawn (e.g. the binary does not exist)
- **THEN** the session's status becomes an Error state carrying the failure reason
- **AND** the Error state is rendered in a color distinct from the QuotaWarning state

### Requirement: Failed sessions remain visible
The system SHALL keep a failed session's tab visible in the session tab strip until the user explicitly dismisses it — never remove it automatically.

#### Scenario: A failed launch's tab persists
- **WHEN** a session fails to launch
- **THEN** its tab remains present in the session tab strip
- **AND** the tab remains present after subsequent app renders until the user dismisses it

### Requirement: Launch-failure prompt with explicit resolution
The system SHALL present an actionable prompt when a launch fails, offering the user a choice to remove the session immediately or defer the decision.

#### Scenario: Failure prompt appears with two actions
- **WHEN** a session fails to launch
- **THEN** a prompt card appears offering a "Kill it" action and a "Later" action

#### Scenario: "Kill it" removes the session
- **WHEN** the user selects "Kill it" on a launch-failure prompt
- **THEN** the corresponding session is removed from the session list
- **AND** the prompt is removed from the failure queue

#### Scenario: "Later" defers without losing the failed state
- **WHEN** the user selects "Later" on a launch-failure prompt
- **THEN** the prompt is removed from the failure queue
- **AND** the session's tab remains visible, still marked as failed

### Requirement: Consistent HTTP response shape on launch outcome
The `POST /session/launch` endpoint SHALL respond `200 OK` for both successful and failed launches, encoding the outcome in the response body rather than the HTTP status code.

#### Scenario: Successful launch response
- **WHEN** a launch succeeds
- **THEN** the response is `200 OK` with a body indicating `"status": "launched"` and the session id

#### Scenario: Failed launch response
- **WHEN** a launch fails to spawn
- **THEN** the response is `200 OK` with a body indicating `"status": "failed"`, the session id, and a failure reason

### Requirement: Active-session fallback on removal
The system SHALL select a remaining session as active when the currently active session is removed, or clear to no active session when none remain.

#### Scenario: Fallback to a remaining session
- **WHEN** the active session is removed
- **AND** at least one other session still exists
- **THEN** one of the remaining sessions becomes the active session

#### Scenario: Fallback to no active session
- **WHEN** the active session is removed
- **AND** no other sessions exist
- **THEN** there is no active session

### Requirement: No fake session on cold start
The system SHALL start with an empty session list — it SHALL NOT seed a placeholder or demo session.

#### Scenario: Fresh start has zero sessions
- **WHEN** the application starts with no sessions previously launched and none yet detected
- **THEN** the session list is empty
- **AND** there is no active session

### Requirement: Structured launch form input
The notch UI's launch form SHALL let the user select from the agent CLIs actually installed on the machine, and select a working directory via a native folder picker, rather than requiring free-text recall of an exact binary name or path.

#### Scenario: Agent selection lists only installed CLIs
- **WHEN** the user opens the launch form
- **THEN** they can choose from the known agent CLIs detected on this machine at startup
- **AND** a known agent CLI that is not installed is not offered
- **AND** selecting a "Custom" option reveals a free-text command field as a fallback

#### Scenario: Launching works regardless of how the app was started
- **WHEN** a session is launched for a detected agent CLI
- **THEN** the process is spawned by its resolved absolute path
- **AND** the launch succeeds even when the application was started without the user's shell environment

#### Scenario: Directory selection via native picker
- **WHEN** the user activates the folder-browse control in the launch form
- **THEN** a native folder picker opens
- **AND** the folder the user selects populates the working-directory field
- **AND** the working-directory field remains directly editable as an alternative to browsing
