# Spec: Day-11 Audited Agent Plugin

## Problem Statement

Agentic coding tools like Claude Code make dozens of tool calls per session, but there is no built-in way to audit what each tool call did, what data passed through it, and how long it took. Session transcripts exist, but they are not structured for quick human review, not stable across versions, and do not expose per-tool size/duration metrics. Users who want to debug workflows, review sessions, or analyze tool usage patterns lack a simple, queryable audit trail.

## Solution

Build a Claude Code plugin that hooks into `PreToolUse` and `PostToolUse` events to append a structured JSONL record for every tool call. Each record captures timestamp, session ID, tool name, inputs, outputs, input/output byte sizes, duration, and status. When the session ends, a `Stop` hook reads the JSONL, optionally merges session-level token/cost totals from `ccusage`, and prints a formatted audit report to the terminal while also saving a markdown report to the plugin's data directory. A bundled `/audit-plugin` skill lets the agent query its own audit history by index, date/time, or grep pattern.

## User Stories

1. As a Claude Code user, I want every tool call logged automatically without changing my workflow, so that I can review what happened after a session.
2. As a developer, I want the audit trail stored per session in a JSONL file, so that sessions are isolated and easy to locate.
3. As a user, I want the audit report printed automatically when a session ends, so that I don't need to remember to run a command.
4. As a user, I want the report to show each tool's name, input size, output size, duration, and status, so that I can quickly spot expensive or failed calls.
5. As a user, I want a markdown copy of the report saved to disk, so that I can reference it later or share it.
6. As a power user, I want optional `ccusage` integration, so that session-level token and cost totals appear alongside the per-tool audit.
7. As a user without `ccusage` installed, I want the tool trail to print anyway, so that the plugin degrades gracefully.
8. As a user, I want to ask the agent about its own audit history via `/audit-plugin`, so that I can review past sessions conversationally.
9. As a user, I want `/audit-plugin` to default to the current session, so that the common case is one command.
10. As a user, I want `/audit-plugin` to support lookup by index, date/time, or grep, so that I can find older sessions without knowing UUIDs.
11. As a user, I want `/audit-plugin` to only return data from files that actually exist, so that the agent cannot hallucinate audit entries.
12. As a developer, I want the audit files kept forever by default, so that I can decide when to clean them up.
13. As a plugin author, I want hooks to receive JSON on stdin and use portable environment variables, so that the scripts work reliably.
14. As a reviewer, I want the plugin to be testable without a live IDE session, so that hook scripts and report generation can be verified independently.
15. As a demo viewer, I want to see the plugin load, a real tool-calling session, and the final audit report, so that the value is clear in under a minute.
16. As a user, I want failed tool calls to be logged with an error status, so that the audit trail is complete even when things go wrong.
17. As a user, I want the report generation to fail gracefully, so that a broken `ccusage` call or missing file does not crash the session.
18. As a user, I want the audit data directory to be in the plugin's writable data area, so that it does not clutter project directories.

## Implementation Decisions

- **Plugin structure**: `.claude-plugin/plugin.json` manifest with `hooks/hooks.json` and hook scripts in `scripts/`.
- **Hook events**: `PreToolUse` records start time; `PostToolUse` logs successful tool calls; `Stop` triggers report generation and reconciles any unmatched PreToolUse entries as errors (since hard tool failures fire no PostToolUse in Claude Code).
- **Audit entry schema**: Each JSONL line includes `timestamp`, `session_id`, `tool_name`, `tool_use_id`, `inputs`, `outputs`, `input_bytes`, `output_bytes`, `duration_ms`, and `status`.
- **Data storage**: Per-session JSONL files and markdown reports live in the plugin data directory, resolved from `${CLAUDE_PLUGIN_DATA}` or `PLUGIN_DATA`.
- **Report generation**: A Python script reads the session JSONL, builds a formatted table, optionally fetches token/cost totals from `ccusage session --json`, prints to stdout, and writes a markdown copy.
- **Token/cost layer**: `ccusage` is optional. When available, session-level input, output, cache read/write, and cost totals are added to the report. When unavailable, the report still prints the tool audit trail.
- **Skill**: A bundled `/audit-plugin` skill defaults to the current session and supports index, date/time, and grep lookup modes. It only reads existing files and returns their contents as a formatted table.
- **Data directory resolution**: Hook scripts use `${CLAUDE_PLUGIN_DATA}` for the plugin data directory. The skill resolves this by targeting `~/.claude/plugins/data/audit-plugin*/` directly since `CLAUDE_PLUGIN_DATA` is not available in the agent shell.
- **Retention**: Keep audit files forever; no auto-deletion. Cleanup is left to the user.
- **Graceful degradation**: Report generation and the skill must never crash the session if audit files or `ccusage` are missing or malformed.
- **Language**: Python for hook scripts to match the repo's Python days and minimize dependency weight.

## Testing Decisions

- **What makes a good test**: Verify the external behavior of the plugin — that hook scripts produce the expected JSONL and report when fed known `PostToolUse` input and `Stop` input.
- **Test seams**:
  1. The audit logging script can be tested by piping a sample `PostToolUse` JSON object to it and asserting the JSONL output.
  2. The report generation script can be tested by creating a sample JSONL file and asserting the printed table and markdown report.
  3. The skill instructions can be validated by checking that the skill file loads and references the correct scripts.
- **Prior art**: Day 10's demo verification pattern — the entrypoint run is the primary check — but Day 11 adds script-level tests because the plugin cannot be run without an IDE.
- **Manual verification**:
  1. Load the plugin in Claude Code.
  2. Run a task with multiple tool calls.
  3. Confirm the audit report prints at session end.
  4. Confirm the markdown report file is written.
  5. Run `/audit-plugin` and confirm it returns the most recent session.

## Out of Scope

- Per-tool token attribution (tokens are measured per model turn, not per tool call; estimation is out of scope).
- Real-time live dashboards or continuous monitoring.
- Auto-deletion or rotation of audit files.
- Support for tools other than Claude Code.
- MCP server or agent tools — the plugin uses hooks, not exposed tools.
- Encryption or secure storage of audit files.
- Network-based audit sinks — local files and stdout only.

## Further Notes

- The hook input `transcript_path` is available but intentionally not parsed because the transcript format is not a stable interface. `ccusage` is used for session token/cost data because it already handles that parsing.
- Input and output byte sizes are used as honest per-tool proxies for data volume; they are not tokens but are accurate measurements of what crossed the tool boundary.
- The plugin should be installable as a skills-directory plugin for fast local iteration, and as a marketplace plugin for distribution.
- The `/audit-plugin` skill should be written defensively: list available sessions, validate the chosen one exists, and refuse to synthesize data if no matching file is found.
