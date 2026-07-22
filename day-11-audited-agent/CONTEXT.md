# Audited Agent — Context

## Goal

Build an agent that logs every tool call to an audit trail, then prints the complete trail after execution. The trail must include: timestamp, tool name, inputs, outputs, duration, and status.

## Stack

- Python
- Anthropic Agent SDK (or similar)
- local Ollama model

## Measurable outcome

A complete, timestamped audit trail of all tool invocations from a single agent run, printed after the agent finishes.

## Key design decisions

### Agent framework

- Use Anthropic Agent SDK (consistent with Day 3) or LangChain (consistent with Days 1-2)
- Local Ollama model (consistent with Days 1-2, 4-5, 10)
- Keep it simple — no complex graphs, just a single agent with tools

### Tools to instrument

Need 3-4 tools to prove the multi-step concept:

- `list_files` — list files in a directory
- `read_file` — read file contents
- `write_file` — write content to a file
- `search_files` — search for a pattern in files

### Audit trail structure

Each entry should include:

- `timestamp` — ISO 8601 timestamp when the tool was called
- `tool_name` — name of the tool invoked
- `inputs` — the arguments passed to the tool
- `outputs` — the result returned by the tool
- `duration_ms` — execution time in milliseconds
- `status` — "success" or "error"

### Output format

- Print as a formatted table for human readability
- Also save as JSON for machine readability
- Print after the agent finishes, not interleaved with execution

### Implementation approach

Option A: Decorator pattern

- Wrap each tool function with an `@audit` decorator
- Decorator logs before/after the tool call
- Clean separation of concerns

Option B: Tool wrapper class

- Create an `AuditedTool` class that wraps the actual tool
- Centralized logging logic
- More explicit but more boilerplate

Option C: Agent middleware

- Intercept tool calls at the agent level
- More invasive but catches all calls automatically
- May be framework-specific

**Decision:** Start with Option A (decorator pattern) — clean, explicit, framework-agnostic.

## Demo scenario

The agent will:

1. List files in a test directory
2. Read a specific file
3. Search for a pattern across files
4. Write a summary to a new file

After completion, print the audit trail showing all 4 calls with full details.

## Gotchas

- Timing precision: use `time.perf_counter()` for accurate duration measurement
- Output size: if a tool returns large output, truncate in the audit trail for readability
- Error handling: ensure failed tool calls are still logged with error status
- Thread safety: not a concern for single-threaded agent, but worth noting
- JSON serialization: ensure all inputs/outputs are JSON-serializable for the saved trail

## Success criteria

1. Agent completes the multi-step task successfully
2. Audit trail prints after execution with all required fields
3. Trail includes at least 3 tool calls
4. Trail is both human-readable (table) and machine-readable (JSON file)
5. Duration measurements are accurate and reasonable
6. Failed tool calls (if any) are logged with error status
