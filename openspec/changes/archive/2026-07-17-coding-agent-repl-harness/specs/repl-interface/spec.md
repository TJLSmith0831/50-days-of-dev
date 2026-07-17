## ADDED Requirements

### Requirement: Display streaming tokens
The system SHALL display LLM tokens in the REPL as they are generated using Rich's live rendering.

#### Scenario: Token streaming
- **WHEN** the LLM generates tokens
- **THEN** tokens are displayed in real-time in the REPL

#### Scenario: Thinking spinner
- **WHEN** the LLM is processing before first token arrives
- **THEN** a spinner is displayed to indicate thinking state

### Requirement: Display speaker layout
The system SHALL display messages with speaker labels (agent in green, user in blue) for clear conversation flow.

#### Scenario: Agent message
- **WHEN** the agent generates a response
- **THEN** the message is displayed with a green "Agent:" label

#### Scenario: User message
- **WHEN** the user enters input
- **THEN** the message is displayed with a blue "You:" label

### Requirement: Expand @file mentions
The system SHALL expand @file mentions to absolute file paths before tool calls.

#### Scenario: File mention expansion
- **WHEN** the user enters @main.py in the REPL
- **THEN** the mention is expanded to the absolute path of main.py

#### Scenario: Invalid file mention
- **WHEN** the user enters @nonexistent.py
- **THEN** the system displays an error indicating the file was not found

### Requirement: Support slash commands
The system SHALL support slash commands: /help, /save, /sessions, /exit, /handoff.

#### Scenario: /help command
- **WHEN** the user enters /help
- **THEN** the system displays available commands and usage

#### Scenario: /save command
- **WHEN** the user enters /save
- **THEN** the current session is saved to the database

#### Scenario: /sessions command
- **WHEN** the user enters /sessions
- **THEN** the system lists available sessions with metadata

#### Scenario: /exit command
- **WHEN** the user enters /exit
- **THEN** the REPL terminates gracefully

#### Scenario: /handoff command
- **WHEN** the user enters /handoff
- **THEN** the system initiates Claude Code handoff flow

### Requirement: Display tool outputs in rich panels
The system SHALL display tool outputs (code, search results) in Rich panels with syntax highlighting.

#### Scenario: Code display
- **WHEN** a Read tool returns code
- **THEN** the code is displayed in a panel with syntax highlighting

#### Scenario: Search results display
- **WHEN** a Web Search tool returns results
- **THEN** the results are displayed in a formatted panel

### Requirement: Accept user input
The system SHALL accept user input via the REPL and pass it to the agent loop.

#### Scenario: User input
- **WHEN** the user enters text and presses Enter
- **THEN** the input is passed to the agent loop as a HumanMessage

#### Scenario: Empty input
- **WHEN** the user presses Enter without text
- **THEN** the system prompts for input again
