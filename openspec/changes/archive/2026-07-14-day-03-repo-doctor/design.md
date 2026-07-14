# Repo Doctor — Design

## Context

Day 3 of the 50-days-of-dev challenge. Repo Doctor is a Python CLI that points the Claude Agent SDK at a broken Python repository and lets the configured agent diagnose and repair wiring-only failures (dependencies, imports, configuration, version constraints) under strict guardrails. The project is intentionally small — the lesson is configuring and constraining the SDK's agent loop, not reimplementing it.

## Goals / Non-Goals

**Goals:**

- Accept a target repo path and detect whether it is a Python project.
- Run the SDK agent with `cwd` set to the target repo.
- Enforce guardrails at the tool-call layer using a `PreToolUse` hook: folder-scoped edits, edit blocklist, bash whitelist, tool allowlist, and a turn cap.
- Define "green" as: dependency install succeeds **and** a smoke invocation exits 0.
- Render a rich report with verdict, attempt log, `git diff`, and verified commands.
- Provide a committed `sandbox/` fixture that is deliberately missing a dependency so the demo shows a full repair.

**Non-Goals:**

- Repairing non-Python repos (detect and defer politely).
- Fixing runtime logic bugs or business logic errors.
- Installing system-level dependencies or resolving environment/prerequisite failures automatically.
- Booting or port-binding as a success criterion.
- Auto-committing, pushing, or otherwise mutating the repository's git history.
- A production-grade, fully generic repair tool.

## Decisions

- **Mandatory gate: `PreToolUse` hook**  
  The SDK's `can_use_tool` callback only fires when the permission flow reaches an "ask" decision. Tools listed in `allowed_tools` are auto-approved and bypass `can_use_tool`. Therefore the strict guardrail is implemented as a `PreToolUse` hook, which runs before every tool call and can deny or modify the input. `can_use_tool` is still provided as a fallback that denies any unexpected tool request.

- **Tool restriction**  
  Only `Bash`, `Read`, `Grep`, and `Edit` are permitted. The SDK's `tools` option (`tools=["Bash", "Read", "Grep", "Edit"]`) restricts the built-in toolset directly. `allowed_tools`/`disallowed_tools` are not used for restriction; they only govern auto-approval. A `PreToolUse` hook denies any tool call that somehow bypasses the `tools` restriction.

- **Bash whitelist and parser**  
  Allowed top-level commands: `uv`, `python`, `git` (only `status` and `diff` subcommands), `ls`, `cat`. The hook parses the command with `shlex.split()` and rejects shell metacharacters that would bypass the whitelist (`|`, `;`, `&`, `$(...)`, backticks, redirection to paths outside the target, and nested interpreters such as `bash -c`). `python -c` is allowed for smoke checks but its argument is screened for dangerous imports. `uv` is the only install driver; `pip`/requirements.txt are not supported.

- **Edit scoping**  
  Every `Edit` target is resolved to an absolute path. The hook denies writes outside the target repo and any path matching the blocklist: `uv.lock`, `pnpm-lock.yaml`, `*.lock`, `.venv`, `node_modules`, `.git`, and any file under those directories.

- **Smoke detection**  
  The smoke command is discovered from `pyproject.toml`: first from `[project.scripts]`, then from `[project.name]`, then from the target directory name. If no script is declared, it falls back to `python -c "import <package_name>"`. A `--smoke` CLI flag can override this for repos that do not fit the heuristic.

- **Outcome classification**  
  The system prompt instructs the agent to classify failures as `config/code` (fixable wiring) or `env/prereq` (not fixable). If green is not reached after `MAX_TURNS`, the final verdict is `GAVE-UP`. The SDK's `output_format` with a JSON schema is used to extract the final verdict from `ResultMessage.structured_output` instead of parsing free text.

- **Cost limits**  
  `max_turns` is set to a small constant (default `10`). `max_budget_usd` is also set to a conservative cap if the SDK supports it.

- **Attempt log**  
  A `PostToolUse` hook records allowed tool invocations, their inputs, and a summary of their results. This becomes the "attempt log" in the report. The `git diff` is captured by running `git diff` in the target repo after the loop.

## CLI / Rich Design

- **Layout**  
  The final report is a single `rich` console output divided into panels: a header panel with the verdict, a compact attempt log, a syntax-highlighted diff panel, and a verified-commands panel. A `Live` view may be used during the agent loop to show the current turn and last tool, then cleared for the final report.

- **Color palette**  
  - `FIXED` — green (`bold green`)  
  - `ENV-BLOCKED` — yellow (`bold yellow`)  
  - `GAVE-UP` — red (`bold red`)  
  - Denied/blocked actions — muted red in the attempt log.  
  - Neutral metadata (turn count, command exit codes) — `dim` or `blue`.

- **Attempt log**  
  A `Table` with columns: `Turn`, `Tool`, `Input` (truncated to 80 chars), `Result`. Allowed tool calls are green; denied calls are red with the denial reason. The `Input` column uses `Text` with `overflow="ellipsis"`.

- **Diff rendering**  
  The `git diff` output is wrapped in a `Panel` titled "Changes" and rendered with `Syntax(diff_text, "diff", theme="monokai", word_wrap=True)` so added/removed lines are clearly highlighted.

- **Verified commands**  
  A `Table` or `Panel` listing each command that exited 0 during the repair, with its exit code and a short status. If the smoke command is overridden, it is marked with `*`.

- **Status / spinners**  
  During the loop, `console.status("Diagnosing...")` or `Live` shows a spinner and the current turn. On completion, the final report replaces the live view.

- **No emojis**  
  Use text labels and `rich` colors instead of emoji to keep the output portable and accessible.

- **Secrets hygiene**  
  The CLI never prints the `ANTHROPIC_API_KEY` or any `.env` contents. The `rich` console output filters tool inputs that contain `ANTHROPIC_API_KEY` or other secrets before rendering.

## Risks / Trade-offs

- **SDK API drift** — `ClaudeAgentOptions` fields such as `tools`, `allowed_tools`, `disallowed_tools`, and the hook callback signatures may differ across SDK versions. Mitigation: verify against the installed SDK before implementation and keep guardrail logic isolated in one module. Note: for `claude-agent-sdk==0.2.118`, `tools` restricts the toolset directly and `PreToolUseHookInput` carries `tool_name`, `tool_input`, `tool_use_id`, plus `session_id`/`cwd`/`transcript_path` from `BaseHookInput`.
- **Bash whitelist bypass** — Any whitelist is fragile against creative shell quoting. Mitigation: `shlex` parsing plus explicit rejection of metacharacters and nested interpreters. This is a teaching demo, not a security boundary.
- **Smoke check fragility** — Auto-detecting the import/console-script entry point may fail for unusual repo layouts. Mitigation: allow `--smoke` override and fall back to directory name.
- **Agent overreach** — The prompt can only discourage logic changes; it cannot perfectly prevent the agent from gutting code. Mitigation: the `Edit` guardrail at least blocks writes outside the repo/lockfiles, and the prompt is explicit.
- **Claude Code CLI dependency** — The `claude-agent-sdk` is a wrapper around the Claude Code CLI and may require the `claude` binary to be installed separately. Mitigation: document this in `AGENTS.md` and `README.md`; if missing, fail fast with a clear message.
- **Final verdict ambiguity** — Determining `ENV-BLOCKED` vs `GAVE-UP` from free-form agent text is imprecise. Mitigation: use the SDK's `output_format` with a JSON schema and read `ResultMessage.structured_output` instead of parsing free text.
