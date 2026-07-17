# CLI

## ADDED Requirements

### Requirement: Verbose diagnostics flag

The CLI SHALL accept a `--verbose` flag (default off) that prints diagnostic
information to stderr without altering normal stdout output.

#### Scenario: Verbose session start

- **WHEN** the REPL is started with `--verbose`
- **THEN** the model name, thread id, and sessions DB path are printed to stderr

#### Scenario: Verbose turn timing

- **WHEN** `--verbose` is set and an agent response completes
- **THEN** the elapsed time for that turn is printed to stderr
