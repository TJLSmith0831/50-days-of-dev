## ADDED Requirements

### Requirement: Integrate grill-with-docs skill
The system SHALL integrate the grill-with-docs skill for interactive requirements gathering with documentation.

#### Scenario: Invoke grill-with-docs
- **WHEN** the user requests grilling with documentation
- **THEN** the system invokes the grill-with-docs skill with the current context

#### Scenario: Grill-with-docs question
- **WHEN** the skill returns a question
- **THEN** the question is displayed to the user in the REPL

#### Scenario: Grill-with-docs response
- **WHEN** the user responds to a grill question
- **THEN** the response is passed back to the skill

### Requirement: Integrate grill-me skill
The system SHALL integrate the grill-me skill for interactive requirements gathering without documentation.

#### Scenario: Invoke grill-me
- **WHEN** the user requests grilling without documentation
- **THEN** the system invokes the grill-me skill with the current context

#### Scenario: Grill-me question
- **WHEN** the skill returns a question
- **THEN** the question is displayed to the user in the REPL

#### Scenario: Grill-me response
- **WHEN** the user responds to a grill question
- **THEN** the response is passed back to the skill

### Requirement: Pass conversation context to skills
The system SHALL pass the current conversation context to grill skills for context-aware questioning.

#### Scenario: Context passing
- **WHEN** a grill skill is invoked
- **THEN** the conversation context is passed to the skill

### Requirement: Incorporate skill outputs into agent context
The system SHALL incorporate grill skill outputs (questions, answers, decisions) into the agent's context for spec generation.

#### Scenario: Skill output incorporation
- **WHEN** a grill skill completes
- **THEN** the skill's outputs are added to the agent's context

### Requirement: Handle skill unavailability
The system SHALL handle cases where grill skills are not installed or unavailable.

#### Scenario: Skill not installed
- **WHEN** a grill skill is not installed
- **THEN** the system displays an error message indicating the skill is required

#### Scenario: Skill execution failure
- **WHEN** a grill skill execution fails
- **THEN** the system displays an error message and allows the user to continue without grilling
