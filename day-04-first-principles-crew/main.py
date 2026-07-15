#!/usr/bin/env python
"""First-Principles Crew CLI: Skeptic -> Physicist -> Builder, REPL front end.

Crew wiring (agents/tasks/config) lives in crew.py + config/*.yaml.
"""

import datetime
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from crewai import Crew, Process, Task

from crew import FirstPrinciplesCrew, print_task_output
from models import (
    Assumption,
    AssumptionSet,
    Fundamental,
    FundamentalSet,
    Recommendation,
)

load_dotenv()
console = Console()

DEFAULT_PROBLEM = "Should we rebuild our legacy monolith as microservices?"
HELP = (
    "Type a follow-up to refine the recommendation.\n"
    "  drill <n or text>    challenge a fundamental, by number or a snippet of its wording\n"
    "  new <problem>        start over on a different problem\n"
    "  help                 show this again\n"
    "  exit / quit / Ctrl-D leave"
)

fp_crew = FirstPrinciplesCrew()


def metric_line(
    assumptions: AssumptionSet, fundamentals: FundamentalSet, elapsed: float
) -> str:
    m = sum(1 for a in assumptions.assumptions if a.questionable)
    n = len(fundamentals.fundamentals)
    return f"{m} assumptions challenged → {n} fundamentals → 1 recommendation in {elapsed:.1f}s (local llama3.2)."


def ollama_down_message(e: Exception) -> str | None:
    text = str(e)
    if "MTLLibraryErrorDomain" in text or "Connection" in text or "500" in text:
        return (
            "[red]Ollama isn't responding. Start it with `ollama serve` "
            "(or restart the Ollama app) and try again.[/red]"
        )
    return None


DECISIONS_FILE = Path(__file__).with_name("decisions.md")


def format_decision(state: dict, when: str) -> str:
    """Markdown block for one session: timestamp, problem, fundamentals, recommendation."""
    fundamentals = "\n".join(
        f"- {f.truth} ({f.basis})" for f in state["fundamentals"].fundamentals
    )
    rec = state["recommendation"]
    return (
        f"## {when} — {state['problem'].splitlines()[0]}\n\n"
        f"**Problem:** {state['problem']}\n\n"
        f"**Fundamentals:**\n{fundamentals}\n\n"
        f"**Recommendation:** {rec.recommendation}\n\n"
        "---\n\n"
    )


def append_decision(state: dict) -> None:
    """Append this session to the local decisions.md. Never crashes the REPL."""
    when = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        with open(DECISIONS_FILE, "a") as f:
            f.write(format_decision(state, when))
    except OSError as e:
        console.print(f"[yellow]Couldn't log to decisions.md ({e}).[/yellow]")


def run(problem: str):
    """Runs the full crew on `problem`. Returns {problem, assumptions, fundamentals, recommendation} or None."""
    console.print(Panel(problem, title="Problem", border_style="cyan"))

    start = time.perf_counter()
    try:
        result = fp_crew.crew().kickoff(inputs={"problem": problem})
    except Exception as e:
        console.print(
            ollama_down_message(e)
            or f"[red]Crew run failed ({e}); try again or rephrase.[/red]"
        )
        return None
    elapsed = time.perf_counter() - start

    assumptions = fp_crew.challenge_task().output.pydantic
    fundamentals = fp_crew.distill_task().output.pydantic
    recommendation = fp_crew.build_task().output.pydantic

    if assumptions is None or fundamentals is None or recommendation is None:
        console.print(
            "[red]Structured output parsing failed; showing raw result.[/red]"
        )
        console.print(result.raw)
        return None

    console.print(f"[bold]{metric_line(assumptions, fundamentals, elapsed)}[/bold]")

    state = {
        "problem": problem,
        "assumptions": assumptions,
        "fundamentals": fundamentals,
        "recommendation": recommendation,
    }
    append_decision(state)
    return state


def resolve_fundamental(
    fundamentals: FundamentalSet, arg: str
) -> tuple[int | None, list[int]]:
    """Resolve 'drill' arg to a 1-based index, by number or substring of the fundamental's wording.

    Returns (index, candidates): index is set only on an unambiguous match; otherwise
    candidates lists every 1-based match (empty if none) so the caller can report why.
    """
    if arg.isdigit():
        idx = int(arg)
        return (idx, []) if 1 <= idx <= len(fundamentals.fundamentals) else (None, [])
    matches = [
        i
        for i, f in enumerate(fundamentals.fundamentals, 1)
        if arg.lower() in f.truth.lower()
    ]
    return (matches[0], []) if len(matches) == 1 else (None, matches)


