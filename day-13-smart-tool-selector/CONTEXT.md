# Day 13 — Smart Tool Selector

Benchmarks three tool-selection strategies for LLM agents with large tool catalogs, measuring whether the right tool gets picked and at what cost.

## Language

**Strategy**:
One of the three tool-selection approaches under comparison: naive baseline, semantic-router pre-filter, or native ToolSearchTool.

**Control lane** (`naive-ts`):
The naive baseline re-run on the native lane's model. Not a strategy — it exists only so the
forced model swap under `ToolSearchTool` (see `docs/adr/0003`) reads as a controlled
difference. Compare `native` against the control lane, `router` against `naive`.
_Avoid_: Fourth strategy (it isn't one; calling it that corrupts the comparison)

**Primary tool**:
The single tool a query's ground truth says a strategy *should* call. Every query has exactly one.
_Avoid_: Expected tool, correct tool (ambiguous with the acceptable set)

**Acceptable set**:
The tools a human wouldn't call wrong for a given query, including the primary tool. Most queries have a one-element acceptable set (just the primary); two queries have a two-element set reflecting genuine ambiguity in realistic phrasing.
_Avoid_: Ground truth (too broad — ground truth also includes the primary/acceptable distinction, not just the set)

**Outcome**:
The graded result for one query run under one strategy: Precise, Acceptable, Incorrect, or Failed. Graded on the *final* tool the agent actually used to answer, not the first tool it tried.
_Avoid_: Result, score, correctness (correctness is one input to outcome, not the whole thing)

**Precise**:
Outcome tier where the final tool equals the query's primary tool.

**Acceptable** (outcome tier):
Outcome tier where the final tool is in the acceptable set but isn't the primary tool.

**Incorrect**:
Outcome tier where a tool was called, but it isn't in the acceptable set.

**Failed**:
Outcome tier where no tool in the acceptable set was ever called within the call cap. Distinct from Incorrect — Failed means the strategy gave up or exhausted its budget without success, not that it confidently landed on the wrong tool.

**Call cap**:
The maximum number of tool calls (5) a strategy gets per query before an unresolved query is graded Failed. Exists so "failing outright" is a reproducible, observable outcome rather than something that only appears on an SDK error.

**Thrashing**:
A strategy calling multiple wrong tools before (or instead of) landing on an acceptable one. Tool-call count is the metric that captures this; it is reported separately from outcome so "wasteful but correct" and "efficient and correct" are distinguishable.
