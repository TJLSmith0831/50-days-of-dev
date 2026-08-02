# 1. Hybrid Session Capture Architecture

- Status: Accepted
- Date: 2026-08-02

## Context
The initial Notch HUD relied on static HTTP pushes and superficial process matching (`sysinfo`), leaving it unable to track real active agent sessions or support multi-session management and interactive permission prompts.

## Decision
We adopt a **Hybrid Session Capture** approach:
1. **Passive Auto-Discovery**: Background file system watching (JSONL transcripts, `~/.claude/`, workspace session stores) to detect active sessions zero-config.
2. **Active Hook Integration**: A local socket / IPC interface for agent runtimes and tools (e.g. Claude Code hooks, MCP wrappers) to push rich state, token telemetry, and blocking permission requests.

## Consequences
- Zero setup needed for standard session observation.
- Deep integration available when agents support approval hooks.
- Dual ingestion pipeline required in the Rust backend (file tailer + IPC/HTTP listener).
