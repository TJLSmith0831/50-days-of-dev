## ADDED Requirements

### Requirement: Per-source session registration
The system SHALL register a distinct session for each actively-updating detected agent log source, rather than overwriting a single shared status with events from multiple sources.

#### Scenario: Two simultaneously active agents each get their own session
- **WHEN** a Claude Code log and a separate Antigravity log both receive new activity
- **THEN** two distinct sessions exist, one corresponding to each source
- **AND** each session's status reflects only its own source's activity

### Requirement: Source-derived session identity
A passively-detected session's identity SHALL be derived from its source location, not from parsing its log content — since real agent transcripts do not reliably self-report an agent type.

#### Scenario: Agent type follows source directory
- **WHEN** a session is registered from a detected log file
- **THEN** its agent type is determined by which known source directory the file belongs to
- **AND** its display name is the fixed label associated with that source

### Requirement: No auto-expiry of passively-detected sessions
A passively-detected session SHALL remain visible with its last-known status after its source stops receiving new writes — it SHALL NOT be automatically removed or reset to an idle/ended state.

#### Scenario: A quiet source keeps its last status
- **WHEN** a passively-detected session's source file stops receiving new writes
- **THEN** the session's tab and last-reported status remain unchanged
- **AND** the session is only removed by explicit user dismissal

### Requirement: Header follows most-recently-active session
The collapsed header SHALL reflect whichever session most recently reported activity, independent of which session tab is currently selected in the drawer.

#### Scenario: Header switches to the newly active session
- **WHEN** a session other than the one currently reflected in the header reports new activity
- **THEN** the collapsed header updates to reflect that session's status

#### Scenario: Tab selection does not override header focus
- **WHEN** the user selects a different session's tab in the expanded drawer
- **THEN** the drawer's detail view reflects the selected session
- **AND** the collapsed header continues to reflect whichever session most recently reported activity, regardless of the tab selection

### Requirement: No historical replay on startup
The system SHALL only treat newly-written log content as session activity — pre-existing content already in a log file when tracking begins SHALL NOT register or update a session.

#### Scenario: Pre-existing log content is ignored
- **WHEN** the application starts and a detected log file already contains content from before the application started watching it
- **THEN** that pre-existing content does not create or update any session

#### Scenario: New content after startup is tracked
- **WHEN** new content is appended to a detected log file after the application has started watching it
- **THEN** a session is created or updated to reflect that new content
