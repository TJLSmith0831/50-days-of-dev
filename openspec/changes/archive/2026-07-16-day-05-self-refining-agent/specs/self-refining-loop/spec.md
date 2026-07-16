## ADDED Requirements

### Requirement: LangGraph state machine drives the refine cycle
The system SHALL implement the refine cycle as a LangGraph state machine whose nodes are `generate_code`, `run_tests`, `calculate_quality`, `measure_performance`, `critique_code`, `revise_code`, `track_improvement`, and `update_memory`, connected by conditional edges. Each node SHALL be a function taking the state and returning the updated state.

#### Scenario: Full iteration traverses the cycle
- **WHEN** a task begins its first iteration
- **THEN** the graph executes generate → test → quality → performance → critique → revise → track, and the resulting state carries a populated `current_code`, `pass_rate`, `quality_score`, and `critique`

#### Scenario: Iteration state is inspectable after the run
- **WHEN** an iteration completes
- **THEN** the per-iteration metrics and critique are retained in state and recoverable for output without re-running the model

### Requirement: The agent never receives test source code
The system SHALL NOT include test source code in any prompt sent to the model. Prompts SHALL contain the task's behavioral description only. Critique SHALL identify failing tests by name and assertion message, never by test body.

#### Scenario: Generation prompt excludes tests
- **WHEN** `generate_code` builds its prompt for a task
- **THEN** the prompt contains the task's behavioral description and the memory log, and contains no test function bodies or assertion source

#### Scenario: Critique names failures without revealing the grader
- **WHEN** 3 of 10 tests fail
- **THEN** the critique names the 3 failing tests and their assertion messages, and does not include the tests' source code

### Requirement: A held-out test set is excluded from critique
Each task SHALL define a held-out subset of its test suite that is never surfaced in critique in any form. The held-out subset SHALL contribute to the scored pass rate.

#### Scenario: Held-out failures are scored but not reported
- **WHEN** the agent's code fails a held-out test
- **THEN** the failure lowers the reported `pass_rate` and does not appear in the critique text

### Requirement: Critique concatenates all three signals
The system SHALL construct critique from all available signals at once — test failures, code-quality feedback, and timing feedback — and SHALL leave prioritization to the model rather than staging the signals across iterations.

#### Scenario: Multi-signal critique
- **WHEN** code passes all tests but has cyclomatic complexity above the task threshold and exceeds its performance baseline
- **THEN** the critique includes both the complexity finding and the timing finding in a single message

#### Scenario: Task without a runtime axis
- **WHEN** critique is built for a task that defines no performance baseline
- **THEN** the critique includes the test and quality signals and omits the timing signal

### Requirement: Plateau detection with a minimum iteration floor
The system SHALL stop iterating on a task when the change in composite quality score is less than 2% for 2 consecutive iterations. Plateau detection SHALL NOT be armed before iteration 3.

#### Scenario: Convergence stops the loop
- **WHEN** iterations 4 and 5 each change the composite quality score by less than 2%
- **THEN** the loop stops and the task is recorded as converged

#### Scenario: Early flat iteration does not stop the loop
- **WHEN** iteration 2 changes the composite quality score by less than 2%
- **THEN** the loop continues, because plateau detection is not armed before iteration 3

### Requirement: Hard iteration cap per task
The system SHALL stop iterating on a task after 10 iterations regardless of plateau state, and SHALL record cap-reached distinctly from converged.

#### Scenario: Cap terminates a non-converging task
- **WHEN** a task reaches iteration 10 without plateauing
- **THEN** the loop stops and the task result records termination by cap, not by convergence

#### Scenario: Output distinguishes the two stop reasons
- **WHEN** results are written for a capped task and a converged task
- **THEN** each records its own distinct stop reason

### Requirement: Best code is retained across iterations, ranked correctness-first
The system SHALL retain the best version of the code seen so far and SHALL report it as the task's final code even when a later iteration scores lower. Versions SHALL be ranked by pass rate first, with composite quality score breaking ties only. Ranking SHALL order the axes rather than blend them into a single number.

#### Scenario: Regression does not lose the best version
- **WHEN** iteration 4 scores 88 and iteration 5 scores 71 at equal pass rate
- **THEN** the task's final reported code is iteration 4's

#### Scenario: Correctness outranks a marginal quality gain
- **WHEN** iteration 6 passes 33% of tests at quality 49.83 and iteration 7 passes 11% at quality 49.87
- **THEN** the task's final reported code is iteration 6's, because a higher pass rate outranks a higher quality score

#### Scenario: Quality breaks ties at equal correctness
- **WHEN** two iterations have the same pass rate and different quality scores
- **THEN** the higher-quality version is retained

### Requirement: Invalid generated code is scored and fed back, not fatal
The system SHALL strip Markdown fences from model output and validate it with `ast.parse()` before scoring. Code failing to parse SHALL score zero on all axes, and the parse error SHALL be supplied as critique for the next iteration.

#### Scenario: Unparseable generation continues the loop
- **WHEN** the model returns prose or truncated code that fails `ast.parse()`
- **THEN** the iteration scores zero, the parse error becomes the critique, and the loop proceeds to the next iteration without raising

#### Scenario: Fenced code is unwrapped
- **WHEN** the model returns code wrapped in triple-backtick fences
- **THEN** the fences are stripped and the inner source is scored

### Requirement: Tasks run sequentially in fixed order
The system SHALL run tasks one at a time to completion in the order sorting → graph → repl, and SHALL NOT interleave iterations across tasks.

#### Scenario: Task order and isolation
- **WHEN** a demo run executes
- **THEN** sorting runs to plateau or cap first, then graph, then repl, and each produces its own independent metric series