def drill_fundamental(
    fundamentals: FundamentalSet, idx: int, problem: str
) -> Fundamental | None:
    if idx < 1 or idx > len(fundamentals.fundamentals):
        return None
    target = fundamentals.fundamentals[idx - 1]
    drill_task = Task(
        description=(
            f"Problem: {problem}\n\nThe Physicist previously claimed this is an irreducible truth: "
            f"'{target.truth}' (basis: {target.basis}). Defend it under scrutiny, or revise it if it "
            "doesn't actually hold up."
        ),
        expected_output="A single revised (or reaffirmed) fundamental truth with its basis.",
        agent=fp_crew.physicist(),
        output_pydantic=Fundamental,
    )
    drill_crew = Crew(
        agents=[fp_crew.physicist()],
        tasks=[drill_task],
        process=Process.sequential,
        verbose=False,
        task_callback=print_task_output,
    )
    try:
        drill_crew.kickoff()
    except Exception as e:
        console.print(
            ollama_down_message(e) or f"[red]Drill failed ({e}); try again.[/red]"
        )
        return None
    return drill_task.output.pydantic


def repl(default_problem: str):
    console.print(
        Panel(HELP, title="First-Principles Crew — REPL", border_style="cyan")
    )

    state = None
    while state is None:
        try:
            problem = Prompt.ask("[cyan]Problem[/cyan]", default=default_problem)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[cyan]Goodbye.[/cyan]")
            return
        state = run(problem)

    while True:
        try:
            cmd = Prompt.ask("[cyan]>[/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[cyan]Goodbye.[/cyan]")
            return

        if cmd in ("exit", "quit"):
            console.print("[cyan]Goodbye.[/cyan]")
            return

        if cmd in ("help", "?"):
            console.print(Panel(HELP, title="Help", border_style="cyan"))
            continue

        if cmd.startswith("new "):
            new_state = run(cmd[len("new ") :].strip())
            if new_state is not None:
                state = new_state
            continue

        if cmd.startswith("drill "):
            arg = cmd[len("drill ") :].strip()
            if not arg:
                console.print("[red]Usage: drill <number or text>[/red]")
                continue
            idx, candidates = resolve_fundamental(state["fundamentals"], arg)
            if idx is None:
                if candidates:
                    listing = "\n".join(
                        f"  {i}. {state['fundamentals'].fundamentals[i - 1].truth}"
                        for i in candidates
                    )
                    console.print(f"[red]Ambiguous match for '{arg}':[/red]\n{listing}")
                else:
                    console.print(f"[red]No fundamental matches '{arg}'.[/red]")
                continue
            revised = drill_fundamental(state["fundamentals"], idx, state["problem"])
            if revised is None:
                console.print(f"[red]Drill on fundamental #{idx} failed.[/red]")
            continue

        if not cmd:
            continue

        # anything else is a free-text refinement
        new_state = run(f"{state['problem']}\n\nFollow-up: {cmd}")
        if new_state is not None:
            state = new_state


def main():
    default_problem = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROBLEM
    repl(default_problem)


def demo():
    """Self-check: metric_line counts questionable assumptions and fundamentals correctly."""
    assumptions = AssumptionSet(
        assumptions=[
            Assumption(statement="a", questionable=True, why="x"),
            Assumption(statement="b", questionable=False, why="y"),
            Assumption(statement="c", questionable=True, why="z"),
        ]
    )
    fundamentals = FundamentalSet(
        fundamentals=[
            Fundamental(truth="t1", basis="b1"),
            Fundamental(truth="t2", basis="b2"),
        ]
    )
    line = metric_line(assumptions, fundamentals, 1.0)
    assert (
        line
        == "2 assumptions challenged → 2 fundamentals → 1 recommendation in 1.0s (local llama3.2)."
    )

    state = {
        "problem": "Ship it?",
        "assumptions": assumptions,
        "fundamentals": fundamentals,
        "recommendation": Recommendation(recommendation="Yes", rests_on=["t1"]),
    }
    block = format_decision(state, "2026-07-15T12:00:00")
    assert block.startswith("## 2026-07-15T12:00:00 — Ship it?")
    assert "- t1 (b1)" in block and "- t2 (b2)" in block
    assert "**Recommendation:** Yes" in block

    print("demo() OK:", line)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        main()
