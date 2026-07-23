# Spec: Day-12 ACP Agent

## Problem Statement

Modern AI agents are often built in isolation across different frameworks (BeeAI, LangChain, CrewAI, custom code), making it difficult to discover, reuse, or integrate them across platforms. This fragmentation leads to duplicated work, inconsistent developer experience, and one-off integrations that don't scale. While protocols like MCP standardize agent-to-tool communication, there is no widely-adopted standard for agent-to-agent communication that enables agents to discover and collaborate with each other regardless of their implementation framework.

## Solution

Build a CLI orchestrator that demonstrates IBM's Agent Communication Protocol (ACP) by chaining three real LLM-backed agents (researcher, writer, critic) built with BeeAI Framework. The CLI discovers available agents via ACP's REST endpoints, chains their outputs (researcher's findings → writer's draft → critic's review), and displays live agent-to-agent communication with streaming thoughts. This demonstrates framework-agnostic interoperability - agents built with BeeAI can be discovered and invoked by any ACP client without custom integration code.

## User Stories

1. As a developer, I want to discover available ACP agents via a CLI command, so that I can understand what capabilities are exposed without reading documentation.
2. As a developer, I want to invoke an ACP agent via a simple CLI command, so that I can test agent capabilities without writing HTTP client code.
3. As a developer, I want to chain multiple ACP agents together, so that I can build workflows where agent outputs become agent inputs.
4. As a developer, I want to see live agent-to-agent communication, so that I can understand how agents are collaborating in real-time.
5. As a developer, I want to see intermediate agent thoughts during execution, so that I can debug agent reasoning and identify bottlenecks.
6. As a developer, I want the CLI to handle agent discovery automatically, so that I don't need to manually configure agent endpoints.
7. As a developer, I want the CLI to handle message routing between agents, so that I don't need to implement ACP protocol details.
8. As a developer, I want error handling to be transparent, so that if an agent fails, I see what went wrong without the CLI crashing.
9. As a developer, I want the CLI to use natural language input, so that I don't need to learn a structured command syntax.
10. As a demo viewer, I want to see a complete workflow from request to final output, so that I understand the value of ACP in under a minute.
11. As a demo viewer, I want to see three distinct agent capabilities (research, writing, critique), so that I understand how different agents can collaborate.
12. As a demo viewer, I want to see the communication flow visually, so that I can trace how data moves between agents.
13. As an agent developer, I want agents to be framework-agnostic, so that I can build agents with BeeAI and have them work with any ACP client.
14. As an agent developer, I want to use BeeAI's built-in ACP integration, so that I don't need to implement ACP protocol details manually.
15. As an agent developer, I want to expose agents via a single HTTP server, so that deployment is simple.
16. As a researcher agent user, I want web search capabilities, so that the agent can gather current information.
17. As a writer agent user, I want LLM-backed content generation, so that the agent can draft coherent text.
18. As a critic agent user, I want LLM-backed analysis, so that the agent can provide meaningful feedback.
19. As a CLI user, I want the command to be simple (`uv run cli.py "research and write about X"`), so that the barrier to entry is low.
20. As a CLI user, I want the output to be readable, so that I can quickly understand the results.

## Implementation Decisions

- **Framework choice**: BeeAI Framework for agent implementation. BeeAI is IBM's open-source agent framework and the reference implementation for ACP. It provides built-in ACP integration via `beeai-framework[acp]`, ReAct agents with tool-calling, memory management, and tool ecosystem.
- **Agent implementation**: Three ReAct agents built with BeeAI:
  - Researcher agent: Uses DuckDuckGo search tool to gather information on a topic
  - Writer agent: Uses LLM to draft content based on research output
  - Critic agent: Uses LLM to review and suggest improvements to the draft
- **ACP Server**: BeeAI's ACPServer hosts all three agents on a single HTTP server (default port 8000). Server exposes REST endpoints for agent discovery (`GET /agents`), agent invocation (`POST /runs`), and streaming responses.
- **CLI orchestrator**: Separate Python script using ACP SDK (`acp-sdk`) for HTTP client operations. CLI discovers agents, chains their outputs, and displays streaming communication.
- **Model selection**: OpenAI's gpt-4.1-mini model (hosted API) for all agents. API key configured via `OPENAI_API_KEY` in `.env` file. This choice prioritizes reliability and tool-calling quality over local-only constraints.
- **CLI interface**: Simple single-command invocation - `uv run cli.py "research and write about quantum computing"`. CLI parses natural language request and routes through agent chain automatically.
- **Agent chaining**: Fixed pipeline for demo: researcher → writer → critic. Researcher output becomes writer input, writer output becomes critic input. CLI handles message transformation between ACP Message format and agent expectations.
- **Streaming display**: CLI uses ACP SDK's streaming support to display live agent thoughts and intermediate results as they're generated via Server-Sent Events (SSE).
- **Error handling**: If an agent fails mid-chain, CLI retries with fallback strategy but fails transparently - error is logged and displayed, but CLI continues to next agent or terminates gracefully rather than crashing.
- **Discovery mechanism**: CLI queries ACP server's `/agents` endpoint at startup to get available agents and their capabilities. No hardcoded agent list.
- **Message format**: ACP Messages with MessageParts for multimodal content. CLI handles serialization/deserialization via ACP SDK.
- **Project structure**: Two entry points - `server.py` (BeeAI ACPServer with agents) and `cli.py` (orchestrator). Shared dependencies in `pyproject.toml`.
- **Dependencies**: `beeai-framework[acp]`, `acp-sdk`, `duckduckgo-search` (for researcher), OpenAI Python SDK.

## Testing Decisions

- **What makes a good test**: The demo itself is the test - it must show a complete workflow using all three agents with live communication display. Tests external behavior (CLI invocation, agent chaining, streaming output) not implementation details.
- **Testing approach**: No unit tests. The `uv run cli.py "research and write about quantum computing"` command is the verification. It must:
  1. Start the ACP server and register three agents
  2. Discover agents via `/agents` endpoint
  3. Invoke researcher agent and display results
  4. Pass researcher output to writer agent and display results
  5. Pass writer output to critic agent and display results
  6. Show live streaming thoughts during execution
  7. Display final output with agent communication flow
- **Secondary seams**: Server health check via `curl http://localhost:8000/agents` for debugging. Individual agent invocation via ACP SDK if needed.
- **Prior art**: Day-10 demo-as-test pattern - spawn server, invoke workflow, verify end-to-end behavior. Day-8 and Day-9 MCP server testing approach.

## Out of Scope

- Dynamic agent routing (fixed pipeline for demo)
- Agent-to-agent direct communication (CLI orchestrator mediates)
- Multi-framework agents (all agents built with BeeAI for demo)
- Local model support (gpt-4.1-mini only for this demo)
- Persistent agent state (stateless ReAct agents)
- Complex error recovery strategies (basic retry with transparent failure)
- Agent marketplace or catalog (local server only)
- Authentication/authorization (localhost only)
- Agent versioning or compatibility checking
- Custom ACP protocol extensions (standard ACP only)

## Further Notes

- The demo uses gpt-4.1-mini instead of local models to ensure reliable tool-calling and coherent multi-agent collaboration, which is the focus of the day (ACP interoperability) rather than local model optimization.
- BeeAI's ACP integration is the reference implementation, making it the natural choice for demonstrating ACP despite the official `i-am-bee/acp` repo being archived (migrated to A2A under Linux Foundation).
- The CLI orchestrator uses the ACP SDK rather than raw HTTP calls to leverage built-in message serialization, streaming support, and error handling.
- Live communication display is a key differentiator - it shows not just the final output but the agent-to-agent message flow and intermediate thoughts, making ACP's value visible.
- The fixed pipeline (researcher → writer → critic) is a simplification for the demo. Real ACP deployments could use dynamic routing, agent negotiation, or peer-to-agent communication.
- Error handling prioritizes transparency over complex recovery - the goal is to show that ACP enables graceful degradation, not to build production-grade fault tolerance.
