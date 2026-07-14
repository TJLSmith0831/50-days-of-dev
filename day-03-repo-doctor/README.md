# Day 03 — Repo Doctor

A guardrailed Claude Agent SDK CLI that repairs wiring-only failures in a Python repository and proves the result with install + smoke checks.

## Demo

From this directory:

```bash
uv sync
uv run --project . python main.py ./sandbox
```

The committed `sandbox/` fixture imports `emoji` without declaring it. Repo Doctor can add the missing dependency, rerun the smoke command, and render a Rich report.

A live `ANTHROPIC_API_KEY` is required in `.env`; copy `.env.example` and add it manually. Never commit `.env`.

## Other checks

```bash
PYTHONPATH=. uv run pytest tests/test_main.py -q
uv run --project . python sdk_smoke.py
```

## Sample report

```text
╭──────────────────── Repo Doctor ────────────────────╮
│ FIXED                                                │
│ Added the missing dependency and verified the smoke │
│ command.                                             │
╰──────────────────────────────────────────────────────╯
Attempt log
  Turn  Tool   Input                         Result
  1     Bash   uv sync                       exited 0
  2     Bash   uv run python -c "import...   exited 0
Changes
  pyproject.toml adds emoji
Verified commands
  uv sync                                      0  green
  uv run python -c "import sandbox"           0  green
```
