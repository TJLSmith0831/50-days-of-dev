import argparse
import asyncio
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    HookMatcher,
    PermissionResultDeny,
    ResultMessage,
    query,
)
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

ALLOWED_TOOLS = {"Bash", "Read", "Grep", "Edit"}
# The SDK exposes structured output (the verdict) as a tool call; it isn't a repo
# action, so it bypasses the repo guardrails but must be permitted to run.
STRUCTURED_OUTPUT_TOOL = "StructuredOutput"
MAX_TURNS = 10
MAX_BUDGET_USD = 1.50
BLOCKED_PARTS = {".venv", "node_modules", ".git"}
BLOCKED_NAMES = {"uv.lock", "pnpm-lock.yaml"}
SHELL_METACHARACTERS = {"|", ";", "&", "`", "<", ">"}
DANGEROUS_PYTHON_IMPORTS = {
    "os",
    "pathlib",
    "shutil",
    "subprocess",
    "socket",
    "requests",
    "urllib",
}
VERDICT_STYLES = {
    "FIXED": "bold green",
    "ENV-BLOCKED": "bold yellow",
    "GAVE-UP": "bold red",
}


@dataclass
class Attempt:
    """
    One tool call the agent made (or was denied), for the attempt log.
    """

    turn: int
    tool: str
    input_summary: str
    result: str
    allowed: bool = True


@dataclass
class Verification:
    """
    The result of an external (non-agent) install or smoke command run.
    """

    command: str
    returncode: int
    output: str


