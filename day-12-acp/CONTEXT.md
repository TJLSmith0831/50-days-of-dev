# Context

## Glossary

**ACP Agent** - An autonomous AI system that exposes its capabilities via the Agent Communication Protocol (ACP). An agent is discoverable, invocable via HTTP, and can send/receive structured multimodal messages. Agents are framework-agnostic - they can be built with BeeAI, LangChain, CrewAI, or custom code.

**ACP Server** - The HTTP server that hosts one or more ACP agents. It exposes REST endpoints for agent discovery (`GET /agents`), agent invocation (`POST /runs`), and streaming responses. The server handles message serialization, routing, and protocol compliance.

**ACP Client** - Any HTTP-speaking client that can discover and invoke ACP agents. A client can be a CLI tool, a web app, or another agent. The client speaks ACP's REST protocol but doesn't need the ACP SDK - curl works.

**Agent Manifest** - Metadata describing an agent's capabilities: name, description, supported content types, and optional dependencies. The manifest enables discovery without running the agent. Embedded in the agent's distribution package for offline discovery.

**Discovery** - The process of finding available ACP agents and their capabilities. Can be runtime (querying a live server's `/agents` endpoint) or offline (reading embedded manifests). Discovery enables dynamic agent composition.

**Message** - The core ACP communication unit, consisting of a sequence of ordered `MessagePart`s. Messages are multimodal - parts can be text, images, code, files, or custom data. Messages have a role (user, agent, system) and content type (MIME).

**MessagePart** - Individual content unit within a Message. A MessagePart has content (the actual data) and a content_type (MIME type like `text/plain`, `image/png`, `application/json`). Multiple parts combine to form structured, multimodal communication.

**Run** - A single agent execution with specific inputs. A run can be synchronous (wait for completion), asynchronous (fire-and-forget with later status check), or streaming (real-time updates via SSE). Each run has a unique ID for tracking.

**CLI Orchestrator** - The command-line interface that coordinates multiple ACP agents to complete a user request. The orchestrator discovers agents, chains their outputs (agent A's result becomes agent B's input), and displays the communication flow visibly to the user.

**Agent-to-Agent Communication** - Direct communication between agents via ACP, without a central coordinator. Agents can call each other's REST endpoints, exchange structured messages, and collaborate as peers rather than through a manager pattern.

**Streaming** - Real-time delivery of agent output as it's generated, using Server-Sent Events (SSE) over HTTP. Streaming enables live visibility into agent thinking, intermediate results, and progress updates.

## Scope

This day builds a CLI orchestrator that:
1. Discovers available ACP agents from a local server
2. Chains multiple real LLM-backed agents to complete a user request
3. Displays live agent-to-agent communication and intermediate thoughts
4. Demonstrates framework-agnostic interoperability (agents could be built with different stacks)

**Agent capabilities:**
- **Researcher agent** - Uses web search (DuckDuckGo) to gather information on a topic
- **Writer agent** - Uses LLM to draft content based on research output
- **Critic agent** - Uses LLM to review and suggest improvements to the draft

All agents are real, LLM-backed capabilities using OpenAI's gpt-4.1-mini model, not stubs or role-playing.

## Framework Decision

**BeeAI Framework** is used for agent implementation. BeeAI is IBM's open-source agent framework and the reference implementation for ACP. It provides:

- Built-in ACP integration via `beeai-framework[acp]`
- ReAct agents with tool-calling support
- Memory management (UnconstrainedMemory, TokenMemory)
- Tool ecosystem (DuckDuckGo search, weather, etc.)
- LLM backend abstraction (Ollama, Anthropic, OpenAI)

The CLI orchestrator uses the raw ACP SDK (`acp-sdk`) for HTTP client operations, while the agents themselves are built with BeeAI and exposed via BeeAI's ACPServer.

## Implementation Decisions

**CLI interface**: Simple single-command invocation - `uv run cli.py "research and write about quantum computing"`. The CLI parses the natural language request and routes it through the agent chain automatically.

**Error handling**: If an agent fails mid-chain, the CLI retries with a fallback strategy but fails transparently - the error is logged and displayed, but the CLI continues to the next agent or terminates gracefully rather than crashing.

**Model selection**: Uses OpenAI's gpt-4.1-mini model (hosted API) for all agents. The API key is configured via `OPENAI_API_KEY` in the day's `.env` file. This choice prioritizes reliability and tool-calling quality over local-only constraints.
