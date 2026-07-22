---
name: audit-plugin
description: Query this project's tool-call audit trails — the per-session JSONL logs the audit-plugin hooks write. Use when the user asks to review, inspect, or summarize a past session's tool calls, find expensive or failed calls, asks "what did the agent do", "show the audit trail", or runs "/audit-plugin". Defaults to the most recent session.
user-invocable: true
argument-hint: "[session index | date/time | grep <pattern>]  (default: latest session)"
---

# audit-plugin — query tool-call audit trails

The audit-plugin hooks write one JSONL file per session. Each line is a tool
call with: `timestamp`, `session_id`, `tool_name`, `tool_use_id`, `inputs`,
`outputs`, `input_bytes`, `output_bytes`, `duration_ms`, `status`.

## Where the data lives

`$CLAUDE_PLUGIN_DATA` is set only inside the hook process, **not** your shell —
so don't rely on it. Find the data dir by checking, in order, the first that
exists:
1. `~/.claude/plugins/data/audit-plugin-audit-plugin/` — marketplace install
   (dir name is `<plugin>-<marketplace>`).
2. `~/.claude/plugins/data/audit-plugin*/` (glob) — in case the marketplace
   name differs.
3. `$CLAUDE_PLUGIN_DATA` / `$PLUGIN_DATA` — only if actually set in your shell.
4. `<this plugin's root>/data/` — local skills-directory dev.

Session logs are `<session_id>.jsonl`; saved reports are `<session_id>.report.md`.

## How to answer

1. **List** the `*.jsonl` files in the data dir (Glob), newest first by mtime.
   If none exist, say so and stop — **do not invent entries**.
2. **Select** the session from the argument:
   - *no argument* → the most recent file.
   - *index* (`1`, `2`, …) → 1 is most recent, 2 the next, and so on.
   - *date/time* (e.g. `2026-07-22`, `14:30`) → the file whose entry timestamps
     match; if ambiguous, list candidates and ask.
   - *`grep <pattern>`* → the file(s) containing the pattern (Grep over `*.jsonl`).
3. **Verify** the chosen file exists (Read it). If the request doesn't resolve to
   a real file, say so — never synthesize a trail.
4. **Render** a table: `# · tool · in_bytes · out_bytes · duration_ms · status`,
   plus totals (calls, bytes, error count). Call out the slowest call and any
   `error` rows. If a `<session_id>.report.md` already exists, prefer
   summarizing that.

## Rules

- Only return data from files that actually exist on disk.
- If nothing matches, report "no matching session" — do not fabricate a trail.
