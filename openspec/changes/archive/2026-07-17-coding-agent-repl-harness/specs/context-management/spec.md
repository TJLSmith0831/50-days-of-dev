## ADDED Requirements

### Requirement: Count tokens in conversation context
The system SHALL count tokens in the conversation context using tiktoken or character-based fallback.

#### Scenario: Token count with tiktoken
- **WHEN** tiktoken is available
- **THEN** the system uses tiktoken for accurate token counting

#### Scenario: Token count fallback
- **WHEN** tiktoken is not available
- **THEN** the system uses character-based estimation (4 chars per token)

### Requirement: Truncate context when exceeding limit
The system SHALL truncate the conversation context when it exceeds the configured max context tokens (default 4000).

#### Scenario: Context truncation
- **WHEN** the context exceeds max context tokens
- **THEN** the oldest messages are removed until context is within limit

#### Scenario: Preserve system prompt
- **WHEN** truncating context
- **THEN** the system prompt is always preserved

#### Scenario: Preserve recent messages
- **WHEN** truncating context
- **THEN** the last N messages (default 10) are always preserved

### Requirement: Preserve tool call results
The system SHALL preserve tool call results during truncation to maintain conversation coherence.

#### Scenario: Tool result preservation
- **WHEN** truncating context
- **THEN** tool call results are preserved if they are within the recent message window

### Requirement: Configure max context tokens
The system SHALL allow configuration of max context tokens via environment variable or config file.

#### Scenario: Default configuration
- **WHEN** no configuration is provided
- **THEN** the system uses the default max context tokens (4000)

#### Scenario: Custom configuration
- **WHEN** a custom max context tokens value is configured
- **THEN** the system uses the configured value

### Requirement: Notify user of truncation
The system SHALL notify the user when context truncation occurs.

#### Scenario: Truncation notification
- **WHEN** context is truncated
- **THEN** the system displays a message indicating truncation occurred

### Requirement: Summarize old context (deferred)
The system SHALL defer intelligent summarization of old context to a future version.

#### Scenario: No summarization in v1
- **WHEN** context is truncated in v1
- **THEN** old messages are simply removed without summarization
