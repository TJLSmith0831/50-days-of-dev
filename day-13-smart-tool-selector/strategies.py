"""The three tool-selection strategies (plus one control lane), behind one shape.

Every lane is `run(query) -> Result`: same catalog, same grading, same metrics.
Differences are in what tools the model can see when it decides.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from agents import Agent, RunHooks, Runner, ToolSearchTool, tool_namespace
from dotenv import load_dotenv
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import FastEmbedEncoder

from bench import CALL_CAP, Query, Result
from tools import BY_NAME, CATALOG

load_dotenv(Path(__file__).resolve().parent / ".env")

# DAY13_MODEL may carry a provider prefix (`openai:gpt-4.1-mini`); the Agents SDK
# wants the bare id.
MODEL = os.environ["DAY13_MODEL"].removeprefix("openai:")

# Confound, documented rather than hidden (spec: Implementation Decisions).
# `tool_search` is rejected by the Responses API on gpt-4.1-mini (and on gpt-5,
# gpt-5.1, and the nano tier); it is only served from gpt-5.2 up. The native lane
# therefore runs on a different, newer model than the other two. The `naive-ts`
# control lane re-runs the naive baseline on that same model so the native lane's
# numbers can be read against a same-model baseline instead of across two models.
TOOL_SEARCH_MODEL = os.environ.get("DAY13_TOOL_SEARCH_MODEL", "gpt-5.4-mini")

# Deliberately neutral: no "use exactly one tool" nudge. That instruction prompts
# the naive baseline out of the very thrashing the benchmark exists to measure,
# so tool discipline has to come from the strategy, not from the system prompt.
INSTRUCTIONS = (
    "You are the user's personal assistant. Handle the user's request using the "
    "tools available to you, then answer briefly."
)

# One Route per tool: 3 example utterances each. This is the habit the day is
# meant to establish — a new tool ships with its utterances, not just a docstring.
ROUTES = [
    Route(name="send_email", utterances=[
        "email marcus the notes",
        "let everyone know the deadline slipped",
        "send a message to the team about Friday",
    ]),
    Route(name="search_calendar", utterances=[
        "what's on my schedule tomorrow",
        "am I free Thursday afternoon",
        "when is my next meeting with Priya",
    ]),
    Route(name="create_calendar_event", utterances=[
        "book a meeting with Priya on Monday",
        "schedule a 30 minute call for next week",
        "put lunch on my calendar at noon",
    ]),
    Route(name="search_contacts", utterances=[
        "what's Marcus's email address",
        "look up Priya's phone number",
        "find me the dentist's contact details",
    ]),
    Route(name="set_reminder", utterances=[
        "remind me to take out the bins",
        "nudge me about the dentist tomorrow morning",
        "set a reminder to renew my passport",
    ]),
    Route(name="search_web", utterances=[
        "who won the world cup",
        "look up the latest news about AI regulation",
        "search the web for the tallest building",
    ]),
    Route(name="get_weather", utterances=[
        "what's the weather in Reykjavik",
        "is it going to rain tomorrow in Lisbon",
        "how hot is it in Austin right now",
    ]),
    Route(name="convert_currency", utterances=[
        "how much is 250 euros in yen",
        "convert 40 dollars to pounds",
        "what's the exchange rate from CHF to SEK",
    ]),
]

# Top-2 rather than top-1: a strict top-1 pre-filter would make the two ambiguous
# queries unanswerable by construction, which measures the ground truth, not the
# strategy.
ROUTER_TOP_K = 2


class Recorder(RunHooks):
    """Records the catalog tools called, in order; enforces the call cap; sums tokens."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tokens = 0
        self.capped = False

    async def on_tool_start(self, context, agent, tool) -> None:
        if tool.name not in BY_NAME:  # hosted tool_search calls aren't catalog calls
            return
        if len(self.calls) >= CALL_CAP:
            self.capped = True
            raise CapExceeded(f"exceeded {CALL_CAP}-call cap")
        self.calls.append(tool.name)

    async def on_llm_end(self, context, agent, response) -> None:
        if response.usage:
            self.tokens += response.usage.total_tokens


class CapExceeded(Exception):
    pass


def _build_router() -> SemanticRouter:
    """Local ONNX encoder, so the routing step costs no API key and no billable tokens."""
    return SemanticRouter(encoder=FastEmbedEncoder(), routes=ROUTES, auto_sync="local")


_router: SemanticRouter | None = None


def route(text: str) -> list[str]:
    global _router
    if _router is None:
        _router = _build_router()
    choices = _router(text=text, limit=ROUTER_TOP_K)
    # SemanticRouter returns a bare RouteChoice, not a list, when only one route
    # clears the similarity threshold.
    if not isinstance(choices, list):
        choices = [choices]
    return [c.name for c in choices if c.name]


async def _run(strategy: str, query: Query, agent: Agent) -> Result:
    hooks = Recorder()
    started = time.perf_counter()
    error = None
    try:
        await Runner.run(agent, query.text, max_turns=CALL_CAP + 2, hooks=hooks)
    except CapExceeded:
        pass
    except Exception as exc:  # benchmark script: record the failure, keep going
        error = f"{type(exc).__name__}: {exc}"[:120]
        hooks.capped = True
    return Result(
        strategy=strategy,
        query=query,
        calls=hooks.calls,
        latency_s=time.perf_counter() - started,
        tokens=hooks.tokens,
        capped=hooks.capped,
        error=error,
    )


def _agent(name: str, tools: list, model: str = MODEL) -> Agent:
    return Agent(name=name, instructions=INSTRUCTIONS, model=model, tools=tools)


async def run_naive(query: Query, model: str = MODEL) -> Result:
    """Strategy 1: all 8 tools bound, every call, no filtering."""
    return await _run("naive", query, _agent("naive", CATALOG, model))


async def run_router(query: Query) -> Result:
    """Strategy 2: local embedding pre-filter picks the routes; only those tools get bound.

    Routing happens inside the timed window — it is latency the user waits through
    even though it burns no billable tokens.
    """
    routing_start = time.perf_counter()
    matched = [n for n in route(query.text) if n in BY_NAME]
    routing_s = time.perf_counter() - routing_start
    result = await _run("router", query, _agent("router", [BY_NAME[n] for n in matched]))
    result.latency_s += routing_s
    result.routed = matched
    return result


async def run_native(query: Query) -> Result:
    """Strategy 3: OpenAI's hosted `tool_search` discovers tools from a namespace."""
    deferred = tool_namespace(
        name="assistant",
        description=(
            "Personal assistant tools: email, calendar, contacts, reminders, "
            "web search, weather, and currency conversion."
        ),
        tools=CATALOG,
    )
    # The namespace alone isn't enough — the API rejects `tool_search` unless at
    # least one tool is also marked deferred. tool_namespace() hands back copies,
    # so flipping this doesn't leak into the shared CATALOG the other lanes bind.
    for tool in deferred:
        tool.defer_loading = True
    agent = _agent("native", [ToolSearchTool(), *deferred], model=TOOL_SEARCH_MODEL)
    return await _run("native", query, agent)


async def run_naive_control(query: Query) -> Result:
    """Control lane: the naive baseline on the native lane's model, to isolate the confound."""
    result = await run_naive(query, model=TOOL_SEARCH_MODEL)
    result.strategy = "naive-ts"
    return result
