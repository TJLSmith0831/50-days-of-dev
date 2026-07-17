#!/usr/bin/env python3
"""SDD Writer Harness — Spec Driven Design REPL with grilling and Claude Code handoff."""

import argparse
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import ollama
from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel

from agent_loop import create_agent
from claude_code_handoff import (
    check_claude_code_available,
    check_claude_code_working,
    handoff_to_claude_code,
    manual_fallback_instructions,
)
from repl_interface import (
    confirm_handoff,
    display_help,
    display_sessions,
    display_welcome,
    expand_file_mentions,
    get_user_input,
)
from session_management import (
    DB_PATH,
    create_checkpointer,
    create_session,
    init_db,
    list_sessions,
    update_session,
)

console = Console()


def preflight_check(model: str) -> bool:
    """Check Ollama is running and the model is pulled — one /api/tags call.

    :param model: Ollama model name
    :return: True if available
    """
    try:
        tags = {m.get("model") or m.get("name") for m in ollama.list().get("models", [])}
    except Exception as e:
        console.print(
            Panel(
                f"[red]Ollama isn't responding.[/red] Start it with [cyan]ollama serve[/cyan].\n\n"
                f"[dim]{str(e)}[/dim]",
                title="Error",
                border_style="red",
            )
        )
        return False
    # Ollama tags include the tag suffix (e.g. "qwen3:14b"); match against both forms.
    if model not in tags and f"{model}:latest" not in tags:
        console.print(
            Panel(
                f"[red]Model {model} not pulled.[/red] Run [cyan]ollama pull {model}[/cyan].\n\n"
                f"[dim]available: {sorted(tags) or '(none)'}[/dim]",
                title="Error",
                border_style="red",
            )
        )
        return False
    return True


def run_repl(model: str, thread_id: str, fresh: bool = False, verbose: bool = False):
    """Run the interactive REPL session.

    :param model: Ollama model name
    :param thread_id: Thread ID for session persistence
    :param fresh: Whether to start a fresh session
    :param verbose: Whether to print debug diagnostics to stderr
    """
    if not preflight_check(model):
        return
    if not check_claude_code_available():
        console.print(
            "[yellow]⚠ Claude Code not available — /handoff will fall back to manual instructions.[/yellow]\n"
            "[dim]Install Claude Code and set ANTHROPIC_API_KEY to enable headless handoff.[/dim]"
        )

    conn = init_db()
    checkpointer = create_checkpointer(conn)

    if fresh:
        thread_id = f"session-{uuid.uuid4().hex[:8]}"

    tid = create_session(conn, thread_id)
    config = {"configurable": {"thread_id": tid}}

    with console.status("[bold green]Loading agent..."):
        workflow = create_agent(model)
        agent = workflow.compile(checkpointer=checkpointer)

    display_welcome(model, tid, fresh)

    if verbose:
        print(
            f"[verbose] model={model} thread_id={tid} sessions_db={DB_PATH}",
            file=sys.stderr,
        )

    while True:
        try:
            user_input = get_user_input()

            if not user_input.strip():
                continue

            # Slash commands
            if user_input.startswith("/"):
                parts = user_input.strip().split()
                cmd = parts[0]
                args = parts[1:]

                if cmd == "/exit":
                    update_session(conn, tid)
                    console.print("[yellow]Session saved. Goodbye![/yellow]")
                    break

                if cmd == "/help":
                    display_help()
                    continue

                if cmd == "/save":
                    update_session(conn, tid)
                    console.print("[green]Session saved.[/green]")
                    continue

                if cmd == "/sessions":
                    sessions = list_sessions(conn)
                    display_sessions(sessions)
                    continue

                if cmd == "/handoff":
                    mode = "bypassPermissions" if "yolo" in args else "acceptEdits"
                    if mode == "bypassPermissions":
                        console.print(
                            "[red]⚠ YOLO mode: headless Claude will run with no permission gates.[/red]\n"
                            "[dim]Arbitrary Bash + file writes proceed without prompts.[/dim]"
                        )
                    if not confirm_handoff():
                        console.print("[yellow]Handoff cancelled.[/yellow]")
                        continue
                    console.print(f"[cyan]Handing off to Claude Code (mode={mode})...[/cyan]")
                    output = handoff_to_claude_code("coding-agent-repl-harness", ".", mode=mode)
                    if output:
                        console.print(Panel(output, title="Claude Code Output", border_style="cyan"))
                    continue

                console.print(f"[red]Unknown command: {cmd}[/red]")
                continue

            # Expand @file mentions
            expanded = expand_file_mentions(user_input)

            # Stream response with thinking spinner
            first = True
            turn_start = time.monotonic()
            with console.status("[green]Thinking…", spinner="dots") as status:
                for msg_chunk, metadata in agent.stream(
                    {"messages": [HumanMessage(content=expanded)]},
                    config,
                    stream_mode="messages",
                ):
                    if metadata.get("langgraph_node") != "agent":
                        continue
                    content = getattr(msg_chunk, "content", "")
                    if not content:
                        continue
                    if first:
                        status.stop()
                        console.print("\n[bold green]Agent:[/bold green] ", end="")
                        first = False
                    console.print(content, end="")
            if first:
                status.stop()
            console.print()

            if verbose:
                elapsed = time.monotonic() - turn_start
                print(f"[verbose] turn elapsed={elapsed:.2f}s", file=sys.stderr)

            update_session(conn, tid)

        except KeyboardInterrupt:
            console.print("\n[yellow]Session ended.[/yellow]")
            update_session(conn, tid)
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")


def main():
    parser = argparse.ArgumentParser(description="SDD Writer Harness")
    parser.add_argument(
        "--model",
        default="qwen3:14b",
        help="Ollama model to use (default: qwen3:14b)",
    )
    parser.add_argument(
        "--thread-id",
        default="default-session",
        help="Thread ID for session persistence (default: default-session)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start a fresh session with a new thread ID",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run preflight checks only",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print debug diagnostics (model, thread id, DB path, turn timing) to stderr",
    )

    args = parser.parse_args()

    if args.self_check:
        console.print("[cyan]Running preflight checks...[/cyan]")
        ok = preflight_check(args.model)
        if ok:
            console.print(f"[green]✓ Ollama up and {args.model} pulled[/green]")
            # End-to-end handoff probe: catches missing credits / auth without
            # waiting for a demo take to fail on camera.
            cc_ok, cc_msg = check_claude_code_working()
            if cc_ok:
                console.print(f"[green]✓ Claude Code handoff ready — {cc_msg}[/green]")
                console.print("[green]✓ All checks passed[/green]")
            else:
                console.print(f"[red]✗ Claude Code handoff will fail — {cc_msg}[/red]")
                console.print("[yellow]⚠ /handoff will fall back to manual instructions[/yellow]")
        return

    run_repl(args.model, args.thread_id, args.fresh, args.verbose)


if __name__ == "__main__":
    main()
