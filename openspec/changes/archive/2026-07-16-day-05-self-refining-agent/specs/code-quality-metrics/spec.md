## ADDED Requirements

### Requirement: Metrics are derived from tooling, never from the model
The system SHALL compute every reported metric from static analysis or measured execution. The system SHALL NOT ask the model to score, rate, or grade its own output on any reported axis.

#### Scenario: No self-reported scores
- **WHEN** any metric is written to state or to results output
- **THEN** its value originates from `radon`, `pylint`, the task's test suite, or `timeit`, and never from model output

### Requirement: Pass rate from the task's test suite
The system SHALL compute pass rate as passing tests divided by total tests, including held-out tests, expressed as a value from 0.0 to 1.0.

#### Scenario: Partial pass
- **WHEN** 7 of 10 tests pass
- **THEN** `pass_rate` is 0.7

#### Scenario: Unparseable code scores zero
- **WHEN** generated code fails `ast.parse()`
- **THEN** `pass_rate` is 0.0 and no tests are executed

### Requirement: Composite quality score from radon and pylint
The system SHALL compute a 0–100 composite quality score weighted 40% maintainability index (`radon`), 30% style (derived from `pylint` violations), and 30% cyclomatic complexity (`radon`).

#### Scenario: Composite is computed from all three components
- **WHEN** quality is calculated for parseable code
- **THEN** the score reflects the maintainability index, the pylint violation count, and the cyclomatic complexity, in the stated 40/30/30 weighting

#### Scenario: Components are recoverable, not just the blend
- **WHEN** a quality score is recorded
- **THEN** its maintainability, style, and complexity components remain individually available for critique

### Requirement: Runtime measured by timeit, minimum of repeated runs
The system SHALL measure runtime with `timeit.repeat()` over at least 5 repeats against a fixed worst-case input, and SHALL report the minimum observed time in milliseconds.

#### Scenario: Minimum is reported, not mean
- **WHEN** 5 timed repeats yield 800ms, 810ms, 950ms, 1400ms, and 805ms
- **THEN** the reported `performance_ms` is 800

#### Scenario: Deterministic input across iterations
- **WHEN** runtime is measured for the same task on successive iterations
- **THEN** the timing input is identical across iterations, so the numbers are comparable

### Requirement: Runtime axis is optional per task
The system SHALL support tasks that define no performance baseline. For such tasks the system SHALL omit `performance_ms` rather than record a placeholder value, and downstream output SHALL represent it as absent.

#### Scenario: REPL task omits runtime
- **WHEN** the repl task is scored
- **THEN** `pass_rate` and `quality_score` are recorded, `performance_ms` is absent, and no zero or sentinel is substituted

### Requirement: Axes are never collapsed into a single number
The system SHALL report pass rate, quality score, and runtime as separate values in state and in all output. The system SHALL NOT blend them into one headline score.

#### Scenario: Quality gain with pass-rate loss stays visible
- **WHEN** an iteration raises quality from 60 to 80 while dropping pass rate from 0.9 to 0.4
- **THEN** both movements appear separately in the output, making the regression visible

### Requirement: Generated code executes in a subprocess with a timeout
The system SHALL write generated code to a temporary file and execute it via `subprocess` with a wall-clock timeout. The system SHALL NOT `exec` or `eval` generated code in the host process.

#### Scenario: Infinite loop does not hang the run
- **WHEN** generated code contains a non-terminating loop
- **THEN** the subprocess is terminated at the timeout, the iteration scores 0.0 pass rate, and the timeout is fed back as critique

#### Scenario: Crash does not take down the REPL
- **WHEN** generated code raises or calls `sys.exit`
- **THEN** the failure is confined to the subprocess and the loop continues

### Requirement: Per-task results written as JSON and CSV, keyed by model
On task completion the system SHALL write `results/<task>_<model>.json` and
`results/<task>_<model>.csv` containing one record per iteration with iteration number,
pass rate, quality score, runtime where applicable, and improvement delta, plus the
task's stop reason and final metrics. The JSON SHALL also record the model that produced
it.

Results keyed by task alone are silently overwritten by the next `--model` run, leaving
numbers on disk with nothing recording who produced them — the mechanism by which one
model's curves were once written up as another's. The filename keys the artifact; the
`model` field keeps the attribution attached to the data even if the file is renamed.

#### Scenario: Both formats emitted
- **WHEN** the sorting task completes under `--model llama3.2`
- **THEN** `results/sorting_llama3.2.json` and `results/sorting_llama3.2.csv` exist and contain one row or record per iteration
- **AND** the JSON's `model` field reads `llama3.2`

#### Scenario: Two models do not collide
- **WHEN** the sorting task is run under `llama3.2` and then under `qwen2.5-coder`
- **THEN** both runs' results exist side by side, and neither overwrote the other

#### Scenario: Absent runtime is represented as empty
- **WHEN** results are written for the repl task
- **THEN** the runtime field is empty rather than zero in both the JSON and the CSV
