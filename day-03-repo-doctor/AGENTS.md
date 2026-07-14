# Day 03 — Repo Doctor — AGENTS.md
Diagnoses and repairs wiring-only failures in Python repositories with Claude Agent SDK guardrails and a verified Rich report.

## Stack
Python · Claude Agent SDK 0.2.x · Rich · python-dotenv · hosted Claude API (required because this day teaches SDK agent-loop configuration)

## Commands
- `uv sync`
- `uv run --project . python main.py ./sandbox`
- `PYTHONPATH=. uv run pytest tests/test_main.py -q`
- `uv run --project . python sdk_smoke.py`

## Concept
The doctor exercises a diagnose → edit → re-run loop while constraining tools, paths, shell commands, and cost. It treats dependency installation plus a successful smoke invocation as green, then reports the verdict, attempts, diff, and verified commands.

## Gotchas
- The Claude Code `claude` CLI must be installed separately and available on `PATH`.
- The SDK smoke test requires a real `ANTHROPIC_API_KEY` in `.env`.
- The monorepo's uv workspace resolves relative script paths from the workspace root; use `uv run --project . python main.py ...` from this directory.
- `.env` files must never be read or printed by assistants, and real API keys must never be committed.
