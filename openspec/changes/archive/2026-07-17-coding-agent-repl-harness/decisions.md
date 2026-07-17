# Decision Log

## D1: What is the core problem being solved?
- **Decision**: Ship a production-ready coding agent harness with a rich CLI REPL quickly, while understanding how it works
- **Why**: User needs a working tool fast but wants to understand the internals, not build from scratch
- **Source**: user

## D2: What are the essential components identified from research?
- **Decision**: Core loop, provider abstraction, tool system, permissions, context management, session layer, REPL UI
- **Why**: These are the patterns common across all production harnesses studied (vibeharness, Ori CLI, Claude Agent SDK, OpenAI Agents SDK)
- **Source**: grill-explore

## D3: What is the recommended approach given local-first requirement?
- **Decision**: Build Python harness using vibeharness as reference, support local models via Ollama
- **Why**: Local-first means avoiding cloud SDK dependencies; vibeharness is Python, supports local models, and has the right patterns
- **Source**: user

## D4: What language and framework for the harness?
- **Decision**: Python with Rich for terminal UI
- **Why**: User specified Python; Rich is the standard for beautiful terminal interfaces in Python (used by vibeharness)
- **Source**: user

## D5: What model providers should be supported?
- **Decision**: Ollama (local models) only for initial version; multi-provider support added later
- **Why**: User wants to focus on local support first; keeps initial scope manageable
- **Source**: user

## D6: What memory persistence approach should be used?
- **Decision**: SQLite database for session and memory persistence
- **Why**: User chose SQLite over JSON; provides better querying, transaction support, and scalability for a production tool
- **Source**: user

## D7: What should the initial tool set include?
- **Decision**: Read, Glob, Grep, Web Search (ddgs), and openspec CLI integration only
- **Why**: SDD workflow requires research tools (Read, Glob, Grep, Web Search) and openspec integration for spec management. Write/Edit/Bash are excluded in v1 since Claude Code handles implementation via opsx:apply handoff.
- **Source**: user (amended from recommended-accepted to align with D12-D16 SDD focus)

## D8: What permission model should be used?
- **Decision**: Deferred to future version
- **Why**: All v1 tools are read-only (Read, Glob, Grep, Web Search, openspec CLI), so no permission model needed until Write/Edit/Bash are added
- **Source**: user (amended from recommended-accepted)

## D9: Should sub-agents be supported in the initial version?
- **Decision**: No, defer sub-agents to future version
- **Why**: Adds complexity (depth control, isolated contexts); core harness functionality is already substantial
- **Source**: user

## D10: What context compaction strategy should be used?
- **Decision**: Simple token-based truncation for initial version; intelligent summarization as future enhancement
- **Why**: Straightforward to implement, sufficient for local models with smaller context windows
- **Source**: recommended-accepted

## D11: What terminal UI features should be included?
- **Decision**: Streaming token display, thinking spinner, speaker layout (agent vs user), @file mention expansion, slash commands (/help, /save, /sessions, /exit), rich panels for diffs/bash output, syntax highlighting for code
- **Why**: These are the core REPL features from vibeharness that provide a good UX without over-engineering
- **Source**: recommended-accepted

## D12: What is the primary use case for this harness?
- **Decision**: Spec Driven Design (SDD) writer using openspec, with grilling ability (grill-with-docs, grill-me skills) and Claude Code handoff via headless Claude
- **Why**: User wants a focused tool that uses smaller models to research/plan specs, then hands off to Claude Code for implementation via opsx:apply
- **Source**: user

## D13: What does "grilling ability" mean?
- **Decision**: Integration with existing grill-with-docs and grill-me skills for interactive questioning and requirements gathering
- **Why**: User has these skills and wants to leverage them for spec development
- **Source**: user

## D14: What does "handoff to Claude Code via headless Claude" mean?
- **Decision**: When user confirms spec is ready, harness calls Claude Code headless API to run opsx:apply for implementation
- **Why**: User wants to use smaller models for planning/research, then leverage Claude Code for actual implementation
- **Source**: user

## D15: What model provider should be used?
- **Decision**: Qwen3:14b (via Ollama) for research and spec planning; Claude API for Claude Code headless integration
- **Why**: Cost-effective approach - use Qwen3:14b for planning, premium Claude model for implementation
- **Source**: user

## D16: What additional tools are needed?
- **Decision**: Add web search tool using ddgs (DuckDuckGo Search)
- **Why**: User needs web search capability for research during spec development
- **Source**: user

## Future Enhancements
- Intelligent context summarization
- Multi-provider support (Anthropic, OpenAI, etc.)
- Sub-agents for focused subtasks
- Planning tools (set_plan, update_plan, get_plan)
- Advanced memory with knowledge graph
