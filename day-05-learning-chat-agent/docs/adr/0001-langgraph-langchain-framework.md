# ADR 0001: LangGraph/LangChain Framework Choice

## Status

Accepted

## Context

Day 05 attempted to build a self-improving agent using a bare-metal approach (single Python file, custom loop, subprocess grading). This approach became too focused on metrics (test scores, attempt counts, lesson verification) rather than demonstrating the core agentic pattern of memory-based learning.

For Day 06, the goal is to build a learning chat agent that:

- Adapts to user writing style across sessions
- Accepts human-in-the-loop feedback
- Uses tools (file writing to sandbox)
- Distinguishes between learning vs responding
- Works with local models (Ollama) to avoid API costs

## Decision

Use **LangGraph with LangChain** as the framework.

### Rationale

**Ollama Integration**

- LangChain has native Ollama support, enabling fully local operation
- No API costs compared to Claude Agents managed service
- Fits the "50 Days of Dev" constraint of local-first development

**Memory Patterns**

- LangGraph's checkpointer system provides built-in session persistence
- The "agents-from-scratch" repository includes a concrete example: email assistant with memory that learns from user feedback
- MemorySaver and other checkpointers handle the cross-session persistence problem

**Ecosystem and Examples**

- Larger community and more tutorials than CrewAI
- Reflection agents pattern provides explicit self-reflection loops adaptable for writing style learning
- More granular control over memory strategies, which aligns with the goal of understanding core patterns

**Tool Usage**

- LangChain's tool calling mechanism is mature and well-documented
- Easy to implement file writing tools for sandbox operations
- ToolNode and tools_condition are prebuilt and tested

**Trade-offs Accepted**

- More boilerplate than CrewAI's cognitive memory system
- Must implement "when to learn vs when to respond" logic manually (this is intentional for understanding the pattern)
- LangGraph state management has learning curve, but this aligns with educational goal

## Alternatives Considered

### CrewAI

**Pros**: Built-in cognitive memory with 5 operations (encode, consolidate, recall, extract, forget); handles "when to learn" automatically

**Cons**: Heavier framework; less mature ecosystem; default embedder uses OpenAI (requires configuration for fully local); may be overkill for learning-focused demo

### Claude Agents

**Pros**: Memory stores and Dreaming service purpose-built for agent memory

**Cons**: Managed service with API costs; contradicts local-first constraint; less educational value for understanding underlying patterns

### Bare-metal (Day 05 approach)

**Pros**: Maximum control; no framework overhead

**Cons**: Reinforces metrics-focused implementation; reinvents well-solved problems; slower to demonstrate learning patterns

## Consequences

- Must implement learning/responding decision logic manually
- Need to configure LangGraph checkpointer for session persistence
- Tool implementation for file writing will use LangChain's tool calling
- Memory storage will use LangGraph's persistence layer rather than custom solution
- Demo will show clear session-to-session preference retention
