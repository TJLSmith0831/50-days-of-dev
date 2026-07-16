## Context

Day 5 builds a self-improving coding agent: it writes code, grades its own work against real measurements, critiques the result, and revises — looping until improvement flattens. The deliverable is an interactive Rich REPL; three built-in coding tasks (sorting, graph shortest-path, Ollama REPL builder) exist to make the improvement curve concrete and graphable for the day's demo video.

Constraints inherited from the repo and from the design interview:

- **Local-first**: LangGraph over Ollama (`llama3.2` or similar code-capable local model). No hosted API.
- **Metrics must not be self-reported.** An LLM grading its own output is the failure mode this day is supposed to avoid. All three axes come from established tooling: `radon`, `pylint`, `timeit`.
- **No overfitting to the test suite.** The agent must improve at *the task*, not at *the grader*.
- **Modular, thoroughly docstring'd**, with `architecture.md` as the structural source of truth.
- ~1–2 hour scope. This is a learning build, not production software.

Current state: `day-05-self-refining-agent/` is scaffolded with `pyproject.toml`, `AGENTS.md`, `architecture.md`, `.gitignore`, and a stub `main.py`.

## Goals / Non-Goals

**Goals:**

- Prove, numerically, that a reflect-retry loop improves generated code across three independent axes.
- Show learning *compounding across tasks* — insights from sorting measurably help on graph.
- Ship an interactive Rich REPL as the primary interface, with `--demo` as the automated path for the video.
- Emit per-iteration JSON + CSV so the improvement curve can be graphed externally.
- Keep every metric defensible: real static analysis, real timing, deterministic tests.

**Non-Goals:**

- Not building a general-purpose coding agent — three fixed built-in tasks only.
- Not a bare-metal agent loop; LangGraph owns the state machine (explicitly ruled out during the interview).
- No vector store / embedding memory. The memory log is human-readable Markdown by design.
- No hosted models, no cloud, no deployment.
- Not a hardened sandbox. Subprocess + timeout is the boundary; this is a local dev-machine tool, not a multi-tenant code runner.
- Not attempting to make the agent *win* — a flat or negative curve is a legitimate, publishable result.

## Decisions

### LangGraph for the loop, not chains or a hand-rolled loop

The loop has real branching (plateau? cap hit? tests passing?) and per-iteration state that must be inspectable after the fact. LangGraph models this as explicit nodes + conditional edges, and its checkpointing gives resumability for free.

*Alternatives:* LangChain chains (no natural conditional cycle); bare `while` loop (explicitly rejected in the interview — Day 5 is not a bare-metal-agent day).

### Metrics come from tooling, never from the model

| Axis | Source | Direction |
|---|---|---|
| Pass rate | Task test suite, run in subprocess | higher better, 0.0–1.0 |
| Quality score | `radon` (MI, cyclomatic) + `pylint` (style) | higher better, 0–100 |
| Runtime | `timeit.repeat()`, minimum of 5 runs | lower better, ms |

Composite quality = **40% maintainability index + 30% style + 30% complexity**. Maintainability is weighted highest because it already folds in Halstead volume and LOC; style and complexity are the axes a critique can act on most directly.

`timeit` reports the **minimum** of repeated runs, not the mean — the minimum is the machine's floor for that code, while higher samples are contamination from unrelated system load. Garbage collection is disabled during timing (`timeit` default).

*Alternative rejected:* LLM-as-judge scoring. It is the thing this day is meant to critique, it drifts, and it cannot be graphed honestly.

### Anti-overfitting: the agent never sees the grader

The interview raised "avoid bias towards solving specific questions" as a hard requirement. The failure mode is real and well-known: given test source, an LLM will special-case the assertions rather than solve the task.

Mitigations, in order of importance:

1. **The agent never receives test source code.** It receives the task prompt (a behavioral spec) only.
2. **Critique reports failing test *names* and assertion messages** — enough to act on, not enough to hardcode against.
3. **A held-out test set is never surfaced in critique at all** and contributes to the scored pass rate. If the agent is special-casing the visible failures, the held-out set exposes it as a gap between reported-fixable and actual pass rate.

This is what makes the pass-rate curve mean "got better at sorting" rather than "got better at these ten assertions."

### Plateau detection with a hard cap

Stop when improvement in composite quality is `< 2%` for **2 consecutive iterations**. Chosen over a fixed iteration count so the agent stops when it has actually converged.

Plateau alone is unbounded on a local model, so a **hard cap of 10 iterations per task** guarantees a demo run terminates. Hitting the cap is recorded distinctly from converging — they are different results and the output must not conflate them.

Best code is retained across iterations: revision can regress, and the loop should not lose a good version to a bad one.

Retention ranks **correctness first, quality as a tiebreak only** — `(pass_rate, quality_score)` as a sort key. Ranking on composite quality alone was the original intent and it proved wrong in the first real run: the graph task retained an 11%-passing version over a 33%-passing one to gain 0.04 quality points. That is the "quality gain bought with a pass-rate loss" risk below, reappearing in the *selection* rule after being designed out of the *reporting*. A sort key orders the axes without collapsing them, so both remain separately reported.

### The memory log is namespaced per model

Cross-session memory and a swappable model interact badly: run `llama3.2 --demo`, then `qwen2.5-coder --demo`, and the second run inherits the first's insights. The comparison is then contaminated — qwen starts with a head start llama never had, and neither curve means what it appears to mean.

The log is therefore keyed by model: `results/memory_log_<model>.md`. Each model accumulates its own learning across sessions, and comparing two models compares like with like. This costs one interpolation and needs no flag to remember at demo time — the failure mode it prevents is silent, which is exactly the kind worth designing out rather than documenting around.

