# Add --verbose flag to the SDD Writer Harness CLI

## Why

Debugging REPL sessions currently requires editing source to add prints. A
`--verbose` flag gives visibility into session/agent internals without code
changes.

## What Changes

- `main.py` gains a `--verbose` argparse flag (default off).
- When set, the harness prints debug information to **stderr**: model name,
  thread id, session DB path, and per-turn timing.
- Normal stdout output (Rich panels, streamed tokens) is unchanged.

## Impact

- Affected: `main.py` only. No new dependencies.
