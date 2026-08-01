"""Day 20 — RAG Scorecard: six deterministic evals over contract-clause RAG.

Commands: `ask <n>` runs one case live and shows the retrieved excerpts and every
score; `eval` runs the whole 250-case set with retrieval; `eval norag` runs the
identical cases with no retrieved text, which is the ablation that shows whether
retrieval is doing any work; `exit` quits.
"""

import statistics
import sys

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent import answer, client
from corpus import Corpus, load_cuad, short_question
from evals import score_all

METRICS = [
    "context_recall", "token_f1", "exact_match", "citation_fidelity", "abstention",
]


def run_case(case, corpus, oai, use_rag: bool):
    query = short_question(case)
    chunks = corpus.search(query, case.contract, oai) if use_rag else []
    ans = answer(query, case.contract, chunks, oai)
    return ans, chunks, score_all(ans, case, chunks)


def show_scores(console: Console, scores) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("eval")
    table.add_column("score", justify="right")
    table.add_column("detail", style="dim", overflow="fold")
    for s in scores:
        c = "green" if s.value >= 0.8 else "yellow" if s.value >= 0.5 else "red"
        table.add_row(s.name, f"[{c}]{s.value:.2f}[/{c}]", s.detail)
    console.print(table)


def run_ask(console: Console, cases, corpus, oai, n: int) -> None:
    case = cases[n % len(cases)]
    with console.status("retrieving + answering…"):
        ans, chunks, scores = run_case(case, corpus, oai, True)
    console.print(
        Panel(
            f"[bold]{short_question(case)}[/bold]\n"
            f"[dim]{case.contract[:70]}[/dim]\n\n"
            + (
                "[yellow]lawyers marked this clause ABSENT[/yellow]"
                if case.impossible
                else f"[green]gold:[/green] {case.gold_answers[0][:300]}"
            ),
            title=f"case {n} — {case.category}",
            border_style="yellow" if case.impossible else "green",
        )
    )
    for c in chunks:
        console.print(f"  [dim][#{c.chunk_id.rsplit('#', 1)[-1]:>3}] {c.text[:100].strip()}…[/dim]")
    verdict = "FOUND" if ans.found else "NOT PRESENT"
    console.print(
        Panel(
            f"[cyan]{verdict}[/cyan]\n\n{ans.answer[:400] or '—'}",
            border_style="cyan",
        )
    )
    show_scores(console, scores)


def run_eval(console: Console, cases, corpus, oai, use_rag: bool = True, limit: int = 0):
    # `limit` exists for the recorded demo: 250 cases is ~12 min of API calls,
    # which is not filmable. The subset is labelled as a subset on screen so the
    # numbers are never mistaken for the full run in README/BRIEF.
    if limit:
        cases = cases[:limit]
    mode = ("with retrieval" if use_rag else "NO retrieval (ablation)") + (
        f" — {limit}-case subset" if limit else "")
    rows = []
    # console.print, not console.status: the spinner is a live region that
    # renders nothing when stdout is not a tty, so a piped run showed no output
    # at all for the ~12 minutes 250 sequential calls take and looked hung.
    console.print(f"[dim]{mode}: {len(cases)} cases, ~{len(cases) * 3 // 60} min[/dim]")
    for i, case in enumerate(cases, 1):
        try:
            ans, chunks, scores = run_case(case, corpus, oai, use_rag)
        except Exception as exc:  # one bad case must not lose 249 others
            console.print(f"[red]{case.case_id}: {type(exc).__name__}: {exc}[/red]")
            continue
        rows.append((case, ans, scores))
        if i % 25 == 0 or i == len(cases):
            console.print(f"[dim]  {i}/{len(cases)}[/dim]")

    # `spread` earns its column: a mean of 1.00 can mean the system passed
    # everything, or that the metric says 1.00 whatever it is shown. The two are
    # indistinguishable from the mean alone, and the first version of this day
    # shipped six metrics that all read 1.00 for the second reason.
    agg = Table(title=f"scorecard — {mode}", show_header=True, header_style="bold")
    for col, just in (("eval", "left"), ("n", "right"), ("mean", "right"),
                      ("spread", "right"), ("", "left")):
        agg.add_column(col, justify=just, style="dim" if col == "" else None)
    for name in METRICS:
        vals = [s.value for _, _, ss in rows for s in ss if s.name == name]
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        spread = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        c = "green" if mean >= 0.8 else "yellow" if mean >= 0.5 else "red"
        note = "[red]no signal — never varied[/red]" if spread == 0 else ""
        agg.add_row(name, str(len(vals)), f"[{c}]{mean:.2f}[/{c}]", f"{spread:.3f}", note)
    console.print(agg)

    # Abstention split apart, because the aggregate hides the asymmetry that
    # matters: a system can score well overall by answering everything (perfect
    # on present clauses, catastrophic on absent ones) or by abstaining
    # everything. The two error directions have completely different fixes.
    present = [(c, a) for c, a, _ in rows if not c.impossible]
    absent = [(c, a) for c, a, _ in rows if c.impossible]
    split = Table(title="the hard half — abstention", show_header=True, header_style="bold")
    for col in ("lawyer says", "n", "model said found", "correct", "rate"):
        split.add_column(col, justify="right" if col != "lawyer says" else "left")
    for label, group, want_found in (
        ("clause IS present", present, True),
        ("clause is ABSENT", absent, False),
    ):
        if not group:
            continue
        found = sum(1 for _, a in group if a.found)
        ok = sum(1 for _, a in group if a.found == want_found)
        c = "green" if ok / len(group) >= 0.8 else "yellow" if ok / len(group) >= 0.5 else "red"
        split.add_row(label, str(len(group)), str(found), str(ok),
                      f"[{c}]{ok / len(group):.0%}[/{c}]")
    console.print(split)
    return rows


