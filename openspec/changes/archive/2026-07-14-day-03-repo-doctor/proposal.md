# Day 3 — Repo Doctor Proposal

## Why

Day 3 of the 50-days-of-dev challenge is meant to exercise the **Claude Agent SDK's diagnose→edit→re-run loop** under explicit permission guardrails. We will build a small CLI, "Repo Doctor," that points Claude at a broken Python repo and lets it repair wiring (deps/imports/config) it is allowed to touch, then hand back a verified green report — or an honest "this part's on you." This makes the lesson concrete: the value is in *configuring and constraining* the agent, not reimplementing the agent loop.

## What Changes

- Add `day-03-repo-doctor/` as a self-contained Python day project.
- Implement `main.py`: CLI target-path parsing, Python-repo detection, SDK agent loop with guardrails, green smoke check, and a rich terminal report.
- Implement a strict `PreToolUse` hook plus a `can_use_tool` fallback to enforce folder scoping, bash whitelisting, blocklist (`uv.lock`, `.venv`, `.git`, lockfiles), and a turn cap.
- Add `sandbox/`, a deliberately broken Python fixture repo used for the end-to-end demo.
- Add `pyproject.toml`, `AGENTS.md`, `README.md`, and a `.env.example` (API key placeholder).
- Leave Node/non-Python repos untouched with a polite defer message.

## Capabilities

### New Capabilities

- `repo-doctor`: Accept a target repo path, detect whether it is Python, run a guardrailed Claude Agent SDK loop to install dependencies and smoke-invoke the project, repair wiring-only failures, and emit a verdict + diff + verified steps.

### Modified Capabilities

None.

## Impact

- Introduces the first paid-API day in the challenge (`ANTHROPIC_API_KEY` required).
- Adds `claude-agent-sdk`, `rich`, and `python-dotenv` as project-level dependencies.
- Creates a committed `sandbox/` fixture with a deliberately broken `pyproject.toml` for the demo.
- No changes to existing days or root workspace configuration.
