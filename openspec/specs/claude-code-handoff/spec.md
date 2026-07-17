## ADDED Requirements

### Requirement: Trigger handoff on /handoff command
The system SHALL trigger the Claude Code handoff flow when the user enters /handoff.

#### Scenario: Handoff trigger
- **WHEN** the user enters /handoff
- **THEN** the system initiates the Claude Code handoff flow

### Requirement: Confirm handoff with user
The system SHALL confirm with the user before proceeding with the handoff.

#### Scenario: User confirmation
- **WHEN** the user confirms the handoff
- **THEN** the system proceeds with Claude Code headless API call

#### Scenario: User cancellation
- **WHEN** the user cancels the handoff
- **THEN** the system returns to the REPL without calling Claude Code

### Requirement: Call Claude Code headless API
The system SHALL call the Claude Code headless API to run opsx:apply with the generated spec.

#### Scenario: Successful API call
- **WHEN** the Claude Code headless API is called successfully
- **THEN** the API executes opsx:apply and returns the result

#### Scenario: API call failure
- **WHEN** the Claude Code headless API call fails
- **THEN** the system displays an error message

### Requirement: Display Claude Code output in REPL
The system SHALL display Claude Code output (logs, progress, results) in the REPL.

#### Scenario: Output display
- **WHEN** Claude Code returns output
- **THEN** the output is displayed in the REPL

### Requirement: Return to REPL after handoff
The system SHALL return to the REPL after the handoff completes (success or failure).

#### Scenario: Return after success
- **WHEN** the handoff completes successfully
- **THEN** the system returns to the REPL and displays a success message

#### Scenario: Return after failure
- **WHEN** the handoff fails
- **THEN** the system returns to the REPL and displays an error message

### Requirement: Check Claude Code availability
The system SHALL check for Claude Code installation and API key before handoff.

#### Scenario: Claude Code installed
- **WHEN** Claude Code is installed and API key is configured
- **THEN** the handoff proceeds

#### Scenario: Claude Code not installed
- **WHEN** Claude Code is not installed
- **THEN** the system displays an error message indicating Claude Code is required

#### Scenario: API key missing
- **WHEN** Claude Code is installed but API key is missing
- **THEN** the system displays an error message indicating API key is required

### Requirement: Support manual opsx:apply fallback
The system SHALL allow the user to manually run opsx:apply if the headless API is unavailable.

#### Scenario: Manual fallback
- **WHEN** the headless API is unavailable
- **THEN** the system provides instructions for manual opsx:apply execution
