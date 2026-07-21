# Subagent Best Practices — Research Summary

## Anthropic Findings

### Architecture Pattern
- **Orchestrator-worker pattern**: Lead agent coordinates and delegates to specialized subagents
- Subagents operate in parallel for speed
- One-level hierarchy: subagents cannot spawn their own subagents

### Context Isolation
- Subagents have **isolated context** — they do NOT inherit coordinator's conversation history
- All necessary information must be explicitly passed in the subagent's prompt
- Only the subagent's final message returns to coordinator; all intermediate work stays sealed
- This protects coordinator's context from overflowing

### Delegation Mechanics
- Subagents spawned via **Agent tool** (formerly Task tool)
- Coordinator's `allowed_tools` MUST include "Agent" or delegation silently never happens
- Never include "Agent" in a subagent's own tool list (prevents runaway nesting)

### Best Practices
- **Pass complete prior findings** as structured data so each claim carries its source metadata
- **Parallelism**: Fire all delegations in one response for independent work to get speed benefits
- **Scale effort to query complexity**: Simple fact-finding = 1 agent with 3-10 tool calls; direct comparisons = 2-4 subagents with 10-15 calls each; complex research = 10+ subagents
- **Tool design is critical**: Give agents explicit heuristics for tool selection

### Subagent Description Quality
Description is the routing layer. Reliable descriptions have four parts:
1. **Primary responsibility** — what the subagent does
2. **Trigger language** — when to delegate (e.g., "Use proactively when...")
3. **Scope boundaries** — what belongs here vs what does not
4. **Expected output** — what should come back

Template: `[Do this specific job]. Use proactively when [clear trigger conditions]. Best for [scope]. Not for [out-of-scope work]. Return [expected result shape].`

### When to Use Agents
- Open-ended problems where you can't predict the required number of steps
- When you can't hardcode a fixed path
- When you need LLMs to operate for many turns with some level of trust in decision-making
- Agents = LLMs using tools in a loop with environmental feedback

### Core Principles
1. Maintain simplicity in agent design
2. Prioritize transparency
3. Start with simple prompts, optimize with evaluation, add multi-step systems only when simpler solutions fall short

---

## OpenAI Findings

### Two Main Patterns

**Handoffs**
- Specialist takes over conversation for that branch of work
- Control moves to the specialist
- Use when: specialist should own the next response rather than merely helping behind the scenes
- Best for: routing itself is part of the workflow, want specialist to respond directly

**Agents as Tools**
- Manager stays in control and calls specialists as bounded capabilities
- Manager keeps ownership of the reply
- Use when: manager should synthesize final answer, specialist does bounded task, want one stable outer workflow
- Generally recommended for subagents

### When to Add Specialists
- Start with one agent whenever you can
- Add specialists only when they materially improve:
  - Capability isolation
  - Policy isolation
  - Prompt clarity
  - Trace legibility
- Splitting too early creates more prompts, traces, and approval surfaces without necessarily making workflow better

### Token Cost
- Subagent workflows **consume more tokens** than comparable single-agent runs
- Each subagent does its own model and tool work

### Parallel Execution
- Good for: read-heavy tasks (exploration, tests, triage, summarization)
- Be careful with: parallel write-heavy workflows (agents editing code at once can create conflicts)
- Codex waits until all requested results are available, then returns consolidated response

### Model Selection
- Different agents need different model and reasoning settings
- If not pinned, Codex can choose setup balancing intelligence, speed, and price
- Model guidance:
  - `gpt-5.6`: Demanding agents, ambiguous multi-step work with planning and tool use
  - `gpt-5.4`: Pinned to GPT-5.4, strong coding + reasoning + broader workflows
  - `gpt-5.6-terra`: Speed/efficiency over depth, exploration, read-heavy scans, parallel workers
  - `gpt-5.3-codex-spark`: Near-instant text-only iteration when latency matters

### Benefits
- Move noisy work off main thread
- Keep main agent focused on requirements, decisions, and final outputs
- Return summaries from subagents instead of raw intermediate output
- Make larger tasks tractable by breaking into bounded pieces

---

## LangChain Findings

### Key Characteristics
- **Centralized control**: All routing passes through the main agent
- **No direct user interaction**: Subagents return results to the main agent, not the user (interrupts can allow user interaction within subagents)
- **Subagents via tools**: Subagents are invoked via tools
- **Parallel execution**: The main agent can invoke multiple subagents in a single turn

### Tool Patterns

**Tool per Agent**
- Each subagent wrapped as its own tool
- Simple pattern: create agent, wrap as @tool, add to main agent's tools
- Example: `@tool("research", description="Research a topic and return findings")`

**Single Dispatch Tool**
- One parameterized tool that can invoke any registered sub-agent by name
- Convention-based invocation: Agent selected by name, task passed as human message, final message returned as tool result
- Team distribution: Different teams can develop and deploy agents independently
- Agent discovery: Sub-agents can be discovered via system prompt (listing available agents) or through progressive disclosure (loading agent information on-demand via tools)

### Registry Pattern
- Dictionary-based registry of available sub-agents: `SUBAGENTS = {"research": research_agent, "writer": writer_agent}`
- Single `task` tool with `agent_name` and `description` parameters
- Tool description lists available agents for the coordinator
- Coordinator's system prompt should list available agents and instruct to use the task tool

### Implementation Example
```python
@tool
def task(agent_name: str, description: str) -> str:
    """Launch an ephemeral subagent for a task. Available agents:
    - research: Research and fact-finding
    - writer: Content creation and editing
    """
    agent = SUBAGENTS[agent_name]
    result = agent.invoke({"messages": [{"role": "user", "content": description}]})
    return result["messages"][-1].content
```

### Context Engineering
- **Subagent specs**: Define what each subagent does
- **Subagent inputs**: What data to pass to subagents
- **Subagent outputs**: What format to expect back

### Checkpointing and State Inspection
- Supports `checkpointer=True` for subgraph persistence
- `get_state` with `subgraphs` parameter for state inspection
- Can use interrupts within subagents for human interaction

### Sync vs Async
- Supports both synchronous and asynchronous execution
- Use `async`/`await` for async patterns

---

## Key Cross-Platform Insights

### Common Patterns
- **Manager-style orchestration** is generally preferred for subagents (Anthropic's Agent tool, OpenAI's agents-as-tools)
- **Context isolation** is critical — subagents don't inherit parent context
- **Parallel execution** for independent work is a key speed benefit
- **Summaries over raw output** — return distilled results, not intermediate noise

### Trade-offs
- **Token cost**: Subagents always cost more than single-agent runs
- **Complexity**: More agents = more prompts, traces, approval surfaces
- **Coordination overhead**: Parallel write-heavy workflows risk conflicts

### When Subagents Make Sense
- Task can be decomposed into independent parallel pieces
- Different specialists need different tools, policies, or model configurations
- Read-heavy exploration/analysis where parallel speedup outweighs token cost
- Need to keep main agent focused on synthesis rather than execution

### When They Don't
- Simple tasks that don't benefit from decomposition
- Write-heavy workflows where coordination overhead dominates
- When token cost is a primary constraint
- When one agent can handle the task adequately
