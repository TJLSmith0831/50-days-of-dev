# Audited Agent — Demo Brief

**Hook:** An agent runs a multi-tool task, and afterward you get a complete audit trail showing every tool call — what was called, when, with what inputs, and what it returned.

---

## What it proves

1. **Complete observability** — every tool invocation is captured with timestamp, tool name, inputs, outputs, and duration
2. **Post-run visibility** — the audit trail is printed after the agent finishes, not scattered in real-time logs
3. **Structured output** — the trail is machine-readable (JSON) and human-readable (formatted table)

---

## Why this matters (the employer story)

This isn't "I know how to log." It's "I design agent infrastructure that makes every action auditable and debuggable."

- **Tool-level instrumentation** — every tool call is wrapped with logging that captures the full call context
- **Post-mortem visibility** — the audit trail is available after execution, not lost in streaming output
- **Structured telemetry** — the trail is JSON-serializable for downstream analysis (cost tracking, pattern detection, compliance)
- **Zero agent changes** — the agent doesn't need to be taught about auditing. The tool layer handles it.

---

## Setup

```bash
cd day-11-audited-agent
uv run demo.py
```

---

## Pre-recording workflow

**Step 1 — Test inputs without recording.**

1. Run `uv run demo.py` manually.
2. Confirm the harness drives the hook scripts with sample events and produces a correct audit trail.
3. Verify the audit trail prints with all fields (timestamp, tool, inputs, outputs, duration, status).
4. If any field is missing or the trail doesn't print — **stop and do not record**. Diagnose the failure first.

**Step 2 — Record the terminal demo.**

Once Step 1 passes cleanly on a dry run, start recording.

**Step 3 — Create the Remotion video.**

Composite the audit logging concept animated intro with the terminal recording.

---

## Demo scenario

Install the plugin in Claude Code:

1. Copy `.claude-plugin/` to `~/.claude/plugins/audit-plugin/`
2. Restart Claude Code
3. Run a multi-tool task (e.g., search files, read content, write output)
4. After session end, the audit trail prints automatically showing the complete call history
5. Run `/audit-plugin` to query the trail conversationally

---

## Shot list (~40–50s)

### Remotion intro (10–15s)

1. **Audit logging concept (10–15s):** animated diagram showing Agent → Tool Layer → Audit Trail. Each tool call is intercepted: timestamp recorded, inputs captured, output logged, duration measured. Caption: *complete observability at the tool layer.*

### Terminal demo (30–35s)

1. **Agent runs (15s):** agent executing a multi-step task with visible tool calls in real-time. Caption: *the agent does its work.*
2. **Audit trail printed (15s):** structured table/json showing the complete call history — timestamp, tool name, inputs, outputs, duration, status. Caption: *after the run, the full story.*
3. **Key fields highlighted (5s):** zoom on timestamp, tool name, inputs/outputs to show the depth of logging. Caption: *every call, captured.*

---

## What NOT to demo

- Real-time logging during execution (distracts from the "after a run" requirement)
- A single-tool task (doesn't prove the trail concept)
- Filtered/redacted logs (show the full trail)
- The test suite (unit tests aren't the story here)

---

## Frame

- Terminal fullscreen, dark theme.
- The audit trail table is the visual — let it render fully before cutting.
- Highlight the structured fields (timestamp, duration, status) to show the depth.
- End on the complete audit trail held for 1–2s.

---

## LinkedIn post draft

> An agent runs a multi-tool task, and afterward you get a complete audit trail showing every tool call — what was called, when, with what inputs, and what it returned.
>
> Built an audited agent that wraps every tool invocation with logging: timestamp, tool name, inputs, outputs, duration, and status. The trail prints after execution, not scattered in real-time logs.
>
> Complete observability at the tool layer. The agent doesn't change behavior. The infrastructure makes every action auditable.
>
> Day 11 of 50 — audit logging. #AIEngineering #AgentObservability #AuditTrail

---

## Checks before recording

1. `uv run demo.py` — harness drives hooks, audit trail prints with all fields
2. Audit trail includes: timestamp, tool name, inputs, outputs, duration, status
3. At least 3 tool calls in the trail (proves the multi-step concept)
4. Plugin loads in Claude Code without errors
5. Real session produces trail at `~/.claude/plugins/data/audit-plugin-audit-plugin/`
