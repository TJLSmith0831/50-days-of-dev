## ADDED Requirements

### Requirement: Append messages to a thread's session log
The system SHALL persist each message as one JSON object per line, appended to `~/.floo-network/projects/<project-hash>/threads/<thread-id>.jsonl`, with the fields `seq` (monotonic per-thread integer), `ts` (ISO-8601), `role` (`user | assistant | system | tool`), `mode` (`spec | go`, the mode active when the message was written), and `content`.

#### Scenario: Appending a message
- **WHEN** a new message is written to a thread
- **THEN** the system appends one JSON line plus a trailing newline to that thread's `.jsonl` file and calls fsync before returning

#### Scenario: Never mutating past messages
- **WHEN** the session log already contains messages
- **THEN** the system only ever appends new lines and never rewrites, reorders, or deletes an existing line

### Requirement: Read a thread's session history
The system SHALL read a thread's full message history by parsing its `.jsonl` file line by line, in `seq` order.

#### Scenario: Reading a complete, well-formed log
- **WHEN** the system reads a thread's `.jsonl` file and every line parses as valid JSON
- **THEN** the system returns the full ordered list of messages

#### Scenario: Reading a log with a torn trailing write
- **WHEN** the system reads a thread's `.jsonl` file and the final line fails to parse as valid JSON
- **THEN** the system drops that line, logs the thread ID and byte offset to `~/.floo-network/harness.log`, and returns the remaining well-formed messages without surfacing an error to the user