def compare(console: Console, with_rag, without_rag) -> None:
    """The headline. Everything else grades the pipeline; this asks whether the
    pipeline is worth having."""
    table = Table(title="does retrieval earn its place?", show_header=True, header_style="bold")
    for col in ("eval", "no retrieval", "with retrieval", "delta"):
        table.add_column(col, justify="right" if col != "eval" else "left")
    for name in METRICS:
        a = [s.value for _, _, ss in without_rag for s in ss if s.name == name]
        b = [s.value for _, _, ss in with_rag for s in ss if s.name == name]
        if not a or not b:
            continue
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        d = mb - ma
        c = "green" if d > 0.05 else "red" if d < -0.05 else "dim"
        table.add_row(name, f"{ma:.2f}", f"{mb:.2f}", f"[{c}]{d:+.2f}[/{c}]")
    console.print(table)


def main() -> None:
    load_dotenv()
    console = Console()
    oai = client()
    with console.status("loading CUAD + building index…"):
        chunks, cases = load_cuad()
        corpus = Corpus.build(chunks, oai)
    console.print(
        Panel(
            "[bold]Day 20 — RAG Scorecard[/bold]\n"
            "Contract-clause RAG over CUAD, and six deterministic evals over it.\n"
            f"[dim]{len({c.contract for c in chunks})} real contracts · "
            f"{len(chunks)} chunks · {len(cases)} lawyer-labelled questions "
            f"({sum(c.impossible for c in cases)} of them clauses that are ABSENT)[/dim]\n\n"
            "  [cyan]ask <n>[/cyan]      run one case, show excerpts + scores\n"
            "  [cyan]eval[/cyan]         all cases, with retrieval\n"
            "  [cyan]eval norag[/cyan]   same cases, no retrieved text\n"
            "  [cyan]eval 30[/cyan]      first 30 cases only (for demos)\n"
            "  [cyan]both[/cyan]         run each and print the delta\n"
            "  [cyan]exit[/cyan]",
            border_style="blue",
        )
    )
    while True:
        try:
            line = console.input("[bold blue]>[/bold blue] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        cmd, _, arg = line.partition(" ")
        try:
            if cmd in ("exit", "quit"):
                break
            elif cmd == "ask":
                run_ask(console, cases, corpus, oai, int(arg or 0))
            elif cmd == "eval":
                a = arg.strip().split()
                run_eval(console, cases, corpus, oai,
                         use_rag="norag" not in a,
                         limit=next((int(x) for x in a if x.isdigit()), 0))
            elif cmd == "both":
                a = run_eval(console, cases, corpus, oai, use_rag=False)
                b = run_eval(console, cases, corpus, oai, use_rag=True)
                compare(console, b, a)
            else:
                console.print("[yellow]ask <n> | eval | eval norag | both | exit[/yellow]")
        except Exception as exc:
            console.print(f"[red]{type(exc).__name__}: {exc}[/red]")
    console.print("[dim]bye[/dim]")


if __name__ == "__main__":
    main()