@dataclass
class DoctorState:
    """
    Mutable record of one Repo Doctor run: target repo, attempts, verifications.
    """

    target: Path
    attempts: list[Attempt] = field(default_factory=list)
    verified: list[Verification] = field(default_factory=list)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse the target repository path and optional smoke command override.
    """
    parser = argparse.ArgumentParser(
        description="Diagnose and repair wiring-only failures in a Python repository."
    )
    parser.add_argument("target", type=Path, help="Path to the target repository")
    parser.add_argument(
        "--smoke",
        help="Override the automatically discovered smoke command, such as 'python -c \"import app\"'",
    )
    return parser.parse_args(argv)


def validate_target(target: Path) -> Path:
    """
    Resolve the target path and confirm it exists and is a directory.
    """
    resolved = target.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Path not found: {target}")
    if not resolved.is_dir():
        raise ValueError(f"Target is not a directory: {target}")
    return resolved


def is_python_project(target: Path) -> bool:
    """
    Check whether the target looks like a Python project Repo Doctor can handle.
    """
    return (target / "pyproject.toml").is_file() or (target / "requirements.txt").is_file()


def _project_metadata(target: Path) -> dict[str, Any]:
    """
    Load `pyproject.toml` as a dict, or `{}` if it's missing or malformed.
    """
    pyproject = target / "pyproject.toml"
    if not pyproject.is_file():
        return {}
    try:
        with pyproject.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _import_name(value: str) -> str:
    """
    Convert a package/project name (e.g. `sample-app`) into an import name.
    """
    return value.replace("-", "_").replace(" ", "_")


def discover_smoke_command(target: Path) -> str:
    """
    Pick a smoke command: a declared console script's `--help`, else `import <pkg>`.
    """
    metadata = _project_metadata(target)
    project = metadata.get("project", {})
    scripts = project.get("scripts", {})
    if scripts:
        script_name = next(iter(scripts))
        return f"{script_name} --help"
    project_name = project.get("name")
    package_name = _import_name(project_name or target.name)
    return f'python -c "import {package_name}"'


def build_smoke_command(command: str) -> str:
    """
    Validate a smoke command against the same whitelist as agent Bash calls.
    """
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"Invalid smoke command: {exc}") from exc
    if not parts or any(part in SHELL_METACHARACTERS for part in parts):
        raise ValueError("Smoke command must be a single whitelisted command")
    error = validate_bash_command(Path.cwd(), command, check_paths=False)
    if error:
        raise ValueError(error)
    return command


def _path_is_blocked(target: Path, candidate: Path) -> bool:
    """
    Check a resolved, in-repo path against the lockfile/venv/git blocklist.
    """
    relative = candidate.relative_to(target)
    if candidate.name in BLOCKED_NAMES or candidate.suffix == ".lock":
        return True
    return any(part in BLOCKED_PARTS for part in relative.parts)


def validate_edit_path(target: Path, raw_path: str) -> str | None:
    """
    Return a denial reason if an Edit path escapes the repo or hits the blocklist, else None.
    """
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = target / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(target)
    except ValueError:
        return "Edit denied: path is outside the target repository"
    if _path_is_blocked(target, candidate):
        return "Edit denied: path is protected by the blocklist"
    return None


def _contains_outside_path(target: Path, parts: list[str]) -> bool:
    """
    Check whether any path-like argument resolves outside the target repo.
    """
    for part in parts:
        if not part or part.startswith("-") or part in {"-c", "--"}:
            continue
        if "/" not in part and not part.startswith("."):
            continue
        candidate = Path(part).expanduser()
        if not candidate.is_absolute():
            candidate = target / candidate
        try:
            candidate.resolve().relative_to(target)
        except ValueError:
            return True
    return False


def _python_code_is_safe(code: str) -> bool:
    """
    Reject `python -c` code that touches the filesystem, network, or eval/exec.
    """
    lowered = code.lower()
    if any(token in lowered for token in ("__import__", "eval(", "exec(", "open(")):
        return False
    return not any(
        f"import {name}" in lowered or f"from {name} " in lowered
        for name in DANGEROUS_PYTHON_IMPORTS
    )


def validate_bash_command(
    target: Path, command: str, *, check_paths: bool = True
) -> str | None:
    """
    Return a denial reason if a Bash command violates the guardrails, else None.
    """
    if any(character in command for character in SHELL_METACHARACTERS):
        return "Bash denied: shell metacharacters are not permitted"
    if "$(" in command or "bash -c" in command or "sh -c" in command:
        return "Bash denied: nested shell commands are not permitted"
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"Bash denied: invalid shell syntax ({exc})"
    if not parts:
        return "Bash denied: empty command"
    executable = Path(parts[0]).name
    if executable not in {"uv", "python", "python3", "git", "ls", "cat"}:
        if not (len(parts) == 2 and parts[1] == "--help" and executable.replace("-", "").replace("_", "").replace(".", "").isalnum()):
            return f"Bash denied: '{executable}' is not on the whitelist"
    if executable == "git" and (len(parts) < 2 or parts[1] not in {"status", "diff"}):
        return "Bash denied: only git status and git diff are permitted"
    if executable == "uv" and (len(parts) < 2 or parts[1] not in {"sync", "run"}):
        return "Bash denied: only uv sync and uv run are permitted"
    if executable in {"python", "python3"} and "-c" in parts:
        code = parts[parts.index("-c") + 1] if parts.index("-c") + 1 < len(parts) else ""
        if not _python_code_is_safe(code):
            return "Bash denied: unsafe Python code"
    if any(token in {"sudo", "mkfs", "dd", "rm", "curl", "wget"} for token in parts):
        return "Bash denied: destructive or network commands are not permitted"
    if check_paths and _contains_outside_path(target, parts[1:]):
        return "Bash denied: command references a path outside the target repository"
    return None


def _summarize(value: Any, limit: int = 160) -> str:
    """
    Stringify and truncate a value for display, redacting the API key.
    """
    text = str(value).replace("ANTHROPIC_API_KEY", "[REDACTED]")
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


def _print_attempt(console: Console, attempt: Attempt) -> None:
    """
    Stream one tool call to the console as it happens (green allow, red deny).
    """
    icon, style = ("✓", "green") if attempt.allowed else ("✗", "red")
    detail = attempt.input_summary if attempt.allowed else attempt.result
    console.print(f"  [{style}]{icon}[/] [bold]{attempt.tool:<5}[/] {detail}")


def _hook_output(decision: str, reason: str) -> dict[str, Any]:
    """
    Build a PreToolUse hook response with the given allow/deny decision.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }


