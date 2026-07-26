# Day 14 Ship Day — Exploration

## D1: What is Day 14 Ship Day building?
- **Decision**: Not a straight portfolio-polish of day-12-acp or day-13-smart-tool-selector. Build a new, standalone "smart tool selection" package that generalizes day-13's semantic-router pre-filtering technique into reusable middleware, rather than shipping day-13's one-off OpenAI-Agents-SDK benchmark as-is.
- **Why**: User's Ship Day goal is genuine open-source stars/awareness. Day-13's router technique (embed query, embed tool example-utterances, top-k pre-filter) is the reusable, provider-agnostic core; the benchmark harness around it (OpenAI Agents SDK, `RunHooks` call-cap, etc.) is not. Day-12's ACP demo has a narrower audience and the underlying protocol's canonical repo was recently archived/folded into A2A, which undercuts long-term star growth.
- **Source**: user

## D2: What does the MCP server actually do (the differentiator)?
- **Decision**: Not a thin wrapper around the `semantic-router` package. It aggregates real downstream MCP servers (connects out to each, pulls their real `list_tools`) rather than a hardcoded fake tool catalog. It exposes a single `find_tool`-style meta-tool to the client; on a query it embeds the request, matches against the aggregated tool set using the semantic-router/fastembed approach adapted from day-13 (not day-13's OpenAI-Agents-SDK harness), returns the top-k real tools, and proxies the actual call through to whichever downstream server owns it. It also tracks and reports token savings live (naive all-tools cost vs. actual routed cost) instead of only reporting Day 13's one-time benchmark finding.
- **Why**: A bare semantic-router wrapper is not differentiated — anyone gets 80% of that from semantic-router's own examples. The real, common pain is too many connected MCP servers flooding a client's context with every tool from every server; routing across a *real* aggregated set (not a fabricated catalog) solves that directly and turns Day 13's "58% token savings" finding into a live, self-demonstrating feature of the tool itself.
- **Source**: user

## D3: New repository, separate from 50-days-of-dev
- **Decision**: Ships as its own new GitHub repository, not a `day-14-slug/` folder inside this monorepo.
- **Why**: It's a standalone open-source package meant to gain its own stars/visibility, not a challenge-day artifact — bundling it inside the 50-days-of-dev polyglot monorepo would bury it and complicate independent installs/versioning.
- **Source**: user

## D4: Demo/downstream servers
- **Decision**: The build's demo aggregates day-08-docs-mcp and day-09-cached-weather-mcp (already-built, real MCP servers from this repo) as the downstream servers being routed to, rather than a fabricated tool catalog.
- **Why**: Real, working tools give an honest demo (no faked catalog), and it's a natural callback to earlier days in the challenge — proves the router works against genuine MCP servers, not toy examples.
- **Source**: user

## D5: Distribution shape
- **Decision**: Primary deliverable is a standalone MCP server usable by any MCP client (Claude Desktop, Claude Code, Cursor, etc.). A thin Claude Code plugin manifest wraps it on top for a one-command install specifically in Claude Code.
- **Why**: Standalone MCP server maximizes audience/star potential; the Claude Code plugin wrapper is near-zero extra cost since Claude Code plugins can bundle an MCP server (precedent: day-11-audited-agent), and taps a second, currently-hyped ecosystem for free.
- **Source**: user
