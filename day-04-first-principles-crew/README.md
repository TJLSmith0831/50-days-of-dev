# Day 04 — First-Principles Crew

Breaks a messy problem into N fundamental truths after challenging M assumptions, then reasons up to one recommendation — in T seconds, fully local. Runs as a multi-turn REPL: refine the recommendation with follow-ups, or drill into any individual fundamental to make the Physicist defend or revise it.

## Stack

Python · CrewAI (`@CrewBase`, YAML agent/task config, `Process.sequential`) · LiteLLM → Ollama (ollama/llama3.2) · Pydantic (structured task outputs) · rich (REPL + formatted agent output) · python-dotenv

## Concept

CrewAI's declarative, role-based orchestration: specialized agents whose outputs chain forward via `context=`, run as a sequential Crew. Contrast with Day 2 (explicit LangGraph state graph) and Day 3 (SDK subagent spawn) — same "multiple cooperating agents" goal, a third distinct abstraction. The first-principles method is the payload that makes the role separation meaningful.

## Project layout

Follows CrewAI's standard golden-path structure ([crewAI#getting-started](https://github.com/crewAIInc/crewAI#getting-started)):

*   `config/agents.yaml` — role/goal/backstory per agent
*   `config/tasks.yaml` — description/expected\_output/agent/context per task, with `{problem}` interpolation
*   `crew.py` — `@CrewBase` class wiring the YAML config to `Agent`/`Task` objects, plus the Ollama `LLM` and Pydantic `output_pydantic` types (things YAML can't express) and a `task_callback` that renders each agent's structured output as a readable panel instead of a raw repr/JSON dump
*   `models.py` — shared Pydantic schemas
*   `main.py` — the REPL front end

## Crew (3 agents, sequential)

*   **Skeptic** — surfaces every assumption baked into the problem statement and flags which are unfounded. → AssumptionSet
*   **Physicist** — context=\[skeptic\]; distills the irreducible truths that survive after the shaky assumptions are stripped. → FundamentalSet
*   **Builder** — context=\[skeptic, physicist\]; reconstructs a concrete recommendation using only the fundamentals. → Recommendation

## Structured Output

Tiny flat Pydantic models via output\_pydantic on each task:

*   Assumption { statement, questionable: bool, why } → AssumptionSet { assumptions: \[...\] }
*   Fundamental { truth, basis } → FundamentalSet { fundamentals: \[...\] }
*   Recommendation { recommendation, rests\_on: \[str\] }

## REPL

Always waits for input before running anything — hit Enter to accept the shown default problem, or type your own.

*   Free-text follow-up — refines the recommendation by re-running the crew with your input appended to the problem
*   `drill <n>` — re-runs just the Physicist against fundamental #n, forcing it to defend or revise that specific claim
*   `new <problem>` — starts a fresh problem
*   `exit` / `quit` — leaves the REPL

Model output on llama3.2 is flaky (structured-output parsing occasionally fails mid-run); failures are caught and print a retry prompt instead of crashing the session — see the AGENTS.md gotchas.

## Decision log

Every completed run appends a timestamped block — problem, fundamentals, recommendation — to a local `decisions.md`. It runs fully offline and is `.gitignore`d, so it's the one place you'd actually paste a real "should we fire this person / kill this feature / take this offer" question: the record stays on your disk, never a server, never the repo.

## Metric

Parsed from the objects, not the prose:

*   M = assumptions where questionable == True
*   N = len(fundamentals)
*   T = perf\_counter() around crew.kickoff()

Final line: "M assumptions challenged → N fundamentals → 1 recommendation in T s (local llama3.2)."

## Usage

```
# Install dependencies
uv sync

# Launch the REPL with a custom default problem
uv run main.py "Should we rebuild our legacy monolith as microservices?"

# Launch the REPL with the built-in example as the default
uv run main.py

# Run the offline self-check (no LLM call)
uv run main.py --demo
```

## Prerequisites

*   Ollama running with llama3.2 model: `ollama run llama3.2`
*   Ollama API accessible at http://localhost:11434