# Day 11 — Audited Agent — AGENTS.md
A Claude Code plugin that logs every tool call to a per-session JSONL audit trail and prints a report at session end.

## Stack
Python (stdlib only) · Claude Code plugin (hooks + skill)

## Commands (verified 2026-07-22)
- `uv run demo.py` — offline self-check: drives the real hook scripts with sample events, asserts the JSONL + report, prints the trail
- `uv run --with pytest pytest tests/ -q` — unit tests for `build_entry` / `render_report`

## Concept
Observability at the tool boundary via hooks, not agent changes. `PreToolUse`
stamps a start time; `PostToolUse` appends one audit record per call (timestamp,
tool, inputs/outputs, byte sizes, duration, status); `Stop` renders the report.
A `/audit-plugin` skill queries past sessions.

## Gotchas
- Do **not** add `"hooks": "./hooks/hooks.json"` to `plugin.json` — Claude Code
  auto-loads `hooks/hooks.json`, and re-declaring it hard-fails the plugin with
  "Duplicate hooks file detected".
- Claude Code has **no** `PostToolUseFailure` event. Worse, a *hard* tool failure
  (e.g. Bash exit≠0 that the tool treats as an error) fires **no** `PostToolUse`
  at all. So: `status:"error"` from `tool_response` covers tools that report an
  error in their result; the `Stop` hook reconciles any `PreToolUse` with no
  matching `PostToolUse` (leftover in `pending.json`) into the trail as an error.
- Duration needs the `PreToolUse` companion: Pre/Post are separate processes, so
  timing is wall-clock (`time.time()`), not `perf_counter`.
- Installed-plugin data lands in `$CLAUDE_PLUGIN_DATA`, which the harness sets to
  `~/.claude/plugins/data/<plugin>-<marketplace>/` (e.g.
  `audit-plugin-audit-plugin/`) — **not** `<plugin root>/data/`. That env var is
  visible only inside the hook process, so the `/audit-plugin` skill looks up the
  `~/.claude/plugins/data/audit-plugin*/` path directly. Resolution order:
  `CLAUDE_PLUGIN_DATA` → `PLUGIN_DATA` → `<plugin root>/data/`; set `PLUGIN_DATA`
  to redirect it in tests.
- `ccusage` is optional; if absent the report prints the tool trail without
  token/cost totals.
- Claude Code only — no Codex manifest (scoped out by decision).
