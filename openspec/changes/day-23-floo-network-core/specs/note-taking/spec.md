## ADDED Requirements

### Requirement: Open the note-creation command bar
The system SHALL open a floating command bar for naming a new note when the user presses ⌘N or clicks the "Create note" button in the Notes sidebar.

#### Scenario: Opening via keyboard shortcut
- **WHEN** the user presses ⌘N
- **THEN** the system opens a command bar with a text input for the new note's filename

#### Scenario: Opening via sidebar button
- **WHEN** the user clicks "Create note" in the Notes tab of the sidebar
- **THEN** the system opens the same command bar as ⌘N

### Requirement: Create a note without an approval gate
The system SHALL write a new note to disk immediately when the user submits a filename from the command bar, with no intermediate confirmation step.

#### Scenario: Submitting a filename
- **WHEN** the user types a filename and presses Enter in the command bar
- **THEN** the system resolves the name to a path under the active project's notes location, writes the file to disk, and opens it in the two-tab Edit/Preview markdown pane

#### Scenario: Canceling before submission
- **WHEN** the user dismisses the command bar without pressing Enter
- **THEN** the system creates no file and returns to the prior view

### Requirement: Auto-save hand-edits to an existing note
The system SHALL save edits to an already-created note automatically, without re-prompting the user.

#### Scenario: Editing an open note
- **WHEN** the user types in the Edit tab of an already-created note
- **THEN** the system writes the updated content to disk without displaying any confirmation prompt
