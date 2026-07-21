# Spec: Day-10 Subagent MCP

## Problem Statement

Frontier model agents like Claude Code burn significant tokens on output, especially during multi-turn coding sessions. Local SLMs via Ollama are cheaper but lack the specialized capabilities that make frontier models effective. There is no way for Claude to delegate to local SLM subagents for specific tasks (research, planning, critique) while remaining the conductor, nor is there a mechanism to analyze token efficiency and provide improvement guidance.

## Solution

Build an MCP server that exposes three bounded subagents via MCP tools: Researcher (web search + synthesis via duckduckgo-search), Advisor (upfront planning to reduce output token burn), and Critiquer (session observer that analyzes token efficiency and writes improvement notes to AGENTS.md or CLAUDE.md). The MCP server uses local Ollama models (mistral to start) for all subagent invocations. A demo workflow shows Claude using all three subagents in sequence during a simple coding task, with the critiquer providing token efficiency analysis.

## User Stories

1. As an MCP client developer, I want a research tool that performs web search and synthesizes findings, so that I can delegate information gathering to a local SLM.
2. As an MCP client developer, I want the research tool to use duckduckgo-search, so that I don't need API keys for web search.
3. As an MCP client developer, I want an advisor tool that provides upfront planning and strategic guidance, so that I can reduce output token burn by giving Claude better instructions.
4. As an MCP client developer, I want the advisor to focus on reducing output tokens (Claude's responses), so that the most expensive token type is minimized.
5. As an MCP client developer, I want a critiquer tool that tracks coding sessions from start to end, so that I can analyze token efficiency across a complete workflow.
6. As an MCP client developer, I want the critiquer to compare actual token usage against an ideal baseline, so that I can identify patterns of waste.
7. As an MCP client developer, I want the critiquer to write improvement notes to AGENTS.md or CLAUDE.md, so that future sessions benefit from the analysis.
8. As an MCP client developer, I want session tracking to be in-memory, so that the implementation is simple for a demo (state lost on server restart is acceptable).
9. As a demo runner, I want to see a full workflow using all three subagents, so that I can understand how they work together.
10. As a demo runner, I want the workflow to include a simple coding task, so that the critiquer has real work to analyze.
11. As a developer, I want subagents to be bounded (1-2 turns max), so that token spend is predictable and the pattern aligns with MCP's request-response model.
12. As a developer, I want subagents to use local Ollama models, so that token cost is minimized compared to frontier model subagents.
13. As a developer, I want tool-per-subagent interface (not single dispatch), so that each tool has a clear purpose and signature.

## Implementation Decisions

- **MCP server structure**: Single MCP server with four tools: `research(query: string)`, `advise(task: string)`, `start_session(session_id: string, goals: string)`, `end_session(session_id: string, history: string)`.
- **Subagent implementation**: Each tool invokes a local Ollama model (mistral) with a bounded agent pattern (1-2 turns max). No open-ended tool-calling loops within subagents.
- **Researcher subagent**: Uses duckduckgo-search (ddgs) library for web search. Accepts a query, performs search, synthesizes findings into structured notes with sources, returns the synthesis.
- **Advisor subagent**: Accepts a task description, returns a recommended approach, potential pitfalls, and efficiency considerations. Focuses on reducing output token burn by providing better upfront instructions.
- **Critiquer subagent**: Session bookend pattern. `start_session` initializes in-memory session state (session_id, goals, start time). `end_session` retrieves session state, analyzes the conversation history for token efficiency patterns, compares actual vs ideal usage, and writes improvement notes to AGENTS.md or CLAUDE.md.
- **Session state management**: In-memory dictionary mapping session_id to session data. State is lost on server restart. No file-based persistence.
- **Ollama integration**: Use LangChain's Ollama integration or direct HTTP calls to Ollama API. Model: mistral (configurable).
- **Demo workflow**: Python client using `mcp` Python SDK with stdio transport. Workflow:
  1. Call `advise` with a simple coding task (e.g., "build a CLI that greets the user")
  2. Call `research` if the task requires information gathering
  3. Call `start_session` with session goals
  4. Simulate Claude doing the coding task (or actually do it if Claude is the demo runner)
  5. Call `end_session` with the conversation history
  6. Show the critiquer's written improvement notes
- **pyproject.toml scripts**: `[tool.scripts] start = "python src/index.py"` for the MCP server, `demo = "python src/demo.py"` for the workflow demo.
- **Dependencies**: `mcp` Python SDK, `duckduckgo-search`, LangChain (for Ollama integration) or direct `ollama` Python package.

## Testing Decisions

- **What makes a good test**: The demo itself is the test — it must show a complete workflow using all three subagents and demonstrate the critiquer writing improvement notes.
- **Testing approach**: No unit tests. The `uv run demo` command is the verification. It must:
  1. Call `advise` with a coding task and receive planning guidance
  2. Call `research` (if applicable) and receive synthesized findings
  3. Call `start_session` and confirm session is initialized
  4. Simulate or perform a coding session
  5. Call `end_session` with conversation history
  6. Verify that improvement notes are written to AGENTS.md or CLAUDE.md
  7. Print the workflow results and the critiquer's analysis
- **Prior art**: Day 8 and Day 9's demo client pattern — spawn server as child process, connect via stdio, call tools, print results, exit cleanly.

## Out of Scope

- OpenRouter integration (local Ollama only for this demo)
- File-based session persistence (in-memory only)
- Real-time checkpointing during sessions (session bookends only)
- Subagent spawning subagents (one-level hierarchy only)
- Full autonomous agent loops (bounded agents only)
- Multiple model configurations (single mistral model to start)
- Token counting from Ollama (estimated based on conversation length)
- Interactive demo input (hardcoded task for the demo)

## Further Notes

- The critiquer's token efficiency analysis is heuristic-based since Ollama may not provide exact token counts. The analysis will estimate based on conversation length and turn patterns.
- The demo coding task should be simple enough to complete in a few turns (e.g., a CLI that greets the user) so that the workflow is clear and the critiquer has meaningful data to analyze.
- The advisor's focus on output tokens is intentional — input token burn is rarely the issue in Claude Code sessions.
- The critiquer writes directly to project files (AGENTS.md or CLAUDE.md) rather than returning structured JSON, which aligns with the goal of providing actionable improvement notes in the project's own documentation format.
