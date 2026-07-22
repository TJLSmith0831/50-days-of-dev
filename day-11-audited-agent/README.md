# Day 11 — Audited Agent

A Claude Code **plugin** that logs every tool call to a per-session JSONL audit
trail and prints a report when the session ends. Observability at the tool
boundary — the agent doesn't change behavior; the hook layer captures everything.

## What it does

- **`PreToolUse`** stamps a wall-clock start time per `tool_use_id`.
- **`PostToolUse`** appends one audit record per call: `timestamp`, `session_id`,
  `tool_name`, `tool_use_id`, `inputs`, `outputs`, `input_bytes`, `output_bytes`,
  `duration_ms`, `status`.
- **`Stop`** reads the session's JSONL, prints a formatted table, and writes a
  markdown copy. If [`ccusage`](https://github.com/ryoppippi/ccusage) is
  installed, session token/cost totals are appended; if not, the trail prints
  anyway.
- **`/audit-plugin`** skill queries past sessions (latest by default; also by
  index, date/time, or grep) and only reads files that exist.

## Layout

```
.claude-plugin/plugin.json      plugin manifest
.claude-plugin/marketplace.json local marketplace entry (for `claude plugin` install)
hooks/hooks.json                PreToolUse + PostToolUse + Stop
scripts/log_tool_use.py         Pre/Post handler (append audit record)
scripts/report.py               Stop handler (render + save report)
scripts/audit_common.py         shared path/size helpers
skills/audit-plugin/SKILL.md    /audit-plugin query skill
demo.py                         offline self-check (no IDE needed)
tests/test_audit.py             unit tests
data/                           runtime JSONL + reports (gitignored)
```

## Try it (no IDE)

```bash
cd day-11-audited-agent
uv run demo.py                          # sample events -> asserts + prints the trail
uv run --with pytest pytest tests/ -q   # unit tests
```

## Install as a plugin (Claude Code)

```bash
claude plugin marketplace add ./day-11-audited-agent
claude plugin install audit-plugin@audit-plugin
```

Then run any multi-tool task; the audit trail lands in `data/<session_id>.jsonl`
and the report prints at session end. Query it later with `/audit-plugin`.

## Data location

The hooks resolve the data dir as `$CLAUDE_PLUGIN_DATA` → `$PLUGIN_DATA` →
`<plugin root>/data/`. For a marketplace install, Claude Code sets
`$CLAUDE_PLUGIN_DATA` to `~/.claude/plugins/data/audit-plugin-audit-plugin/`, so
that's where the logs actually land (that env var is visible only inside the hook
process, which is why the `/audit-plugin` skill looks that path up directly).

## Scope

Claude Code only. Claude Code has no `PostToolUseFailure` event; a hard tool
failure fires no `PostToolUse` either, so failed calls are reconciled at `Stop`
from the `PreToolUse` start records and tagged `status: error`. Codex support and
per-tool token attribution are out of scope (see
`specs/day-11-audited-agent.md`).
