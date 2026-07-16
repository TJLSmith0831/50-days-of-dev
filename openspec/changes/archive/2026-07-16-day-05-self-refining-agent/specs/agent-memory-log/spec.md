## ADDED Requirements

### Requirement: Insights are distilled on task completion
The system SHALL distill 3–5 insights to the memory log when a task stops, and SHALL NOT write to the log on individual iterations.

#### Scenario: Log written once per task
- **WHEN** the sorting task stops after 5 iterations
- **THEN** exactly one block of 3–5 insights is appended for that task, not one per iteration

#### Scenario: Capped tasks still record learnings
- **WHEN** a task stops by hitting the iteration cap rather than converging
- **THEN** insights are still distilled and appended

### Requirement: Distillation is grounded in measured deltas
The system SHALL prompt insight distillation against the task's recorded per-iteration metric deltas, not the model's impression of its work. Insights SHALL be constrained to transferable observations rather than task-specific tricks.

#### Scenario: Insight cites a measured movement
- **WHEN** insights are distilled for a task whose quality rose after helpers were extracted
- **THEN** the distillation prompt includes the per-iteration metric series so the insight can reference the actual movement

#### Scenario: Log is not a self-congratulation surface
- **WHEN** insights are distilled
- **THEN** the prompt requires transferable observations tied to metric changes, and excludes assessments of the agent's own performance

### Requirement: Memory log is human-readable Markdown
The system SHALL persist the memory log to `results/memory_log_<model>.md` as Markdown, with each task's block naming the task, its iteration count, its insights, and a confidence level.

#### Scenario: Log is legible without tooling
- **WHEN** a user opens `results/memory_log_<model>.md`
- **THEN** it reads as plain Markdown showing each completed task, its insights, and confidence, with no deserialization required

### Requirement: Memory log is read before generation
The system SHALL read the memory log and include it in the generation prompt for every task after the first. The prompt SHALL require the model to state which insights it is applying.

#### Scenario: Second task inherits the first task's learning
- **WHEN** the graph task begins after sorting has completed
- **THEN** the generation prompt contains sorting's insights and asks the model to name the ones it is applying

#### Scenario: First task with an empty log
- **WHEN** the first task begins and no memory log exists yet
- **THEN** generation proceeds with no memory section and does not error

### Requirement: Memory persists across sessions
The system SHALL append to an existing memory log rather than truncating it, so insights accumulate across separate runs.

#### Scenario: Second session builds on the first
- **WHEN** a run starts and `results/memory_log_<model>.md` already contains insights from a prior session
- **THEN** those insights are read into the first task's generation prompt and new insights are appended below them

### Requirement: Memory is namespaced per model
The system SHALL key the memory log to the configured model so that insights accumulated under one model are never read into a run under a different model.

#### Scenario: Switching models does not inherit foreign insights
- **WHEN** a run starts under `qwen2.5-coder` and a memory log exists from a prior `llama3.2` run
- **THEN** the `qwen2.5-coder` run reads no insights from the `llama3.2` log, and writes its insights to its own log

#### Scenario: Same model accumulates across runs
- **WHEN** a second run starts under the same model as a prior run
- **THEN** the prior run's insights are read into the first task's generation prompt