def make_pre_tool_hook(state: DoctorState, console: Console):
    """
    Build the PreToolUse hook that enforces the tool/path/command whitelist, logs denials, and streams them live.
    """

    async def pre_tool_use(input_data: Any, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        tool_name = input_data["tool_name"]
        # StructuredOutput is the SDK's verdict-submission channel, not a repo
        # action — let it through so the agent can report its verdict.
        if tool_name == STRUCTURED_OUTPUT_TOOL:
            return _hook_output("allow", "Verdict submission")
        tool_input = input_data.get("tool_input") or {}
        reason: str | None = None
        if tool_name not in ALLOWED_TOOLS:
            reason = f"Tool '{tool_name}' is not permitted"
        elif tool_name == "Bash":
            reason = validate_bash_command(state.target, str(tool_input.get("command", "")))
        elif tool_name == "Edit":
            path = tool_input.get("file_path") or tool_input.get("path")
            reason = "Edit denied: missing file path" if not path else validate_edit_path(state.target, str(path))
        if reason:
            attempt = Attempt(len(state.attempts) + 1, tool_name, _summarize(tool_input), reason, False)
            state.attempts.append(attempt)
            _print_attempt(console, attempt)
            return _hook_output("deny", reason)
        return _hook_output("allow", "Allowed by Repo Doctor guardrails")

    return pre_tool_use


def make_post_tool_hook(state: DoctorState, console: Console):
    """
    Build the PostToolUse hook that records every allowed call in the attempt log and streams it live.
    """

    async def post_tool_use(input_data: Any, tool_use_id: str | None, context: Any) -> dict[str, Any]:
        if input_data["tool_name"] == STRUCTURED_OUTPUT_TOOL:
            return {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}
        attempt = Attempt(
            len(state.attempts) + 1,
            input_data["tool_name"],
            _summarize(input_data.get("tool_input")),
            _summarize(input_data.get("tool_response")),
        )
        state.attempts.append(attempt)
        _print_attempt(console, attempt)
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse"}}

    return post_tool_use


async def deny_unexpected_tool(tool_name: str, input_data: dict[str, Any], context: Any):
    """
    Fallback `can_use_tool` callback: deny any tool call outside the allowed set.
    """
    return PermissionResultDeny(f"Tool '{tool_name}' denied by Repo Doctor")


SYSTEM_PROMPT = """You are Repo Doctor. Work only inside the target repository.

Follow this sequence: install dependencies with the exact target-scoped uv command provided in the
user prompt, run the discovered smoke command, classify the failure as config/code or env/prereq,
fix only wiring failures, then reinstall and rerun the smoke command. Wiring fixes include dependency
declarations, imports, and configuration or version constraints. Do not change business logic, gut
source files, bypass the smoke check, commit, push, delete files, or install system-level dependencies.
If the failure is an environment or prerequisite problem, stop and return ENV-BLOCKED with a concise
remediation. If the repair is not green within the turn limit, return GAVE-UP. Finish with the
structured verdict.
"""


VERDICT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["FIXED", "ENV-BLOCKED", "GAVE-UP"]},
            "summary": {"type": "string"},
        },
        "required": ["verdict", "summary"],
        "additionalProperties": False,
    },
}


async def run_agent(state: DoctorState, smoke_command: str, console: Console) -> tuple[str, str]:
    """
    Run the diagnose-fix-reverify agent loop and return its (verdict, summary).
    """
    project = shlex.quote(str(state.target))
    install_command = f"uv sync --project {project}"
    smoke_run = f"uv run --project {project} {smoke_command}"
    prompt = (
        f"Target repository: {state.target}\n"
        f"Target-scoped install command: {install_command}\n"
        f"Target-scoped smoke command: {smoke_run}\n"
        "Begin by running those exact commands."
    )
    async def prompt_stream():
        yield {
            "type": "user",
            "message": {"role": "user", "content": prompt},
        }

    options = ClaudeAgentOptions(
        cwd=state.target,
        system_prompt=SYSTEM_PROMPT,
        tools=sorted(ALLOWED_TOOLS),
        allowed_tools=sorted(ALLOWED_TOOLS) + [STRUCTURED_OUTPUT_TOOL],
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        can_use_tool=deny_unexpected_tool,
        hooks={
            "PreToolUse": [HookMatcher(matcher=None, hooks=[make_pre_tool_hook(state, console)])],
            "PostToolUse": [HookMatcher(matcher=None, hooks=[make_post_tool_hook(state, console)])],
        },
        output_format=VERDICT_SCHEMA,
    )
    final_verdict = "GAVE-UP"
    summary = "The agent did not return a structured verdict."
    async for message in query(prompt=prompt_stream(), options=options):
        if isinstance(message, ResultMessage):
            structured = message.structured_output or {}
            candidate = structured.get("verdict") if isinstance(structured, dict) else None
            if candidate in VERDICT_STYLES:
                final_verdict = candidate
            if isinstance(structured, dict) and structured.get("summary"):
                summary = str(structured["summary"])
            elif message.result:
                summary = _summarize(message.result, 500)
    return final_verdict, summary