### Memory log: Markdown, distilled on completion, read on task start

On task completion the agent distills **3–5 transferable insights** to `results/memory_log_<model>.md`; the next task reads the log before generating and must reference which insights it is applying.

Written **on task completion, not per iteration** — per-iteration logging produces noise, and an insight is only credible once the task's whole curve is visible. Only insights general enough to transfer are kept ("modular helpers score higher on maintainability"), not task-specific tricks ("use 3 as the pivot").

Markdown over a vector store: it is inspectable, it is demoable on camera, it survives across sessions with no infrastructure, and at this scale retrieval is unnecessary — the whole log fits in context.

*Trade-off:* the log grows unbounded across sessions. At 3 tasks × ~5 insights this is a non-issue; if it ever matters, cap or summarize.

### Sequential tasks, all-signals critique

Tasks run one at a time to plateau, in fixed order (sorting → graph → REPL), so each produces a clean independent curve and so memory flows forward in a defined direction.

Critique concatenates **all three signals at once** (test failures + quality feedback + timing) and lets the agent prioritize, rather than staging correctness-then-quality-then-speed. Real critique is multi-dimensional, and watching the agent negotiate the trade-off is itself the interesting output.

### REPL task: pass rate + quality only, no runtime axis

The REPL-builder task's wall-clock is dominated by Ollama inference — noise the agent's code cannot control — so timing it would produce a random walk, not an improvement curve. **Per the design interview, the REPL task drops the runtime axis** and is scored on pass rate + quality only. The demo graph will show a gap in the third task's perf series; this is deliberate and honest, and the gap is worth explaining on camera rather than papering over.

Its tests still must not hit a live model — a flaky or slow test suite corrupts the very pass-rate curve being graphed. Tests stub the **network boundary** (the `ollama` module / HTTP call), not an injected interface, so the agent remains free to structure its code however it likes without the harness dictating a solution shape.

### Default to `llama3.2`, keep the model swappable

`llama3.2` is the default — it matches Day 4, it is already pulled, and holding the model constant across days makes the *loop* the variable under test rather than the model.

A code-tuned model (`qwen2.5-coder`) is likely to produce a more legible improvement curve, which matters for the demo, so the model is a `--model` flag rather than a constant. Swapping is a flag, not an edit: `uv run main.py --demo --model qwen2.5-coder`.

Deliberately *not* building an A/B harness — running the demo twice with different flags answers the same question with no code. If `llama3.2` yields a flat curve, that is itself worth reporting alongside a `qwen2.5-coder` run.

### Generated code runs in a subprocess with a timeout

Scoring means executing what the model wrote. Generated code is written to a temp file and run via `subprocess` with a wall-clock timeout — never `exec`'d in the host process, where an infinite loop or a stray `sys.exit` would take the REPL down with it.

This is a containment boundary against *the agent's mistakes* (infinite loops, runaway memory, accidental file writes), not a security sandbox against an adversary. That distinction is stated plainly rather than implied; a local-first learning tool running a local model does not warrant container isolation, and pretending subprocess isolation is a security boundary would be worse than naming its limits.

## Risks / Trade-offs

- **The local model may not improve at all.** llama3.2 is small; the curve could be flat or noisy. → The build measures honestly and reports what happened. A flat curve is a real finding and a more interesting post than a fabricated win. Iteration cap keeps a null result cheap.
- **Plateau may trigger on iteration 2** before any real work happens, if the first revision happens to move < 2%. → Enforce a minimum of 3 iterations before plateau detection is armed.
- **Quality score can be gamed** — an agent can delete code to cut complexity and LOC, raising the score while failing tests. → Pass rate is scored independently and reported separately; a quality gain alongside a pass-rate drop is visible in the output, not hidden inside a single blended number. This is precisely why the three axes are never collapsed into one score.
- **`pylint` is slow** (seconds per run) and this runs every iteration across ~30 iterations. → Acceptable at this scale; if it dominates, `flake8` is a faster substitute for the style component.
- **Small local models produce unparseable code** (markdown fences, prose, truncation). → Strip fences and validate with `ast.parse()` before scoring; a syntactically invalid generation scores 0 and feeds the parse error back as critique rather than crashing the loop.
- **Unbounded wall-clock on `--demo`** — 3 tasks × up to 10 iterations × local inference could run long. → Hard cap per task; report elapsed time so the video can be planned around it.
- **The memory log could degrade into flattery** ("I did great") rather than transferable insight. → Distillation is prompted against the *measured deltas*, not the agent's impression, and the log is inspectable on camera.

## Open Questions

Both resolved during implementation:

- **Should `results/memory_log_<model>.md` be committed?** Yes. It is the artifact that proves cross-session learning and holds no sensitive content. `.gitignore` uses `results/*` plus `!results/memory_log_*.md` — the `results/` form would have made the negation impossible, since git cannot re-include a file under an excluded directory.
- **Does the graph task need a fixed random seed for its generated test graphs?** Yes, seeded (`PERF_SEED = 1337`, asserted in `tasks._self_check`). Both timed tasks build their input under that seed, so the runtime axis measures the agent's code rather than input variance.

Raised and resolved *after* the first measured run:

- **Should best-version retention rank on quality alone?** No — correctness first, quality as tiebreak. See the plateau/retention decision above.
- **Are the performance baselines right?** No; recalibrated from 100ms/200ms to 10ms/5ms against a measured reference implementation. A baseline no real solution can miss makes the timing signal inert.
