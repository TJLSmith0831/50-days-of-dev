## Context

This is a new standalone Python package for the 50-days-of-dev project (day-06). The goal is to build a Spec Driven Design (SDD) writer harness that uses smaller local models (Qwen3:14b via Ollama) for research and spec planning, then hands off to Claude Code for implementation via opsx:apply. The harness integrates with existing grill skills (grill-with-docs, grill-me) for interactive requirements gathering.

**Current state**: The repo has day-05 (learning-chat-agent) which demonstrates LangGraph with Ollama, Rich terminal UI, and SQLite persistence. This provides a reference for similar patterns.

**Constraints**:
- Must use Python with Rich for terminal UI (user preference)
- Must support local models via Ollama (Qwen3:14b)
- Must use SQLite for session/memory persistence
- Must integrate with existing openspec CLI and grill skills
- No Write/Edit/Bash tools in v1 (Claude Code handles implementation)
- Scoped to ~1-2 hrs implementation time per 50-days-of-dev pattern

**Stakeholders**: User (single developer building SDD workflow tools)

## Goals / Non-Goals

**Goals:**
- Build a REPL-based coding agent harness with streaming token display and Rich UI
- Implement core agent loop with tool dispatch (Read, Glob, Grep, Web Search, openspec CLI)
- Support SQLite-based session persistence with mid-turn checkpointing and resume
- Integrate grill-with-docs and grill-me skills for requirements gathering
- Provide Claude Code headless API integration for opsx:apply handoff
- Support @file mention expansion and slash commands (/help, /save, /sessions, /exit, /handoff)
- Implement simple token-based context compaction for long sessions

**Non-Goals:**
- Write/Edit/Bash tools in v1 (deferred to future version)
- Permission model in v1 (all tools are read-only)
- Sub-agents in v1 (deferred to future version)
- Intelligent context summarization (deferred to future version)
- Multi-provider support (Ollama only in v1)
- Dynamic tool creation (create_new_tool deferred)

## Decisions

### Architecture: LangGraph-based agent loop

**Decision**: Use LangGraph for the agent execution loop, similar to day-05.

**Rationale**: LangGraph provides a clean state management pattern with built-in checkpointing. The day-05 reference implementation demonstrates successful integration with Ollama, Rich, and SQLite. LangGraph's streaming support enables real-time token display in the REPL.

**Alternatives considered**:
- vibeharness: More complex, designed for production multi-provider use. Overkill for this focused SDD tool.
- Custom loop: Would require reinventing state management, checkpointing, and streaming. LangGraph handles these well.

### Tool system: Registry with JSON schema generation

**Decision**: Implement a tool registry that generates JSON schemas for each tool and handles execution.

**Rationale**: Ollama's tool calling requires JSON schemas. A registry pattern makes it easy to add tools (Read, Glob, Grep, Web Search, openspec CLI) and ensures consistent schema generation. This matches the pattern from vibeharness and LangGraph tool conventions.

**Tool implementations**:
- Read: Read file contents using pathlib
- Glob: File pattern matching using glob
- Grep: Search file contents using re/ripgrep
- Web Search: DuckDuckGo search via ddgs library
- openspec CLI: Subprocess wrapper for openspec commands

### REPL UI: Rich-based with streaming display

**Decision**: Use Rich for terminal UI with streaming token display, thinking spinner, speaker layout, and syntax highlighting.

**Rationale**: Rich is the standard for beautiful Python terminal interfaces (used by vibeharness and day-05). Streaming display provides immediate feedback during LLM generation. Speaker layout (agent vs user) makes conversations readable. Syntax highlighting for code blocks improves spec readability.

**UI components**:
- Streaming token display with Rich's live rendering
- Thinking spinner during LLM processing
- Speaker panels (agent in green, user in blue)
- @file mention expansion (resolve paths before tool calls)
- Slash commands: /help, /save, /sessions, /exit, /handoff
- Rich panels for tool outputs (syntax highlighted code, search results)

### Session persistence: SQLite with LangGraph checkpointer

**Decision**: Use SQLite database with LangGraph's SqliteSaver for session persistence.

**Rationale**: SQLite provides ACID guarantees and querying capabilities for session management. LangGraph's SqliteSaver handles checkpointing automatically, enabling mid-turn resume. Database location: `~/.coding-agent-harness/sessions.db`.

**Schema**:
- LangGraph checkpoints table (managed by SqliteSaver)
- Sessions table: session_id, created_at, updated_at, thread_id, metadata
- Messages table: message_id, session_id, role, content, timestamp

