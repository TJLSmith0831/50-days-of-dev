## 1. Scaffold and environment

- [x] 1.1 Update `day-05-self-refining-agent/pyproject.toml` deps to `langgraph`, `langchain-ollama`, `radon`, `pylint`, `rich`, `python-dotenv`; keep `[tool.uv] package = false`.
- [x] 1.2 Run `uv sync` and confirm `radon`, `pylint`, and `langgraph` import cleanly.
- [x] 1.3 Confirm Ollama is reachable and `llama3.2` is pulled; optionally `ollama pull qwen2.5-coder` for the comparison run.
- [x] 1.4 Add `results/` to `.gitignore` with an exception for `results/memory_log_*.md`.

## 2. Sandboxed execution (foundation — everything scores through this)

- [x] 2.1 Implement `utils.strip_fences()` and `utils.validate_syntax()` — unwrap Markdown fences, `ast.parse()`, return the parse error rather than raising.
- [x] 2.2 Implement `utils.run_in_subprocess()` — write code to a temp file, run via `subprocess` with a wall-clock timeout, capture stdout/stderr/returncode, never `exec` in-process.
- [x] 2.3 Self-check: assert an infinite-loop snippet is killed at the timeout and a `sys.exit(1)` snippet does not take down the caller.

## 3. Metrics layer

- [x] 3.1 Implement `metrics.calculate_pass_rate()` — run the task suite in the subprocess, count passes over total including held-out, return 0.0 for unparseable code.
- [x] 3.2 Implement `metrics.calculate_code_quality_score()` — `radon` maintainability index + cyclomatic complexity, `pylint` violation count, blended 40/30/30, returning components alongside the composite.
- [x] 3.3 Implement `metrics.measure_performance()` — `timeit.repeat()` with ≥5 repeats on a fixed input, return the minimum in ms; return `None` for tasks with no baseline.
- [x] 3.4 Implement `metrics.write_results()` — emit `results/<task>_<model>.json` and `.csv` per iteration, with absent runtime written as empty rather than zero, plus stop reason and final metrics. (Keyed by model, and the model recorded inside the JSON: an unkeyed `<task>.json` was silently overwritten by the next `--model` run.)
- [x] 3.5 Self-check: assert a known-good and known-bad snippet score in the expected direction on each axis, and that `timeit` returns the minimum of a seeded sample.

## 4. Tasks

> The three tasks are `Task` **instances** (`SORTING_TASK`, `GRAPH_TASK`, `REPL_TASK`), not subclasses: they differ in data, not behavior, so a subclass per task would add a type and no capability.