def run_command(target: Path, command: str) -> Verification:
    """
    Run a shell command in the target repo and capture its outcome.
    """
    result = subprocess.run(
        shlex.split(command),
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    return Verification(command, result.returncode, output)


def verify_green(state: DoctorState, smoke_command: str) -> bool:
    """
    Independently re-run install + smoke outside the agent to confirm the repair.
    """
    project = shlex.quote(str(state.target))
    install = run_command(state.target, f"uv sync --project {project}")
    state.verified.append(install)
    if install.returncode != 0:
        return False
    smoke = run_command(state.target, f"uv run --project {project} {smoke_command}")
    state.verified.append(smoke)
    return smoke.returncode == 0


def git_diff(target: Path) -> str:
    """
    Return the tracked-file diff produced by the agent's edits, if any.
    """
    result = subprocess.run(
        ["git", "diff", "--", "."],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def render_report(
    console: Console,
    state: DoctorState,
    verdict: str,
    summary: str,
    diff: str,
) -> None:
    """
    Render the verdict, attempt log, diff, and verified commands as Rich panels.
    """
    console.print(Panel(f"[{VERDICT_STYLES[verdict]}]{verdict}[/]\n{summary}", title="Repo Doctor"))
    attempts = Table(title="Attempt log")
    attempts.add_column("Turn", style="dim")
    attempts.add_column("Tool")
    attempts.add_column("Input")
    attempts.add_column("Result")
    for attempt in state.attempts:
        style = "green" if attempt.allowed else "red"
        attempts.add_row(str(attempt.turn), f"[{style}]{attempt.tool}[/]", attempt.input_summary, attempt.result)
    console.print(attempts)
    console.print(Panel(Syntax(diff or "No tracked changes.", "diff", theme="monokai", word_wrap=True), title="Changes"))
    verified = Table(title="Verified commands")
    verified.add_column("Command")
    verified.add_column("Exit code")
    verified.add_column("Status")
    for item in state.verified:
        status = "[green]✓ pass[/]" if item.returncode == 0 else "[red]✗ fail[/]"
        verified.add_row(item.command, str(item.returncode), status)
    console.print(verified)


async def main(argv: list[str] | None = None) -> int:
    """
    Diagnose the target repo, let the agent attempt a wiring fix, then verify and report.
    """
    args = parse_args(argv)
    try:
        target = validate_target(args.target)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not is_python_project(target):
        print("Repo Doctor currently supports Python repositories only; deferring without changes.")
        return 0
    load_dotenv()
    state = DoctorState(target)
    try:
        smoke_command = build_smoke_command(args.smoke or discover_smoke_command(target))
    except ValueError as exc:
        print(f"Invalid smoke command: {exc}", file=sys.stderr)
        return 2
    console = Console()
    console.rule("[bold cyan]🩺 Repo Doctor[/]")
    console.print(f"[dim]Target:[/] {target}")
    console.print(f"[dim]Smoke: [/] {smoke_command}\n")
    try:
        agent_verdict, summary = await run_agent(state, smoke_command, console)
    except Exception as exc:
        agent_verdict, summary = "ENV-BLOCKED", f"Agent unavailable: {_summarize(exc, 400)}"
    with console.status("Verifying green outside the agent..."):
        green = verify_green(state, smoke_command)
    verdict = "FIXED" if green else agent_verdict
    if verdict == "FIXED" and not green:
        verdict = "GAVE-UP"
    render_report(console, state, verdict, summary, git_diff(target))
    return 0 if verdict == "FIXED" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
