"""Day 19 — Agentic RAG: the agent decides whether to rewrite before retrieving.

Commands: `ingest <dir>` builds and persists the index, `query <text>` runs the
classify → (rewrite) → answer → judge workflow and streams the events, `exit`
quits and prints the session's raw-vs-rewritten score tally.
"""

import asyncio
import statistics
import sys
import urllib.request
from pathlib import Path

from llama_index.core.workflow import StartEvent, StopEvent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

from agentic_workflow import (
    DEFAULT_INDEX_DIR,
    AgenticRAGWorkflow,
    AnsweredEvent,
    ClassifiedEvent,
    RewrittenEvent,
)

OLLAMA_URL = "http://localhost:11434"
DAY_DIR = Path(__file__).parent
MODEL = "llama3.2"
JUDGE_MODEL = "qwen3:14b"


def check_ollama(console: Console) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/version", timeout=2):
            return True
    except OSError:
        console.print(
            f"[red]Ollama is not reachable at {OLLAMA_URL}.[/red]\n"
            "Start it with [cyan]ollama serve[/cyan] and make sure "
            f"[cyan]ollama pull {MODEL}[/cyan] and "
            f"[cyan]ollama pull {JUDGE_MODEL}[/cyan] have been run."
        )
        return False


def format_event(console: Console, ev) -> None:
    if isinstance(ev, ClassifiedEvent):
        verdict, color, tail = (
            ("VAGUE", "yellow", "rewriting, then answering both")
            if ev.is_vague
            else ("SPECIFIC", "green", "no rewrite — answering as typed")
        )
        console.print(
            f"  [yellow]→ ClassifiedEvent[/yellow] [{color}]{verdict}[/{color}] "
            f"[dim]{tail}[/dim]"
        )
    elif isinstance(ev, RewrittenEvent):
        console.print(
            f"  [yellow]→ RewrittenEvent[/yellow] [cyan]{ev.rewritten}[/cyan]"
        )
    elif isinstance(ev, AnsweredEvent):
        sources = ", ".join(
            Path(node.metadata.get("file_name", "?")).name for node in ev.nodes
        )
        console.print(
            f"  [yellow]→ AnsweredEvent[/yellow] [magenta]{ev.path}[/magenta] "
            f"[dim]{len(ev.nodes)} nodes: {sources}[/dim]"
        )


async def run_ingest(
    workflow: AgenticRAGWorkflow, dirname: str, console: Console
) -> None:
    path = Path(dirname).expanduser()
    if not path.is_absolute():
        path = (DAY_DIR / path).resolve()
    try:
        result = await workflow.run(dirname=str(path))
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return
    console.print(
        f"[green]Ingested {result['documents']} documents "
        f"({result['nodes']} nodes), persisted to {result['persisted_to']}[/green]"
    )


def render_result(console: Console, result: dict) -> None:
    paths = result["paths"]
    body = []
    if result["skipped_rewrite"]:
        body.append("[green]Already specific — no rewrite.[/green]\n")
    else:
        body.append(f"[dim]rewritten:[/dim] [cyan]{result['rewritten']}[/cyan]\n")
    for name in ("raw", "rewritten"):
        if name not in paths:
            continue
        entry = paths[name]
        body.append(
            f"[bold magenta]{name}[/bold magenta] "
            f"[bold]judge: {entry['score']}/5[/bold]\n{entry['answer']}\n"
        )
    console.print(
        Panel(
            "\n".join(body).strip(),
            title=f"[bold cyan]Q: {result['question']}[/bold cyan]",
            border_style="cyan",
        )
    )


async def run_query(
    workflow: AgenticRAGWorkflow, query: str, console: Console, tally: dict
) -> None:
    handler = workflow.run(query=query)
    try:
        async for ev in handler.stream_events():
            if not isinstance(ev, StartEvent | StopEvent):
                format_event(console, ev)
        result = await handler
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        handler.cancel()
        return
    except Exception as exc:  # noqa: BLE001 — deliberate: see below
        # Anything the workflow raises that isn't a usage error — most often
        # Ollama going away mid-run, which happened while recording the demo
        # when loading qwen3:14b next to llama3.2 exhausted memory and killed
        # the server. Letting it propagate ends the REPL and takes the session
        # tally with it, which is the one thing the run is for.
        console.print(f"[red]{type(exc).__name__}: {exc}[/red]")
        if not check_ollama(console):
            console.print("[red]Query abandoned — the tally is unchanged.[/red]")
        handler.cancel()
        return

    render_result(console, result)
    if result["skipped_rewrite"]:
        tally["skipped"].append(result["paths"]["raw"]["score"])
    else:
        for name, entry in result["paths"].items():
            tally[name].append(entry["score"])


def print_summary(console: Console, tally: dict) -> None:
    if not any(tally.values()):
        return
    table = Table(title="Session — judge scores (1-5)")
    table.add_column("bucket", style="cyan")
    table.add_column("queries", justify="right")
    table.add_column("avg score", justify="right")
    labels = {
        "raw": "raw query (vague)",
        "rewritten": "rewritten query",
        "skipped": "skipped — already clear",
    }
    for name, label in labels.items():
        scores = tally[name]
        avg = f"{statistics.mean(scores):.2f}" if scores else "—"
        table.add_row(label, str(len(scores)), avg)
    console.print(table)


async def main() -> None:
    console = Console()
    if not check_ollama(console):
        sys.exit(1)

    with Status("[bold cyan]Loading models…[/bold cyan]", console=console):
        # temperature=0 throughout. At Ollama's default, classify flips its
        # verdict between runs on the same query — it called "tell me about
        # evaluation" VAGUE and SPECIFIC on consecutive sessions — which makes
        # both the score tally and the recorded demo unreproducible.
        llm = Ollama(
            model=MODEL, request_timeout=360.0, context_window=8000, temperature=0
        )
        judge_llm = Ollama(
            model=JUDGE_MODEL,
            request_timeout=360.0,
            context_window=8000,
            temperature=0,
        )
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    workflow = AgenticRAGWorkflow(
        llm=llm, judge_llm=judge_llm, embed_model=embed_model, timeout=600
    )
    tally = {"raw": [], "rewritten": [], "skipped": []}
    indexed = DEFAULT_INDEX_DIR.is_dir()
    console.print(
        f"[bold green]Agentic RAG[/bold green]  "
        f"[dim]{MODEL} + {JUDGE_MODEL} judge · "
        f"index: {'loaded on next query' if indexed else 'not built'}[/dim]\n"
        "  [cyan]ingest <dir>[/cyan]  — load markdown files and build the index\n"
        "  [cyan]query <text>[/cyan]  — classify, rewrite if vague, answer both, judge\n"
        "  [cyan]exit[/cyan]          — quit and print the score tally"
    )

    while True:
        try:
            user_input = console.input("\n[bold]❯ [/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        # rich can't see the newline the terminal echoed on Enter, so the Status
        # regions below would erase the command that was just typed when they
        # clean up. Day 18 hit this; same fix.
        console.line()
        if not user_input:
            continue
        command, _, arg = user_input.partition(" ")
        command = command.lower()
        if command in {"exit", "quit"}:
            break
        if command == "ingest" and arg:
            with Status("[bold cyan]Ingesting…[/bold cyan]", console=console):
                await run_ingest(workflow, arg, console)
        elif command == "query" and arg:
            with Status("[bold cyan]Running workflow…[/bold cyan]", console=console):
                await run_query(workflow, arg, console, tally)
        else:
            console.print("[red]Commands: ingest <dir>, query <text>, exit[/red]")

    print_summary(console, tally)
    console.print("[dim]Bye.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
