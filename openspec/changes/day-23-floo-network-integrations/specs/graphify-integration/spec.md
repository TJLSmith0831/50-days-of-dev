## ADDED Requirements

### Requirement: Run Graphify against the active project
The system SHALL shell out to `graphify extract <project-dir> --out <out-dir> --no-viz --code-only` for a safe, key-less, JSON-only run, scoped to the active project's root (or a user-selected subdirectory).

#### Scenario: Running Graphify
- **WHEN** the user triggers a Graphify run from the results pane
- **THEN** the system spawns `graphify extract` with the active project (or selected subdirectory) as the target and `<out-dir>` set to that project's `graphify-out/` unless overridden

#### Scenario: Toggling run options
- **WHEN** the user enables the incremental, code-only, or deep-mode toggle before running
- **THEN** the system adds the corresponding flag (`--update`, `--code-only`, `--mode deep`) to the invocation

### Requirement: Display Graphify results in a dedicated pane
The system SHALL read `GRAPH_REPORT.md` and `graph.json` from the output directory after a successful run and render them in a results pane, with a query surface for `graphify query`/`path`/`explain`.

#### Scenario: Viewing results after a run
- **WHEN** a Graphify run completes successfully
- **THEN** the system loads `GRAPH_REPORT.md` as a summary view and `graph.json` as an explorable, filterable graph in the results pane

#### Scenario: Querying the graph
- **WHEN** the user submits a question in the query surface
- **THEN** the system invokes `graphify query "<question>" --graph <out-dir>/graph.json` and displays the result

### Requirement: Auto-inject a bounded report summary into the thread
The system SHALL, after each successful Graphify run, append a `role: "tool"` message to the active thread containing the first 4000 characters of `GRAPH_REPORT.md` and a note that the full report and graph are available in the results pane.

#### Scenario: Summary injection after a run
- **WHEN** a Graphify run completes successfully
- **THEN** the system appends a `role: "tool"` JSONL message with the truncated report summary and a pointer to the full results pane

### Requirement: Surface run failures without crashing
The system SHALL surface a Graphify process failure (non-zero exit) as an inline error in the results pane and SHALL NOT inject any message into the thread for a failed run.

#### Scenario: Graphify process fails
- **WHEN** `graphify extract` exits non-zero
- **THEN** the system shows the process's stderr output in the results pane and does not append any message to the thread's session log
