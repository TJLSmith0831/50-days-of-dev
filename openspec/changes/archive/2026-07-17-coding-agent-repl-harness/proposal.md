## Why

Build a Spec Driven Design (SDD) writer harness with grilling ability and Claude Code handoff via headless Claude. The user wants a focused tool that uses smaller models (Ollama) for research and spec planning, then hands off to Claude Code for implementation via opsx:apply. This approach is cost-effective and leverages the right model for each phase.

## What Changes

- Build Python-based coding agent harness using vibeharness as reference implementation
- Implement dual-model architecture: Qwen3:14b (via Ollama) for research/planning, Claude API for Claude Code headless integration
- Create Rich-based terminal UI for REPL with streaming token display, thinking spinner, speaker layout (agent vs user), @file mention expansion, and slash commands (/help, /save, /sessions, /exit, /handoff)
- Implement SQLite database for session and memory persistence
- Build tool system with Read, Glob, Grep, Web Search (ddgs), and openspec CLI integration
- Integrate existing grill-with-docs and grill-me skills for interactive requirements gathering
- Implement Claude Code headless API integration for opsx:apply handoff when user confirms spec is ready
- Implement simple token-based context compaction (intelligent summarization deferred)
- Exclude Write, Edit, Bash, create_new_tool, permissions, sub-agents from initial version (not needed for SDD workflow)

## Capabilities

### New Capabilities

- `agent-loop`: Core turn-based agent execution loop handling LLM invocation, tool dispatch, and result processing
- `tool-system`: Tool registry with JSON schema generation and execution (Read, Glob, Grep, Web Search, openspec CLI)
- `repl-interface`: Rich-based terminal REPL with streaming display, slash commands, and @file mention expansion
- `session-management`: SQLite-based session persistence with mid-turn checkpointing and resume capability
- `context-management`: Token counting and simple truncation-based compaction for long sessions
- `grilling-integration`: Integration with grill-with-docs and grill-me skills for requirements gathering
- `claude-code-handoff`: Claude Code headless API integration for opsx:apply execution

### Modified Capabilities

None - this is a new standalone harness.

## Impact

- New Python package with dependencies: Rich, ollama-python, anthropic (for Claude Code headless), ddgs, sqlite3 (stdlib)
- No changes to existing codebase - standalone tool
- Requires Ollama installation for local model support
- Requires Claude API key for Claude Code headless integration
- SQLite database created in user's home directory for session storage
- Integrates with existing openspec CLI and grill skills in the repository
