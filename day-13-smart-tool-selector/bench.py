"""Ground truth, outcome grading, and report tabulation — all pure and offline.

This is the seam the self-check drives (`uv run demo.py`): no OpenAI, no network.
Vocabulary (Strategy, Primary tool, Acceptable set, Outcome, Call cap) is defined
in CONTEXT.md; the grading design is argued in docs/adr/0001.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CALL_CAP = 5

# Fixed by the spec. Kept here as a plain number so this module stays importable
# without pulling in the SDK — demo.py's self-check runs fully offline.
CATALOG_SIZE = 8

# `naive-ts` is not a fourth strategy — it is the naive baseline re-run on the
# native lane's model, so the forced model swap (see strategies.py) reads as a
# controlled difference rather than an unexplained one.
STRATEGIES = ("naive", "router", "native", "naive-ts")


@dataclass(frozen=True)
class Query:
    text: str
    primary: str
    acceptable: frozenset[str] = field(default=frozenset())

    def __post_init__(self) -> None:
        object.__setattr__(self, "acceptable", frozenset(self.acceptable) | {self.primary})


# 6 unambiguous (acceptable set == {primary}) + 2 deliberately ambiguous, per spec.
QUERIES = [
    Query("What's the weather like in Reykjavik right now?", "get_weather"),
    Query("How much is 250 euros in Japanese yen?", "convert_currency"),
    Query("What have I got on my calendar on Thursday?", "search_calendar"),
    Query("Put a 1:1 with Priya on my calendar for Monday at 10am", "create_calendar_event"),
    Query("What's Priya's email address?", "search_contacts"),
    Query("Who won the Tour de France this year?", "search_web"),
    Query("Remind me to call the dentist tomorrow morning", "set_reminder", {"create_calendar_event"}),
    Query("Let the team know the meeting moved to 3pm", "send_email", {"create_calendar_event"}),
]


@dataclass
class Result:
    strategy: str
    query: Query
    calls: list[str]
    latency_s: float
    tokens: int
    capped: bool = False
    error: str | None = None
    # Which tools the pre-filter bound before the model saw anything. Empty for
    # lanes that don't pre-filter — the whole catalog was visible.
    routed: list[str] = field(default_factory=list)

    @property
    def outcome(self) -> str:
        return grade(self.calls, self.query, self.capped)


def grade(calls: list[str], query: Query, capped: bool) -> str:
    """Grade one run. Precedence: land on the final tool first, then judge failure.

    Failed means the strategy never landed in the acceptable set *and* ran out of
    road (no tool at all, an exhausted call cap, or an errored run). Incorrect
    means it stopped on its own, confidently, on a tool outside the set.
    """
    if not calls:
        return "Failed"
    final = calls[-1]
    if final == query.primary:
        return "Precise"
    if final in query.acceptable:
        return "Acceptable"
    if capped and not any(c in query.acceptable for c in calls):
        return "Failed"
    return "Incorrect"


def render_table(results: list[Result]) -> str:
    """Per-query detail: every query × every strategy, in one skimmable block."""
    lines = [
        f"{'Query':<46} {'Strategy':<9} {'Outcome':<11} {'Calls':>5} {'Latency':>8} {'Tokens':>7}",
        "-" * 90,
    ]
    by_query: dict[str, list[Result]] = {}
    for r in results:
        by_query.setdefault(r.query.text, []).append(r)

    for text, rows in by_query.items():
        for i, r in enumerate(rows):
            label = (text[:43] + "...") if i == 0 and len(text) > 46 else (text if i == 0 else "")
            trail = "  " + " -> ".join(r.calls) if r.calls else "  (no tool called)"
            lines.append(
                f"{label:<46} {r.strategy:<9} {r.outcome:<11} {len(r.calls):>5} "
                f"{r.latency_s:>7.2f}s {r.tokens:>7}"
            )
            if r.routed:
                # The pre-filter's decision, made locally before any model call.
                lines.append(
                    f"{'':<46} {'':<9}   pre-filter: {CATALOG_SIZE} tools -> {', '.join(r.routed)}"
                )
            lines.append(f"{'':<46} {'':<9} {trail}")
        lines.append("")
    return "\n".join(lines)


def summarize(results: list[Result]) -> str:
    """Per-strategy roll-up: the actual answer to 'which strategy wins'."""
    lines = [
        f"{'Strategy':<9} {'Precise':>8} {'Accept':>7} {'Incorr':>7} {'Failed':>7} "
        f"{'AvgCalls':>9} {'AvgLat':>8} {'Tokens':>8}",
        "-" * 70,
    ]
    for s in STRATEGIES:
        rows = [r for r in results if r.strategy == s]
        if not rows:
            continue
        tally = {t: sum(r.outcome == t for r in rows) for t in ("Precise", "Acceptable", "Incorrect", "Failed")}
        lines.append(
            f"{s:<9} {tally['Precise']:>8} {tally['Acceptable']:>7} {tally['Incorrect']:>7} "
            f"{tally['Failed']:>7} {sum(len(r.calls) for r in rows) / len(rows):>9.2f} "
            f"{sum(r.latency_s for r in rows) / len(rows):>7.2f}s {sum(r.tokens for r in rows):>8}"
        )
    return "\n".join(lines)
