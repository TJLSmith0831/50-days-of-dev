"""Claude Code headless API integration for opsx:apply handoff."""

from __future__ import annotations

import subprocess
import time
from threading import Thread
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()

load_dotenv()

# ponytail: single source of truth for the handoff model — the CLI's bare
# default can silently resolve to a model with no credits (e.g. Fable 5),
# while named aliases like "sonnet"/"opus" don't. Both the probe and the
# real call must use the SAME model or the probe can pass while the real
# call fails, exactly as happened once already.
HANDOFF_MODEL = "sonnet"

def check_claude_code_available() -> bool:
    """Check if the `claude` CLI is installed and callable.

    Auth (OAuth via `claude login` or ANTHROPIC_API_KEY) is left for the CLI
    itself to enforce at invocation time.

    :return: True if `claude --version` succeeds
    """
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_claude_code_working() -> tuple[bool, str]:
    """End-to-end probe that catches auth/credit failures — a real one-token
    round trip through the `claude` CLI. Only used from --self-check because
    it costs a token per call and adds ~2s of latency.

    :return: (ok, message). ok=False message is the error to surface.
    """
    if not check_claude_code_available():
        return False, "claude CLI not on PATH"
    try:
        r = subprocess.run(
            ["claude", "--print", "--model", HANDOFF_MODEL, "Reply with exactly: ok"],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "claude --print timed out (>60s)"
    out = (r.stdout + r.stderr).strip()
    # ponytail: substring match on the "credits required" and "auth" text —
    # cheaper than parsing --output-format=json, catches both known failures
    low = out.lower()
    if "credits are required" in low or "usage credits" in low:
        return False, "auth OK but no credits — top up before /handoff"
    if r.returncode != 0 or "not authenticated" in low or "please log in" in low:
        return False, f"claude auth failed: {out[:200]}"
    return True, "claude --print round trip succeeded"


VALID_MODES = {"acceptEdits", "bypassPermissions"}


def handoff_to_claude_code(
    change_name: str, repo_root: str, mode: str = "acceptEdits"
) -> Optional[str]:
    """Call Claude Code headless to run opsx:apply on a change.

    :param change_name: OpenSpec change name
    :param repo_root: Repository root path
    :param mode: Claude Code permission mode. "acceptEdits" (default) lets the
        session write/edit files but still prompts for Bash — headless will deny
        anything not auto-approved. "bypassPermissions" runs with no gates
        (equivalent to --dangerously-skip-permissions); largest blast radius.
    :return: Claude Code output or None on failure
    """
    if mode not in VALID_MODES:
        return f"error: invalid mode {mode!r} (choose from {sorted(VALID_MODES)})"

    if not check_claude_code_available():
        console.print(
            Panel(
                "[red]Claude Code not available.[/red] "
                "Install it and set ANTHROPIC_API_KEY.\n\n"
                "[yellow]Manual fallback:[/yellow]\n"
                f"  cd {repo_root}\n"
                f"  openspec instructions apply --change {change_name}\n"
                f"  # Then use your AI assistant to implement the tasks",
                title="Handoff Failed",
                border_style="red",
            )
        )
        return None

    # ponytail: `claude --print` buffers plain-text stdout when piped, so real
    # streaming would require --output-format=stream-json + JSON parsing. Not
    # worth it — a spinner + elapsed timer gives liveness feedback for cheap.
    argv = [
        "claude", "--print", "--model", HANDOFF_MODEL, "--permission-mode", mode,
        f"Run opsx:apply for change '{change_name}' in {repo_root}. "
        "Follow the tasks.md checklist and implement all pending items.",
    ]
    box: dict = {}

    def _run():
        try:
            box["result"] = subprocess.run(
                argv, capture_output=True, text=True, timeout=600, cwd=repo_root,
            )
        except subprocess.TimeoutExpired:
            box["error"] = "error: Claude Code timed out (10 min limit)"
        except FileNotFoundError:
            box["error"] = "error: claude CLI not found"

    t = Thread(target=_run, daemon=True)
    t.start()
    start = time.time()
    # ponytail: 5s updates, not 1s — sub-5s gaps defeat asciinema idle-trim and
    # bloat demo captures (a 3-min run becomes ~36s of screen time at 1s ticks)
    with console.status(f"[cyan]Claude Code running (mode={mode})... 0s[/cyan]") as status:
        while t.is_alive():
            status.update(f"[cyan]Claude Code running (mode={mode})... {int(time.time()-start)}s[/cyan]")
            time.sleep(10)
    t.join()

    if "error" in box:
        return box["error"]
    r = box["result"]
    return (r.stdout + r.stderr).strip() or "(no output)"


def manual_fallback_instructions(change_name: str, repo_root: str) -> str:
    """Return manual opsx:apply instructions as a string.

    :param change_name: OpenSpec change name
    :param repo_root: Repository root path
    :return: Instruction text
    """
    return (
        f"Manual opsx:apply fallback:\n"
        f"  1. cd {repo_root}\n"
        f"  2. openspec instructions apply --change {change_name}\n"
        f"  3. Use your AI assistant to implement the pending tasks\n"
        f"  4. Mark tasks complete in tasks.md as you go"
    )
