## ADDED Requirements

### Requirement: Trigger handoff via /go command or UI button
The system SHALL trigger the identical handoff function whether the user types `/go` in chat or clicks the corresponding UI button.

#### Scenario: Triggering via chat command
- **WHEN** the user types `/go` in an idle thread
- **THEN** the system begins the handoff sequence

#### Scenario: Triggering via UI button
- **WHEN** the user clicks the `/go` button in an idle thread
- **THEN** the system begins the same handoff sequence as the chat command

### Requirement: Gate mode switches on idle state
The system SHALL reject a mode switch (either direction) while a call is in flight (an in-flight executor response, tool call, or turn), and allow it once the thread returns to idle.

#### Scenario: Attempting /go while a call is in flight
- **WHEN** the user invokes `/go` while the executor is mid-turn
- **THEN** the system rejects the switch and the thread remains in its current mode until idle

### Requirement: Hand off to go-mode with carried-forward history
The system SHALL, on a valid `/go`, terminate the spec-mode executor process and spawn a fresh go-mode executor with the full conversation history carried forward, with no summarization call.

#### Scenario: Handoff with no existing OpenSpec change
- **WHEN** `/go` is invoked on a thread whose `.meta.json` has `openSpecChangeName: null`
- **THEN** the system spawns a go-mode executor (Claude: `--resume <session-id> --permission-mode acceptEdits`; Codex: `--sandbox workspace-write`) and the executor continues the conversation directly

#### Scenario: Handoff with an existing OpenSpec change
- **WHEN** `/go` is invoked on a thread whose `.meta.json` has a non-null `openSpecChangeName`
- **THEN** the system spawns a go-mode executor and sends `/grill-apply <change-name>` (Claude) or `$grill-apply <change-name>` (Codex) as the first message

### Requirement: React to unexpected executor exit
The system SHALL, on receiving an `ExecutorEvent::Crashed`, show an inline banner in the chat pane, revert the thread's `currentMode` to `spec` in its `.meta.json`, and leave the JSONL history untouched.

#### Scenario: Executor crashes mid-session
- **WHEN** the live executor process emits a `Crashed` event
- **THEN** the system displays a chat-pane banner stating the executor process ended unexpectedly, sets `currentMode` back to `spec`, and preserves all existing session history

### Requirement: Make the harness UI a pass-through wrapper once live
The system SHALL, once a go-mode executor is spawned, forward user input directly to the live executor process and stream its output back, rather than treating it as a fire-and-forget dispatch.

#### Scenario: Sending a message during an active go-mode session
- **WHEN** the user sends a message while a go-mode executor is live
- **THEN** the system forwards it directly to the executor process and streams the response back into the chat pane
