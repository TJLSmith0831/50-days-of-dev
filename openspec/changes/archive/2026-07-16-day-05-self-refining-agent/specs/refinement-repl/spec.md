## ADDED Requirements

### Requirement: Interactive REPL is the default entrypoint
The system SHALL start an interactive Rich REPL when `uv run main.py` is invoked with no arguments.

#### Scenario: Bare invocation opens the REPL
- **WHEN** the user runs `uv run main.py`
- **THEN** an interactive prompt opens and awaits a command, and no task starts automatically

### Requirement: REPL command surface
The REPL SHALL support solving a named task, displaying accumulated results, and exiting. An unrecognized command SHALL produce a usage message rather than an error trace.

#### Scenario: Solve a task by name
- **WHEN** the user enters `solve sorting`
- **THEN** the sorting task begins iterating and per-iteration metrics render live

#### Scenario: Show results
- **WHEN** the user enters `show results` after a task has completed
- **THEN** the accumulated per-iteration metrics render as a table

#### Scenario: Unknown command
- **WHEN** the user enters an unrecognized command
- **THEN** the REPL prints a usage message and continues awaiting input

#### Scenario: Exit
- **WHEN** the user enters `quit`
- **THEN** the REPL exits with status 0

### Requirement: Live per-iteration metric display
During iteration the REPL SHALL render each iteration's number, pass rate, quality score, and runtime where applicable, as they are computed.

#### Scenario: Metrics render per iteration
- **WHEN** iteration 2 of the sorting task completes
- **THEN** the REPL displays iteration 2's pass rate, quality score, and runtime before iteration 3 begins

#### Scenario: Task without a runtime axis
- **WHEN** an iteration of the repl task completes
- **THEN** pass rate and quality render and the runtime column shows as absent rather than as zero

#### Scenario: Stop reason is surfaced
- **WHEN** a task stops
- **THEN** the REPL states whether it converged or hit the iteration cap

### Requirement: Demo mode runs all tasks unattended
The system SHALL run all three tasks sequentially to plateau or cap, without interactive input, when invoked as `uv run main.py --demo`, and SHALL write results for each task on completion.

#### Scenario: Demo runs end to end
- **WHEN** the user runs `uv run main.py --demo`
- **THEN** sorting, graph, and repl each run to plateau or cap in order, and `results/` contains JSON and CSV for each plus the memory log

#### Scenario: Demo reports elapsed time
- **WHEN** a demo run finishes
- **THEN** the total elapsed time is reported

### Requirement: Model is selected by a required flag
The system SHALL require a `--model` flag naming a local Ollama model, and SHALL NOT
provide a default. The flag SHALL apply to both the interactive REPL and demo mode.

Every curve and the memory log are keyed by model, so an implicit default lets a run be
attributed to a model that did not produce it — which is what happened: a
`qwen2.5-coder` run was banked and written up as `llama3.2`'s.

#### Scenario: Model is required
- **WHEN** the user runs `uv run main.py --demo` with no `--model` flag
- **THEN** the run exits with a usage error naming `--model` as required, and no task runs

#### Scenario: Model override
- **WHEN** the user runs `uv run main.py --demo --model qwen2.5-coder`
- **THEN** the run uses `qwen2.5-coder` and writes results under that model's memory log

#### Scenario: Active model is visible
- **WHEN** a run starts
- **THEN** the model in use is displayed, so a recorded demo shows which model produced the curve

### Requirement: Missing Ollama fails with a clear message
The system SHALL verify that Ollama is reachable and the configured model is available before starting a task, and SHALL report a clear, actionable message rather than a stack trace when it is not.

#### Scenario: Ollama not running
- **WHEN** the user starts a task and Ollama is not reachable
- **THEN** the REPL prints a message naming Ollama as unreachable and how to start it, and exits without a traceback

#### Scenario: Model not pulled
- **WHEN** the configured model is not present in the local Ollama instance
- **THEN** the REPL prints a message naming the missing model and the command to pull it
