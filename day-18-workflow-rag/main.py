"""Day 18 — Workflow RAG: RAG over local markdown via a LlamaIndex Workflow.

Commands: `ingest <dir>` builds and persists the index, `query <text>`
runs the retrieve → synthesize steps and streams the intermediate events,
`exit` quits.
"""

import asyncio
import sys
import urllib.request
from pathlib import Path

from llama_index.core.workflow import StartEvent, StopEvent
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from rag_workflow import (
    DEFAULT_INDEX_DIR,
    IngestedEvent,
    RAGWorkflow,
    RetrievedEvent,
)
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

OLLAMA_URL = "http://localhost:11434"
DAY_DIR = Path(__file__).parent


def check_ollama(console: Console) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/version", timeout=2):
            return True
    except OSError:
        console.print(
            f"[red]Ollama is not reachable at {OLLAMA_URL}.[/red]\n"
            "Start it with [cyan]ollama serve[/cyan] and make sure "
            "[cyan]ollama pull llama3.2[/cyan] has been run."
        )
        return False


def format_event(console: Console, ev) -> None:
    if isinstance(ev, IngestedEvent):
        console.print(
            "  [yellow]→ IngestedEvent[/yellow] [dim]index loaded from disk, "
            "handing off to retrieve step[/dim]"
        )
    elif isinstance(ev, RetrievedEvent):
        console.print(
            f"  [yellow]→ RetrievedEvent[/yellow] [dim]{len(ev.nodes)} nodes[/dim]"
        )
        for i, node in enumerate(ev.nodes):
            source = Path(node.metadata.get("file_name", "unknown")).name
            preview = node.get_content()[:100].replace("\n", " ")
            console.print(
                f"    [dim][{i}][/dim] score={node.score:.3f} "
                f"[cyan]{source}[/cyan] [dim]{preview}…[/dim]"
            )


async def run_ingest(workflow: RAGWorkflow, dirname: str, console: Console) -> None:
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


async def run_query(workflow: RAGWorkflow, query: str, console: Console) -> None:
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
    console.print(
        Panel(
            result["answer"],
            title=f"[bold cyan]Q: {query}[/bold cyan]",
            border_style="cyan",
        )
    )


async def main() -> None:
    console = Console()
    if not check_ollama(console):
        sys.exit(1)

    with Status("[bold cyan]Loading models…[/bold cyan]", console=console):
        llm = Ollama(model="llama3.2", request_timeout=360.0, context_window=8000)
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    workflow = RAGWorkflow(llm=llm, embed_model=embed_model)
    indexed = DEFAULT_INDEX_DIR.is_dir()
    console.print(
        f"[bold green]Workflow RAG[/bold green]  "
        f"[dim]index: {'loaded on next query' if indexed else 'not built'}[/dim]\n"
        "  [cyan]ingest <dir>[/cyan]  — load markdown files and build the index\n"
        "  [cyan]query <text>[/cyan]  — ask a question (events stream as they flow)\n"
        "  [cyan]exit[/cyan]          — quit"
    )

    while True:
        try:
            user_input = console.input("\n[bold]❯ [/bold]").strip()
        except (EOFError, KeyboardInterrupt):
            break
        # The newline the terminal echoes on Enter is invisible to rich, so
        # Console still believes the cursor is on the prompt line. The Status
        # regions below clean up with ESC[1A ESC[2K ("up one, erase") and would
        # wipe the command that was just typed. This tells rich about the line
        # break it can't see.
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
                await run_query(workflow, arg, console)
        else:
            console.print("[red]Commands: ingest <dir>, query <text>, exit[/red]")

    console.print("[dim]Bye.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
