# Agent Communication Protocol (ACP) Research

## What is ACP?

Open standard for agent-to-agent communication, developed by IBM/BeeAI, now part of A2A under Linux Foundation. Key characteristics:

- **REST-based HTTP** (unlike MCP's JSON-RPC)
- **Framework-agnostic** - agents built with any stack can interoperate
- **Multimodal messages** - text, images, code, files
- **Async-first, sync supported** - handles long-running tasks
- **Offline discovery** - agents embed metadata for discovery when inactive
- **No SDK required** - works with curl/Postman, but SDKs available

## Popular Repositories

### i-am-bee/acp (1,019 stars, archived)
- **Official IBM/BeeAI implementation** (migrated to A2A)
- Python SDK (`acp-sdk`) and TypeScript SDK
- Comprehensive documentation at agentcommunicationprotocol.dev
- Extensive examples directory
- **Starting point**: Quickstart guide with echo agent

### agentclientprotocol/agent-client-protocol (3,711 stars)
- **Different ACP** - Agent Client Protocol for editor↔agent communication
- Rust-based with SDKs: Java, Python, Kotlin, TypeScript, Dart, C++
- Focus on coding agents in IDEs
- **Starting point**: Language-specific SDK examples

### Kickflip73/agent-communication-protocol (7 stars)
- P2P, zero-server approach
- Multi-language SDKs (Python, Node.js, Go, Rust, Java)
- **Starting point**: SKILL.md for onboarding

### agent-context-protocol/agent-context-protocol
- Focus on multi-agent coordination and fault tolerance
- Integrates with MCP for tool access
- **Starting point**: `pip install agent_context_protocol`

## Quickstart Recipes

### 1. Official ACP Echo Agent (Python)
```bash
uv init --python '>=3.11' my_acp_project
cd my_acp_project
uv add acp-sdk
```

```python
# agent.py
import asyncio
from collections.abc import AsyncGenerator
from acp_sdk.models import Message
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()

@server.agent()
async def echo(input: list[Message], context: Context) -> AsyncGenerator[RunYield, RunYieldResume]:
    """Echoes everything"""
    for message in input:
        yield message

server.run()
```

### 2. BeeAI Framework Integration
```bash
pip install 'beeai-framework[acp]'
```

```python
from beeai_framework.adapters.acp import ACPServer, ACPServerConfig
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel

llm = ChatModel.from_name("ollama:llama3.1")
agent = ReActAgent(llm=llm, tools=[], memory=UnconstrainedMemory())
ACPServer(config=ACPServerConfig(port=8001)).register(agent).serve()
```

### 3. Multi-Agent Workflow (IBM Tutorial)
Demonstrates BeeAI + CrewAI integration with 4 agents:
- Research agent (CrewAI)
- SongWriter agent (CrewAI)
- A&R critique agent (BeeAI)
- Markdown report agent (CrewAI)

## Example Patterns

- **Chat agents with tools/memory** - BeeAI ReAct agents
- **Slack agents using MCP** - MCP server integration
- **RAG with LlamaIndex** - Document retrieval
- **Prompt chaining** - Sequential agent execution
- **Dynamic routing** - Language-specific translation
- **Handoff patterns** - Multilingual delegation
- **CrewAI integration** - Collaborative agent crews

## Documentation & Learning

- **Official docs**: agentcommunicationprotocol.dev
- **DeepLearning.AI course**: Hands-on ACP introduction
- **OpenAPI spec**: GitHub REST API definition
- **IBM tutorial**: Multi-agent workflows with BeeAI + CrewAI
