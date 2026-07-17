"""Rich-based terminal REPL with streaming display, slash commands, and @file expansion."""

from __future__ import annotations

import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

SLASH_COMMANDS = {
    "/help": "Show available commands",
    "/save": "Persist current session",
    "/sessions": "List available sessions",
    "/exit": "Exit the REPL",
    "/handoff": "Hand off to Claude Code (writes only). Append `yolo` for full autonomy: /handoff yolo",
}


def expand_file_mentions(text: str) -> str:
    """Expand @file mentions to absolute paths.

    :param text: User input text
    :return: Text with @file mentions expanded to absolute paths
    """
    def replace_match(m: re.Match) -> str:
        filename = m.group(1)
        path = Path(filename).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / filename
        if path.exists():
            return str(path)
        return m.group(0)

    return re.sub(r"@([\w./\-]+)", replace_match, text)


def display_tool_output(tool_name: str, output: str):
    """Display tool output in a Rich panel with syntax highlighting.

    :param tool_name: Name of the tool
    :param output: Tool output text
    """
    if tool_name in ("read_file",):
        syntax = Syntax(output, "python", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"tool: {tool_name}", border_style="cyan"))
    else:
        console.print(Panel(output, title=f"tool: {tool_name}", border_style="cyan"))


def display_help():
    """Display available slash commands."""
    table = Table(title="Slash Commands", border_style="blue")
    table.add_column("Command", style="bold cyan")
    table.add_column("Description")
    for cmd, desc in SLASH_COMMANDS.items():
        table.add_row(cmd, desc)
    console.print(table)


def display_sessions(sessions: list):
    """Display session list in a Rich table.

    :param sessions: List of session dicts
    """
    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return
    table = Table(title="Sessions", border_style="green")
    table.add_column("Thread ID", style="bold cyan")
    table.add_column("Created")
    table.add_column("Updated")
    for s in sessions:
        table.add_row(s["thread_id"], s["created_at"][:19], s["updated_at"][:19])
    console.print(table)


def display_welcome(model: str, thread_id: str, fresh: bool):
    """Display welcome panel on startup.

    :param model: Model name
    :param thread_id: Thread ID
    :param fresh: Whether this is a fresh session
    """
    console.print(
        Panel(
            f"[green]SDD Writer Harness[/green]\n\n"
            f"Model: {model}\n"
            f"Thread ID: {thread_id}\n"
            f"Memory: {'fresh' if fresh else 'resumed'}\n\n"
            "[yellow]Type /help for commands, /exit to quit[/yellow]",
            title="Session Started",
            border_style="green",
        )
    )


def get_user_input() -> str:
    """Get user input with blue speaker label.

    :return: User input string
    """
    return console.input("\n[bold blue]You:[/bold blue] ")


def confirm_handoff() -> bool:
    """Ask user to confirm Claude Code handoff.

    :return: True if confirmed
    """
    response = console.input("[yellow]Hand off to Claude Code? (y/N): [/yellow]")
    return response.lower().strip() in ("y", "yes")
