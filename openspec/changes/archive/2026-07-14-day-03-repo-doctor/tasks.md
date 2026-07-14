## 1. Scaffold and environment

- [x] 1.1 Create `day-03-repo-doctor/` folder and `pyproject.toml` with `package = false` and deps: `claude-agent-sdk`, `rich`, `python-dotenv`.
- [x] 1.2 Add `.env.example` (placeholder for `ANTHROPIC_API_KEY`) and ensure `.env`, `.venv`, and lockfiles are gitignored.
- [x] 1.3 Run `uv sync` and a `uv run python -c "print('hello')"` smoke check to confirm the environment works.
- [x] 1.4 Stub `main.py` with `async def main()` and `if __name__ == "__main__": asyncio.run(main())` so `uv run main.py ./sandbox` has an entrypoint.

## 2. API key and .env setup

- [x] 2.1 Create `.env.example` with `ANTHROPIC_API_KEY=...` and add `.env` to `.gitignore`.
- [x] 2.2 Pause: add a real `ANTHROPIC_API_KEY` to `.env` before proceeding. Do not commit `.env`.
- [x] 2.3 Update the root `AGENTS.md` with a rule: never read `.env` files; real API keys are never committed.
- [x] 2.4 Verify `python-dotenv` loads the key without `main.py` reading or printing it.

## 3. SDK smoke test

- [x] 3.1 Write a minimal SDK query that runs `ls` in a temporary directory using `ClaudeAgentOptions(allowed_tools=["Bash", "Read"], max_turns=5).
- [x] 3.2 Verify `ANTHROPIC_API_KEY` is loaded from `.env` and confirm whether the `claude` CLI binary is auto-located or needs an explicit `cli_path`.
- [x] 3.3 Confirm messages stream correctly and the query terminates without interactive prompts.

## 4. Doctor brain and guardrails

- [x] 4.1 Implement CLI argument parsing: accept a target repo path positional argument and fail cleanly if it does not exist or is not a directory.
- [x] 4.2 Implement Python-repo detection: require `pyproject.toml` or `requirements.txt`; defer politely on any other repo type.
- [x] 4.3 Implement the `PreToolUse` hook: enforce the tool allowlist (`Bash`, `Read`, `Grep`, `Edit`), edit scoping and blocklist, and bash whitelist/parser.
- [x] 4.4 Implement the `can_use_tool` fallback so any tool call that bypasses the hook is denied.
- [x] 4.5 Craft the doctor system prompt: install → smoke → classify → fix → verify; wiring-only fixes; env/prereq failures stop with `ENV-BLOCKED`.
- [x] 4.6 Wire the SDK `query()` call with `cwd=target`, the system prompt, `max_turns`, `max_budget_usd`, and the guardrail callbacks.

## 5. Green check and report

- [x] 5.1 Implement smoke-command auto-discovery from `pyproject.toml`: prefer `[project.scripts]`, then `[project.name]`, then directory name; support `--smoke` override.
- [x] 5.2 Implement the green check: a dependency install command exits 0 and a smoke invocation exits 0.
- [x] 5.3 Collect an attempt log via a `PostToolUse` hook (allowed tool, input, result summary) and capture `git diff` in the target repo.
- [x] 5.4 Render a rich terminal report with verdict (`FIXED` / `ENV-BLOCKED` / `GAVE-UP`), attempt log, diff, and the verified command sequence.
- [x] 5.5 Configure the SDK's `output_format` with a JSON schema for the verdict and read `ResultMessage.structured_output` to extract the final verdict (`FIXED` / `ENV-BLOCKED` / `GAVE-UP`).

## 6. Sandbox and demo

- [x] 6.1 Create `sandbox/` as a minimal Python package with a `pyproject.toml` that omits a required dependency but imports it in `main.py`.
- [x] 6.2 Run the Repo Doctor CLI end-to-end and verify the repaired dependency, passing smoke check, and Rich report.
- [x] 6.3 Write `day-03-repo-doctor/AGENTS.md` with stack, commands, concept, gotchas, and a clear note that `.env` files must never be read and real API keys must never be committed.
- [x] 6.4 Write `README.md` with the one-liner, demo instructions, and a sample report.

## 7. Final verification

- [x] 7.1 Run the demo from a clean state and capture the final output.
- [x] 7.2 Review `git status` to ensure only intended files are added (no `.venv`, lockfiles, or `.env` with real keys).
