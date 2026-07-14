## ADDED Requirements

### Requirement: CLI accepts and validates a target repo path
The CLI SHALL accept a target repo path as its first positional argument and exit with a clear, human-readable error if the path does not exist or is not a directory.

#### Scenario: Missing target argument
- **WHEN** the user runs `uv run main.py` without a target argument
- **THEN** the CLI prints a usage error and exits with a non-zero status

#### Scenario: Non-existent target
- **WHEN** the user runs `uv run main.py /path/that/does/not/exist`
- **THEN** the CLI prints "Path not found" and exits with a non-zero status

### Requirement: Detect Python projects
The system SHALL inspect the target directory for the presence of `pyproject.toml` or `requirements.txt`. If neither is present, it SHALL print a polite defer message and exit with status 0 without invoking the SDK agent.

#### Scenario: Python project detected
- **WHEN** the target directory contains `pyproject.toml`
- **THEN** the doctor proceeds to the SDK agent loop

#### Scenario: Non-Python project deferred
- **WHEN** the target directory contains neither `pyproject.toml` nor `requirements.txt`
- **THEN** the CLI prints a defer message and exits with status 0

### Requirement: Configure the SDK agent loop
The system SHALL invoke the Claude Agent SDK with `cwd` set to the absolute path of the target repo, a system prompt containing the doctor behavior and guardrail rules, a `max_turns` limit, and a tool/guardrail configuration that exposes only the intended repair tools.

#### Scenario: Agent starts in target directory
- **WHEN** the doctor begins the agent loop
- **THEN** `ClaudeAgentOptions.cwd` equals the target repo's absolute path and the system prompt includes the install→smoke→classify→fix→verify instructions

### Requirement: Enforce edit scoping and blocklist via PreToolUse hook
The system SHALL register a `PreToolUse` hook that denies any `Edit` or `Write` whose resolved file path is outside the target repo or matches the blocklist (`uv.lock`, `pnpm-lock.yaml`, `*.lock`, `.venv`, `node_modules`, `.git`, and any file under those directories).

#### Scenario: Edit outside target repo rejected
- **WHEN** the agent attempts to `Edit` a file at `/etc/passwd`
- **THEN** the `PreToolUse` hook denies the call and the attempt log records the denial

#### Scenario: Edit lockfile rejected
- **WHEN** the agent attempts to `Edit` `uv.lock` inside the target repo
- **THEN** the `PreToolUse` hook denies the call

### Requirement: Enforce bash whitelist via PreToolUse hook
The system SHALL register a `PreToolUse` hook that denies any `Bash` command whose top-level executable or subcommand is not on the whitelist (`uv`, `python`, `git` (only `status` and `diff`), `ls`, `cat`), or that contains dangerous shell constructs (`rm -rf`, `curl | sh`, `git push`, `git commit`, `sudo`, `mkfs`, `dd if=`, `bash -c`, `python -c` with dangerous imports, or paths outside the target repo).

#### Scenario: Whitelisted install command allowed
- **WHEN** the agent attempts `Bash` with command `uv sync`
- **THEN** the `PreToolUse` hook allows the call

#### Scenario: Dangerous command rejected
- **WHEN** the agent attempts `Bash` with command `rm -rf .venv`
- **THEN** the `PreToolUse` hook denies the call

#### Scenario: Git commit rejected
- **WHEN** the agent attempts `Bash` with command `git commit -m "fix"`
- **THEN** the `PreToolUse` hook denies the call

### Requirement: Limit the agent toolset
The system SHALL prevent the agent from invoking tools other than `Bash`, `Read`, `Grep`, and `Edit` by using the SDK's `tools` option (`tools=["Bash", "Read", "Grep", "Edit"]`). A `PreToolUse` hook SHALL deny any tool call that somehow bypasses the `tools` restriction.

#### Scenario: Disallowed tool rejected
- **WHEN** the agent attempts to call `WebSearch` or `Write`
- **THEN** the call is denied before execution

### Requirement: Cap the agent loop
The system SHALL set `max_turns` to a configured limit (default 10) and terminate the agent loop when that limit is reached.

#### Scenario: Max turns reached
- **WHEN** the agent loop reaches `MAX_TURNS` without achieving green
- **THEN** the doctor terminates and reports `GAVE-UP`

### Requirement: Define the green check
The system SHALL consider the repair successful when a dependency install command exits 0 and a smoke invocation exits 0. The smoke invocation SHALL be either `python -c "import <entry>"` or `<cmd> --help`, where `<entry>` and `<cmd>` are automatically discovered from `pyproject.toml` metadata and console scripts, with a `--smoke` CLI flag available as an override.

#### Scenario: Install and smoke both succeed
- **WHEN** `uv sync` exits 0 and `python -c "import sandbox"` exits 0
- **THEN** the system sets the verdict to `FIXED`

#### Scenario: Smoke fails after successful install
- **WHEN** the install command exits 0 but the smoke invocation crashes
- **THEN** the agent attempts a wiring fix and re-verifies, or the doctor reports `GAVE-UP` after `MAX_TURNS`

### Requirement: Restrict fixes to wiring failures
The system prompt SHALL instruct the agent to fix only wiring (dependencies, imports, and configuration/versions) and to classify environment or prerequisite failures as `env/prereq` and stop, reporting `ENV-BLOCKED`.

#### Scenario: Environment failure reported
- **WHEN** the agent determines a failure is caused by an environment or prerequisite issue (e.g., wrong Python version, missing system library)
- **THEN** it stops and reports `ENV-BLOCKED` with remediation text

### Requirement: Extract verdict via structured output
The system SHALL configure the SDK's `output_format` with a JSON schema for the verdict and read `ResultMessage.structured_output` to extract the final verdict (`FIXED`, `ENV-BLOCKED`, or `GAVE-UP`) instead of parsing free-form agent text.

### Requirement: Emit a rich outcome report
The system SHALL emit a rich terminal report containing the verdict (`FIXED`, `ENV-BLOCKED`, or `GAVE-UP`), a chronological attempt log, a `git diff` of tracked changes in the target repo, and the verified command sequence that produced the green check.

#### Scenario: Green report
- **WHEN** the repair is `FIXED`
- **THEN** the report includes the `FIXED` verdict, attempt log, `git diff`, and the list of successful commands

### Requirement: Prevent cheating and unsafe mutations
The system SHALL never allow git commit or push, never allow edits whose sole purpose is to bypass the smoke check, and never allow deletion or gutting of source logic.

#### Scenario: Commit attempt blocked
- **WHEN** the agent attempts `git commit` or `git push`
- **THEN** the bash whitelist denies the command

### Requirement: Provide a deliberately broken sandbox fixture
The `sandbox/` fixture SHALL be a minimal Python repo that is missing a dependency declaration, so that running Repo Doctor on it demonstrates a full install→fix→smoke-green flow.

#### Scenario: Sandbox fails before doctor runs
- **WHEN** `uv run python -c "import sandbox"` is executed on a fresh checkout
- **THEN** it fails due to a missing dependency

#### Scenario: Sandbox is healed
- **WHEN** Repo Doctor completes on `sandbox/`
- **THEN** `uv run python -c "import sandbox"` succeeds and `pyproject.toml` declares the missing dependency
