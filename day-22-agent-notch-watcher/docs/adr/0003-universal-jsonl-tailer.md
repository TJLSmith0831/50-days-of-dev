# 3. Universal JSONL Tailer over Bespoke Adapters

- Status: Accepted
- Date: 2026-08-02

## Context
Writing separate Rust adapter structs for every agent tool (Claude Code, Cursor, Antigravity, Goose, Aider, Ollama) introduces hundreds of lines of fragile, schema-specific parsing code.

## Decision
Adopt a single `UniversalJsonlTailer` in Rust:
1. Tail any active file matching `*.jsonl`, `*.log`, or `transcript*.json` under standard agent session paths.
2. Generically extract fields (`status`, `tokens`, `model`, `tool`, `message`, `permission`) without schema-specific parser classes.
3. Expose standard HTTP IPC endpoints (`/event` and `/permission/request`) for CLI hooks.

## Consequences
- Minimum code diff (~60 lines of Rust total).
- Zero per-agent parser boilerplate.
- Instantly compatible with future AI agents that write JSON logs or hit HTTP endpoints.
