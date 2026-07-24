# Tiered outcome (Precise/Acceptable/Incorrect/Failed) graded on final tool, with a 5-call cap

A binary correct/incorrect on the *first* tool call would double-count thrashing (already captured by tool-call count) and couldn't distinguish "picked a defensible tool" from "picked a wrong one" or from "never landed anywhere." We instead grade outcome on the *final* tool the agent used, as one of four tiers, and cap each query at 5 tool calls — after which no acceptable tool means Failed, distinct from Incorrect. Without the cap, a strategy that eventually stumbles onto the right tool after many wrong guesses would only look "inefficient," never "failing outright," undercutting the benchmark's own premise that too many tools can cause outright failure.

## Consequences

Tool-call count and outcome are now orthogonal metrics — a strategy can be "correct but wasteful" (many calls, Precise) distinctly from "efficient and correct" (few calls, Precise), and neither conflates with genuine failure. The cap of 5 is somewhat arbitrary (not tied to the 8-tool catalog size) and may need retuning if it turns out to be too tight or too loose once the harness is actually run.
