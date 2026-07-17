# Coding Agent REPL Harness Research

## Research Sources

- [vibeharness](https://github.com/jeanlag1/vibeharness) - ~2.4k lines Python, hackable, educational
- [Ori CLI](https://github.com/aayoawoyemi/ori-cli) - Advanced memory/graph, React terminal UI
- [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) - Production-ready, batteries included
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) - Multi-agent orchestration focus

## Core Agent Loop Pattern

All harnesses implement a turn-based loop:

1. **Receive prompt** - User input + system prompt + tool definitions + conversation history
2. **Evaluate and respond** - Model produces text and/or tool calls
3. **Execute tools** - Run requested tools, collect results
4. **Repeat** - Feed results back to model until no tool calls
5. **Return result** - Final response with usage/cost metadata

A turn is one round trip: model output → tool execution → results fed back. Sessions chain multiple turns until completion.

## Essential Components

### Core Loop (`agent.py`)
- Main while loop driving LLM ↔ tools cycle
- Tool dispatch and result handling
- Stop reason handling (max_tokens, tool_use, end_turn)
- Auto-resume on max_tokens

### Provider Abstraction (`llm.py`)
- Multi-provider support (Anthropic, OpenAI, etc.)
- Streaming responses (token-by-token)
- Prompt caching (cache_control breakpoints → ~90% discount)
- Rate-limit-aware retry with exponential backoff and jitter
- Per-model pricing table for cost metering

### Tool System (`tools/`)
- Tool registry with JSON schema generation
- File operations: Read, Write, Edit (strict matching)
- Search: Glob, Grep
- Execution: Bash (persistent PTY sessions)
- Planning: set_plan, update_plan, get_plan
- Sub-agents: task tool for isolated subtasks

**Tool execution details**:
- Edit uses Claude-Code-style strict matching (unique substring, fails loudly if ambiguous)
- Bash uses pexpect for real PTY (cd, export, shell functions persist across calls)
- Output is ANSI-stripped, run-length-collapsed, head/tail truncated

### Permissions (`permissions.py`)
- Auto/ask/deny modes
- Per-tool allow/deny lists
- Approval memory for repeated operations
- Permission policy: auto-approved tools bypass prompts, disallowed tools blocked regardless

### Context Management (`context.py`)
- Token counting per turn
- Auto-compaction at thresholds
- Message history pruning
- Efficient context handling for long sessions

### Session Layer (`session.py`)
- JSON serialization after every tool call (mid-turn checkpointing)
- Ctrl-C safe (never loses progress)
- Resume with full transcript re-rendering
- Session persistence across restarts

### REPL UI (`ui.py`, `repl_input.py`)
- Streaming token display
- Rich panels for diffs, bash output, plans
- @file mention expansion (attach files as context)
- Slash command system
- Thinking spinner during LLM calls
- Speaker layout (agent vs user turns)

## Advanced Patterns

### REPL Body (Ori CLI pattern)
- Persistent Python subprocess
- Tree-sitter-indexed codebase graph in memory
- Structural navigation and judgment operations
- Computational reasoning surface
- Recursive self-invocation (rlm_call) for sub-LLM calls

### Persistent Memory
- Knowledge graph with learning retrieval
- Session continuity across restarts
- Warm context injection (top of system prompt)
- Echo/fizzle feedback loop
- Importance accumulation → reflection at threshold

### Sub-agents
- Isolated agent instances for focused subtasks
- Short final reports to parent conversation
- No recursive spawning (depth control)
- Reduces parent conversation bloat

### Planning
- Externalized checklist tools (TodoWrite-style)
- Reduces drift on long sessions
- set_plan, update_plan, get_plan operations
- Encourages model to externalize thinking

## Architecture Comparison

### vibeharness
- **Size**: ~2.4k lines Python
- **Focus**: Educational, hackable
- **Strengths**: Readable end-to-end, all essential patterns
- **Best for**: Learning harness engineering

### Ori CLI
- **Size**: Larger, more complex
- **Focus**: Advanced memory/graph
- **Strengths**: REPL body, persistent memory, React terminal UI
- **Best for**: Production with advanced features

### Claude Agent SDK
- **Size**: Production library
- **Focus**: Batteries included
- **Strengths**: Turnkey, production-ready, comprehensive tooling
- **Best for**: Quick integration, less educational

### OpenAI Agents SDK
- **Size**: Framework
- **Focus**: Multi-agent orchestration
- **Strengths**: Handoffs, sandbox workspaces, multi-agent patterns
- **Best for**: Complex multi-agent workflows

## Key Implementation Decisions

### Language Choice
- **Python**: vibeharness, OpenAI Agents SDK (strong ecosystem for LLM tools)
- **TypeScript**: Claude Agent SDK (good for web/integrated tools)
- **Go**: agent-harness (clean-room implementation, strong typing)

### Terminal UI
- **Rich (Python)**: vibeharness uses Rich for panels
- **Ink (React for terminals)**: Ori CLI uses Ink for complex UI
- **Bubble Tea (Go)**: agent-harness uses Bubble Tea for TUI

### Tool Execution
- **PTY shells**: pexpect (Python) for real shell persistence
- **Direct execution**: subprocess for simple commands
- **Container-based**: OpenAI SandboxAgents for isolated workspaces

### State Management
- **JSON checkpointing**: vibeharness (after every tool call)
- **Session objects**: Claude Agent SDK (structured session protocol)
- **Database persistence**: Claw Code Java (PostgreSQL transcripts)

## Recommended Starting Point

**vibeharness** is the best reference for learning:
- Small enough to read end-to-end (~2.4k lines)
- Includes all essential patterns
- Educational focus with clear architecture
- Python (accessible, strong LLM ecosystem)

## Next Steps for Implementation

1. **Study vibeharness source code** - Read through each module to understand patterns
2. **Choose language and UI framework** - Python/Rich or TypeScript/Ink
3. **Implement core loop first** - Get basic LLM ↔ tools working
4. **Add streaming** - Token-by-token display for responsiveness
5. **Build tool registry** - Start with Read, Write, Edit, Bash
6. **Add permissions** - Auto/ask/deny modes
7. **Implement session persistence** - JSON checkpointing
8. **Add REPL UI** - Streaming display, slash commands
9. **Add advanced features** - Sub-agents, planning, memory (optional)

## Open Questions

- Memory persistence: Simple JSON vs knowledge graph?
- Multi-provider support: Start with one provider or abstraction from day one?
- Sub-agent depth: Allow recursive spawning or hard limit?
- Context compaction: Simple truncation or intelligent summarization?
