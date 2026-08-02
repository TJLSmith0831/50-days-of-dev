## ADDED Requirements

### Requirement: Quit affordance
The notch SHALL provide an in-app way to exit the application that is reachable whether or not the drawer is expanded.

#### Scenario: Quit control is visible in the expanded drawer
- **WHEN** the user expands the drawer
- **THEN** a "Quit" control is visible

#### Scenario: Right-click reveals Quit
- **WHEN** the user right-clicks the notch with the drawer expanded
- **THEN** a context menu appears containing a "Quit" action

#### Scenario: Quit exits the application
- **WHEN** the user activates any of the notch's Quit controls
- **THEN** the application exits

### Requirement: Scrollable session tab strip
The session tab strip SHALL remain fully reachable via horizontal scrolling when the number of session tabs exceeds the available width — it SHALL NOT clip tabs or crowd out the launch control with no indication anything is hidden.

#### Scenario: Tabs beyond the visible width are reachable by scroll
- **WHEN** the number of session tabs exceeds the drawer's visible width
- **THEN** the tab strip can be scrolled horizontally to reach every tab
- **AND** the launch control remains visible and usable

### Requirement: Prompt queue indicator
Any prompt card backed by a queue of more than one pending item (permission requests, launch failures) SHALL indicate that additional items are waiting.

#### Scenario: Multiple pending permission requests
- **WHEN** more than one permission request is pending
- **THEN** the permission-prompt card displays a count of the additional requests waiting behind the one shown

#### Scenario: Multiple pending launch failures
- **WHEN** more than one launch failure is pending
- **THEN** the launch-failure prompt card displays a count of the additional failures waiting behind the one shown

### Requirement: Genuine empty header state
The collapsed header SHALL render a neutral empty state — no fabricated agent, status, or token gauge — when no session exists and no agent activity has been reported.

#### Scenario: No sessions and no activity yet
- **WHEN** no sessions exist
- **AND** no agent activity has been reported via the event endpoint or passive detection since the application started
- **THEN** the collapsed header shows a neutral "no agent running" state
- **AND** no token gauge is drawn