### Context management: Token counting and truncation

**Decision**: Implement simple token-based truncation for v1. Count tokens using tiktoken or character-based fallback, truncate oldest messages when context exceeds limit.

**Rationale**: Local models (Qwen3:14b) have smaller context windows. Simple truncation is straightforward to implement and sufficient for initial use. Intelligent summarization is deferred (D10).

**Configuration**:
- Max context tokens: 4000 (configurable)
- Truncation strategy: Remove oldest messages, keeping system prompt and last N messages
- Preserve: System prompt, last 10 messages, tool call results

### Grilling integration: Skill invocation via openspec CLI

**Decision**: Integrate grill-with-docs and grill-me skills by calling the skill tool via openspec CLI or direct skill invocation.

**Rationale**: User has these skills installed. The harness can invoke them as tools, passing the current context. This enables interactive requirements gathering within the REPL.

**Implementation**:
- Grill skill as a tool that accepts conversation context and returns questions
- User responses flow back to the skill
- Skill outputs become part of the agent's context for spec generation

### Claude Code handoff: Headless API integration

**Decision**: When user confirms spec is ready (/handoff), call Claude Code headless API to run opsx:apply.

**Rationale**: User wants to use smaller models for planning/research, then leverage Claude Code for implementation. The headless API allows programmatic execution of opsx:apply with the generated spec.

**Implementation**:
- /handoff command triggers handoff flow
- Confirm with user before proceeding
- Call Claude Code headless API with spec location
- Display Claude Code output in REPL
- Return to REPL after completion (or error)

### Model configuration: Dual-model approach

**Decision**: Qwen3:14b (via Ollama) for research/planning, Claude API for Claude Code headless integration.

**Rationale**: Cost-effective approach. Qwen3:14b is capable for spec planning and research at low cost. Claude API is used only for implementation via Claude Code, where its superior coding ability justifies the cost.

**Configuration**:
- Default model: qwen3:14b (Ollama)
- Fallback: llama3.2 if qwen3:14b unavailable
- Claude model: claude-sonnet-4-20250514 (via Claude Code headless, not direct API)

### Project structure: Monorepo day-06 folder

**Decision**: Create day-06-coding-agent-repl-harness/ following the 50-days-of-dev pattern.

**Rationale**: Consistent with existing structure. Each day is self-contained with its own pyproject.toml and dependencies.

**Structure**:
```
day-06-coding-agent-repl-harness/
  AGENTS.md
  README.md
  main.py
  pyproject.toml
  src/
    agent_loop.py
    tool_system.py
    repl_interface.py
    session_management.py
    context_management.py
    grilling_integration.py
    claude_code_handoff.py
  .env.example
```

## Risks / Trade-offs

**Risk: Ollama model availability** → Mitigation: Preflight check on startup, clear error message if Ollama not running or model not pulled. Fallback to llama3.2 if qwen3:14b unavailable.

**Risk: Context window overflow with long sessions** → Mitigation: Simple truncation strategy preserves recent context. User can /save and /exit to start fresh session. Intelligent summarization deferred to v2.

**Risk: Grill skill integration complexity** → Mitigation: Start with simple tool invocation. If direct skill invocation is complex, fall back to subprocess calls to the skill CLI.

**Risk: Claude Code headless API availability** → Mitigation: Check for Claude Code installation and API key before /handoff. Provide clear error if unavailable. Allow manual opsx:apply as fallback.

**Risk: SQLite database corruption** → Mitigation: Use SQLite's WAL mode for better concurrency. Implement backup/restore via /sessions command. Database is not critical (can be recreated).

**Trade-off: No Write/Edit tools limits agent autonomy** → Acceptable: This is intentional per the SDD workflow. The agent focuses on research and spec generation; Claude Code handles implementation.

**Trade-off: Simple truncation loses older context** → Acceptable for v1: User can manage session length via /save and /exit. Intelligent summarization deferred to v2.

## Migration Plan

No migration needed — this is a new standalone package.

**Deployment steps**:
1. Create day-06 folder structure
2. Add pyproject.toml with dependencies (Rich, ollama-python, anthropic, ddgs, langgraph, langchain-ollama, tiktoken)
3. Implement core modules following task breakdown
4. Test with Ollama running and qwen3:14b pulled
5. Verify grill skill integration
6. Test Claude Code handoff (if available)

**Rollback strategy**: Delete day-06 folder. No impact on existing codebase.

## Open Questions

None — all key decisions are captured in the decision log (D1-D16 with D7/D8 amended).
