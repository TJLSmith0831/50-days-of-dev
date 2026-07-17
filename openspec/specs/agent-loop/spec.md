## ADDED Requirements

### Requirement: Execute agent turn with LLM invocation
The system SHALL execute a single agent turn by invoking the configured LLM (Qwen3:14b via Ollama) with the current conversation context and system prompt.

#### Scenario: Successful LLM invocation
- **WHEN** the agent loop executes a turn with valid context
- **THEN** the LLM returns a response message with optional tool calls

#### Scenario: LLM invocation failure
- **WHEN** the LLM invocation fails (Ollama not running, model unavailable)
- **THEN** the system displays an error message and pauses for user input

### Requirement: Dispatch tool calls and process results
The system SHALL dispatch any tool calls returned by the LLM, execute them via the tool registry, and feed the results back to the LLM for the next turn.

#### Scenario: Single tool call
- **WHEN** the LLM returns a single tool call (e.g., Read)
- **THEN** the tool is executed and the result is added to the conversation context

#### Scenario: Multiple tool calls
- **WHEN** the LLM returns multiple tool calls in a single turn
- **THEN** all tools are executed and all results are added to the conversation context

#### Scenario: Tool execution failure
- **WHEN** a tool execution fails (file not found, permission error)
- **THEN** the error message is returned to the LLM for handling

### Requirement: Continue loop until completion
The system SHALL continue the agent loop until the LLM returns a response without tool calls or the user interrupts via /exit.

#### Scenario: Loop completes
- **WHEN** the LLM returns a response without tool calls
- **THEN** the agent loop pauses and waits for user input

#### Scenario: User interrupts
- **WHEN** the user enters /exit or presses Ctrl+C
- **THEN** the agent loop terminates gracefully

### Requirement: Maintain conversation state
The system SHALL maintain the conversation state including all messages, tool calls, and tool results across turns.

#### Scenario: State preservation
- **WHEN** the agent loop completes a turn
- **THEN** the conversation state includes all messages from previous turns

### Requirement: Support streaming token display
The system SHALL stream LLM tokens to the REPL as they are generated for real-time feedback.

#### Scenario: Streaming display
- **WHEN** the LLM generates tokens
- **THEN** tokens are displayed in the REPL as they arrive
