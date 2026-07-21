# Day 10 — Subagent MCP — Context

## Glossary

**Advisor** — A bounded subagent that provides upfront planning and strategic guidance before Claude begins work. Its goal is to reduce output token burn by giving Claude better instructions so it needs fewer turns to complete a task. Accepts a task description and returns a recommended approach, potential pitfalls, and efficiency considerations.

**Bounded agent** — A subagent with a hard limit on turns (typically 1-2) and no open-ended tool-calling loop. Unlike full autonomous agents, bounded agents complete a single operation and return a result. This pattern aligns with MCP's request-response model and keeps token spend predictable.

**Critiquer** — A bounded subagent that observes Claude's coding session and analyzes token efficiency. It tracks session state from start to end, compares actual token usage against an ideal baseline, and writes improvement notes to AGENTS.md or CLAUDE.md. Exposed via session bookend tools: `start_session` initializes tracking, `end_session` triggers analysis and writes findings.

**Researcher** — A bounded subagent that performs web search, takes notes, and synthesizes research. Uses duckduckgo-search (ddgs) for web queries, then organizes findings into structured notes. Accepts a research query and returns synthesized results with sources.

**Session** — A bounded unit of work tracked by the critiquer, from `start_session` (with goals) to `end_session` (with full conversation history). The MCP server maintains in-memory session state including start time, goals, and action logs. Session data is lost on server restart.

**Subagent** — A local SLM (via Ollama) exposed as an MCP tool to Claude. Subagents are bounded agents that Claude can delegate to for specific tasks (research, advice, critique). Unlike frontier model subagents, these use local models to minimize token cost while providing specialized capabilities.

**Token efficiency analysis** — The critiquer's core function: comparing actual token usage against an ideal baseline for a session. The critiquer identifies patterns of waste (e.g., redundant file reads, inefficient turn sequences) and writes actionable improvement notes to project files without hurting output quality.

## Key Decisions

- **Bounded agents only**: Subagents are 1-2 turn operations, not full autonomous loops. This aligns with MCP's request-response model and keeps token spend predictable.
- **Local Ollama models**: Subagents use local SLMs (mistral to start) to minimize token cost. Claude (frontier model) remains the conductor.
- **Tool per subagent**: Three separate MCP tools — `research(query)`, `advise(task)`, and session bookends `start_session(session_id, goals)` + `end_session(session_id, history)`. No single dispatch tool.
- **Researcher uses ddgs**: Web search via duckduckgo-search library. Claude does not pass search results; the researcher handles the full search-to-synthesis pipeline.
- **In-memory session store**: Critiquer tracks sessions in a dictionary. State is lost on server restart. No file-based persistence for this demo.
- **Critiquer writes to project files**: Findings are written to AGENTS.md or CLAUDE.md as improvement notes. The critiquer does not return structured JSON — it writes directly to files.
- **Advisor focuses on output tokens**: The advisor's goal is reducing output token burn (Claude's responses) by providing better upfront instructions. Input token burn is rarely the issue.
- **Full workflow demo**: Measurable outcome is a complete workflow — advisor plans, researcher gathers info, Claude codes a simple task, critiquer analyzes the session.