- [x] 4.1 Implement the `Task` dataclass — behavioral `prompt`, `test_suite()`, `held_out_suite()`, `quality_criteria`, and optional `performance_baseline`.
- [x] 4.2 Implement `SortingTask` — randomized-pivot quicksort; visible + held-out tests (empty, single, duplicates, sorted, reverse); baseline recalibrated to 10ms at n=10k with a fixed seed (measured; the design's ~100ms guess was unmissable and made the timing signal inert).
- [x] 4.3 Implement `GraphTask` — shortest path; visible + held-out tests; seeded graph generation so the timing input is identical across iterations (design open question — resolved: seeded); baseline recalibrated to 5ms (measured; design guessed ~200ms).
- [x] 4.4 Implement `REPLTask` — Ollama-backed REPL; tests stub the network boundary (`ollama` module / HTTP call) so no live model is hit and no solution shape is dictated; **no** `performance_baseline`.
- [x] 4.5 Verify no task passes test source into any prompt — only the behavioral description. (Asserted in `tasks._self_check`, not just reviewed by eye.)

## 5. Memory log

- [x] 5.1 Implement `memory.read_log(model)` — return `results/memory_log_<model>.md` contents, empty string when absent.
- [x] 5.2 Implement `memory.distill_insights()` — prompt against the recorded per-iteration metric deltas for 3–5 transferable insights; forbid self-assessment.
- [x] 5.3 Implement `memory.append_log()` — append a Markdown block (task, iteration count, insights, confidence); never truncate an existing log.
- [x] 5.4 Self-check: assert a log from a prior run survives a new run and is read into the first task's prompt, and that a run under a different model reads none of it. (Persistence/namespacing in `memory._self_check`; prompt injection in `graph._self_check`.)

## 6. LangGraph loop

- [x] 6.1 Define `AgentState` per `architecture.md` — add `stop_reason` and per-axis quality components; make `performance_ms` optional. (Also added `scored_code`: metrics describe the code that entered the iteration, while `current_code` holds the not-yet-scored revision.)
- [x] 6.2 Implement `generate_code` — behavioral prompt + memory log, no test source; require the model to name applied insights when the log is non-empty.
- [x] 6.3 Implement `run_tests`, `calculate_quality`, `measure_performance` nodes over the metrics layer.
- [x] 6.4 Implement `critique_code` — concatenate all three signals, name failing tests and assertion messages only, exclude held-out failures and test source, omit timing for tasks without a baseline.
- [x] 6.5 Implement `revise_code` — critique + memory log into a revision.
- [x] 6.6 Implement `track_improvement` — append delta, retain best-scoring code, arm plateau only from iteration 3, set `stop_reason` to converged or capped. (Retention ranks `(pass_rate, quality)` correctness-first after the first real run retained 11%-passing code over 33%-passing code for +0.04 quality; spec + design updated.)
- [x] 6.7 Implement `update_memory` node and wire the conditional edges per `architecture.md`. (Back edge goes to `run_tests`, not `generate_code` as the diagram showed — regenerating would discard the revision and the loop would never refine. Reconciled in 8.5.)
- [x] 6.8 Self-check: assert plateau does not fire at iteration 2, fires after two sub-2% deltas from iteration 3, that the cap stops at 10 with `stop_reason` capped, and that a scoring regression does not lose the best version.

## 7. REPL and demo

- [x] 7.1 Implement the Ollama preflight — reachable + model present, actionable message and clean exit, no traceback. (Both paths exercised.)
- [x] 7.2 Implement the interactive Rich REPL — `solve <task>`, `show results`, `quit`, usage message on unknown input.
- [x] 7.3 Implement live per-iteration rendering — iteration, pass rate, quality, runtime-or-absent; surface the stop reason on completion.
- [x] 7.4 Implement `--demo` — all three tasks in order unattended, results written per task, total elapsed time reported.
- [x] 7.5 Wire `main.py` argument routing: bare invocation opens the REPL, `--demo` runs the automated path, `--model` selects the model; display the active model on start. (Revised: `--model` is **required with no default**. A default let a `qwen2.5-coder` run be banked and written up as `llama3.2`'s.)

## 8. Verify and document

- [x] 8.1 Run `uv run main.py --demo --model <model>` end to end; confirm three metric series, a populated memory log, and JSON + CSV per task. (Done for both models. Results are keyed per model — `<task>_<model>.json`/`.csv` — after an unkeyed run was found overwriting the previous model's curves.)
- [x] 8.2 Inspect the improvement curves — confirm they are legible enough to graph, and record the honest result even if flat or noisy (a null result is publishable). (Recorded: across 6 task-runs / 43 revisions the pass rate never beat iteration 1's, while quality rose up to +10. Quality curves are noisy run-to-run; the pass-rate result held across every run and is the only directional claim made.)
- [x] 8.3 Confirm the graph task's prompt shows evidence of applying sorting's insights. (Verified in `results/debug/<model>/graph/iter01_generate_prompt.md`: sorting's distilled insights are carried in. The prompt asks the model to name the insight it applied; the local models routinely ignore that instruction.)
- [x] 8.4 Rerun with `--model qwen2.5-coder` and compare curves. (Done; both models in the README results table. `--model` is now required precisely so a comparison cannot be misattributed.)
- [x] 8.5 Reconcile `architecture.md` with what was actually built — it is the structural source of truth. (Superseded: `architecture.md` was deleted. It had drifted, was referenced from nowhere, and duplicated this change's own `design.md` plus the module docstrings. The code and `AGENTS.md` are the source of truth.)
- [x] 8.6 Write `README.md` — outcome tagline, run commands, the measured result, and the REPL-has-no-perf-axis caveat. (Rewritten from the real artifacts. The prior headline — "llama3.2's loop made the code worse, best was iteration 1 on 2 of 3" — was unsupported: those numbers were qwen's, and the repl 0% that anchored it was a `_parse_payload` bug.)
- [x] 8.7 Update root `README.md` tracker: Day 5 status `planned` → `done` with the outcome tagline.
