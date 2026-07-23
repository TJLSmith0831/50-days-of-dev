# ACP Agent — Demo Brief

**Hook:** Three independent LLM agents (researcher, writer, critic) sit behind one ACP server. A CLI that has never seen their code discovers them over REST, chains researcher → writer → critic, and prints the live hand-off.

---

## What it proves

1. **Discovery, not hardcoding** — the CLI doesn't know "researcher" and "writer" exist until it calls `GET /agents`. Add or rename an agent on the server and the CLI adapts without a code change.
2. **Framework-agnostic hand-off** — the CLI speaks ACP's REST protocol (`acp-sdk`), the agents are built with a different stack (BeeAI's `ReActAgent`). Neither side imports the other's code; the wire format is the contract.
3. **A real chain, not a mock** — each stage is a live gpt-4.1-mini call. The researcher actually searches DuckDuckGo; the writer drafts from *that* researcher's output; the critic reviews *that* draft. Output changes with the topic because nothing is scripted.

---

## What is ACP? (10–15s definition beat)

> "The **Agent Communication Protocol (ACP)** is an open protocol for agent interoperability that solves the growing challenge of connecting AI agents, applications, and humans."
>
> — [agentcommunicationprotocol.dev/introduction/welcome](https://agentcommunicationprotocol.dev/introduction/welcome)

Plain English:

- MCP standardizes agent → tool (an agent calling a search API, a file reader). ACP standardizes agent → agent — one agent's *output* becoming another agent's *input*, over plain REST instead of a custom in-process handoff.
- No SDK required to talk to an ACP server — it's HTTP. `curl http://localhost:8000/agents` lists what's available; `POST /runs` invokes one. The SDK (used here) just adds typed serialization and streaming on top.
- Framework-agnostic by design: the three agents here are BeeAI ReAct agents, but a LangChain or CrewAI agent exposed via ACP would be invoked by this exact same CLI, unmodified.
- ACP itself is IBM/BeeAI's open-source project; it has since migrated into the Linux Foundation's A2A effort, but BeeAI's ACP integration (used in this build) still works standalone and is the most direct on-ramp for a demo.

**Sources:**
- ACP welcome/introduction: https://agentcommunicationprotocol.dev/introduction/welcome
- Further background: [RESEARCH.md](RESEARCH.md), [CONTEXT.md](CONTEXT.md) (glossary: Agent, Server, Client, Manifest, Discovery, Message, MessagePart, Run)

---

## Setup

```bash
cd day-12-acp
uv sync
uv run server.py    # Terminal 1 — ACP server, registers researcher/writer/critic on :8000
```

```bash
cd day-12-acp
uv run cli.py "research and write about quantum computing"   # Terminal 2 — CLI orchestrator
```

Requires `OPENAI_API_KEY` in `day-12-acp/.env` (already configured; agents run on gpt-4.1-mini).

---

## Pre-recording workflow

**Step 1 — Test inputs without recording.**

1. Start `uv run server.py`, confirm `curl http://127.0.0.1:8000/agents` lists all three agents.
2. Run `uv run cli.py "<topic>"` manually end to end.
3. Confirm: agents discovered → `[researcher]` fires and returns prose (not one-word-per-line — that was a real bug in `extract_text_from_messages`, fixed and covered by `tests/test_workflow.py`) → `[writer]` fires using the researcher's actual output → `[critic]` fires using the writer's actual output → `=== Final Report ===` prints all three.
4. If any stage prints empty, errors, or the report reads token-by-token — **stop and do not record**. Diagnose first (stale server, missing API key, a regression in the join logic).

**Step 2 — Record the terminal demo.**

Once Step 1 passes cleanly on a dry run, start recording.

**Step 3 — Create the Remotion video.**

Composite the ACP definition animated intro (agent ↔ ACP server ↔ agent, REST arrows) with the terminal recording.

---

## Demo scenario

Terminal 1 already running `server.py` off-camera (or shown briefly starting up). On camera:

```bash
uv run cli.py "research and write a short note about the history of chess"
```

Pick a topic the researcher can actually find current material on — avoid anything requiring private/local data, since the researcher's only tool is DuckDuckGo search.

---

## Shot list (~45–55s)

### Remotion intro (10–15s)
1. **ACP concept (10–15s):** animated diagram — three boxes (Researcher, Writer, Critic) inside one ACP Server box, a CLI box outside making `GET /agents` then `POST /runs` calls with arrows showing output-becomes-input chaining. Caption pulls from the agentcommunicationprotocol.dev quote above.

### Terminal demo (30–40s)
2. **Server up (5s):** `uv run server.py` output, three agents registered. Caption: *one server, three independently built agents.*
3. **Discovery (5s):** CLI's `Discovered agents: researcher, writer, critic` line. Caption: *the CLI asked — it wasn't told.*
4. **Researcher stage (10s):** `[researcher]` output streaming in, real search-grounded findings. Caption: *stage 1 — real web search, real findings.*
5. **Writer → Critic hand-off (10s):** `[writer]` output visibly building on the researcher's specific findings, then `[critic]` output referencing the writer's specific draft. Caption: *each stage's output is the next stage's input — over HTTP.*
6. **Final Report (10s):** the `=== Final Report ===` block, all three outputs stacked. Caption: *one CLI, three agents, zero shared code.*

---

## What NOT to demo

- `curl` calls alone without the CLI — proves the protocol is plain REST, but skips the actual payoff (chaining + discovery).
- A topic vague enough that the writer/critic outputs could plausibly be templated (undermines "each stage's output" claim) — pick something with concrete, checkable facts.
- The retry-on-failure path (`day12_acp.py`'s single retry) — real but not visually interesting; mention it in prose, don't stage a failure on camera.
- The test suite (`pytest`) — proves the pipeline logic in isolation, not the live ACP round-trip that's the actual story.

---

## Frame

- Two terminals or a split pane — server log to one side (quiet, just confirms it's alive), CLI output as the main focus.
- Let each `[stage]` block finish printing before cutting; the chaining is only convincing if you can read each stage's specific content.
- End on the full `=== Final Report ===` held for 1–2s.

---

## LinkedIn post draft

> Three agents. Zero shared code. One protocol.
>
> Built a CLI that discovers ACP-compliant agents at runtime — no hardcoded agent list — then chains them: a researcher's live web-search findings become a writer's draft, the writer's draft becomes a critic's review. Every hand-off is a plain HTTP call.
>
> The agents are built with BeeAI's ReAct framework; the CLI only knows ACP's REST contract. Swap the agents for a different framework entirely and the CLI wouldn't notice — that's the point of agent-to-agent interoperability.
>
> Day 12 of 50 — ACP (Agent Communication Protocol). #AIEngineering #AgentInteroperability #ACP

---

## Checks before recording

1. `uv run pytest -q` — 7 tests green (pipeline logic, discovery, retry, report formatting, token-join fix)
2. `uv run server.py` then `curl http://127.0.0.1:8000/agents` — all three agents listed
3. `uv run cli.py "<topic>"` dry run — discovery line, three `[stage]` blocks with real prose (not one word per line), final report prints
4. Confirm `.env` has a valid `OPENAI_API_KEY` before recording — a bad key fails silently deep in the ReAct loop, not at startup
