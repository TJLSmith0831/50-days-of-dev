## ADDED Requirements

### Requirement: Persist sessions to SQLite database
The system SHALL persist session data to a SQLite database located at ~/.coding-agent-harness/sessions.db.

#### Scenario: Session creation
- **WHEN** a new session is started
- **THEN** the session metadata is stored in the SQLite database

#### Scenario: Session update
- **WHEN** a session is updated (new messages, state change)
- **THEN** the session is updated in the SQLite database

### Requirement: Use LangGraph SqliteSaver for checkpointing
The system SHALL use LangGraph's SqliteSaver for automatic checkpointing of agent state.

#### Scenario: Checkpoint creation
- **WHEN** the agent completes a turn
- **THEN** the state is checkpointed via SqliteSaver

#### Scenario: Checkpoint restore
- **WHEN** a session is resumed
- **THEN** the state is restored from the last checkpoint

### Requirement: Support mid-turn checkpointing
The system SHALL support checkpointing in the middle of a turn (before tool execution completes) for resilience.

#### Scenario: Mid-turn checkpoint
- **WHEN** the agent is executing tools
- **THEN** the state is checkpointed before tool execution

#### Scenario: Resume from mid-turn
- **WHEN** the session is resumed from a mid-turn checkpoint
- **THEN** the agent continues from the interrupted state

### Requirement: List available sessions
The system SHALL list all available sessions with metadata (session_id, created_at, updated_at, thread_id).

#### Scenario: Session list
- **WHEN** the user runs /sessions
- **THEN** the system displays a list of sessions with metadata

#### Scenario: Empty session list
- **WHEN** no sessions exist
- **THEN** the system displays a message indicating no sessions

### Requirement: Resume session by ID
The system SHALL allow resuming a session by session ID or thread ID.

#### Scenario: Resume by session ID
- **WHEN** the user specifies a session ID on startup
- **THEN** the system loads the session state from the database

#### Scenario: Resume by thread ID
- **WHEN** the user specifies a thread ID on startup
- **THEN** the system loads the session state from the database

### Requirement: Delete sessions
The system SHALL allow deleting sessions to clean up the database.

#### Scenario: Delete session
- **WHEN** the user deletes a session
- **THEN** the session and associated data are removed from the database

### Requirement: Backup and restore database
The system SHALL support database backup and restore operations.

#### Scenario: Database backup
- **WHEN** the user runs a backup command
- **THEN** the database is copied to a backup file

#### Scenario: Database restore
- **WHEN** the user runs a restore command with a backup file
- **THEN** the database is restored from the backup
