import re
import uuid
from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from ddgs import DDGS

console = Console()

DB_PATH = "gift_scout.db"
MAX_TOOL_CALLS = 8  # ~2 calls (search+commit) per pick, + slack
SHORTLIST_TARGET = 3


class GiftScoutState(TypedDict):
    """
    State for the Gift Scout AI shopping buddy.
    """

    recipient_profile: str
    interview_history: list[str]
    question_count: int
    directions: list[str]
    messages: Annotated[list, add_messages]
    shortlist: list[dict]
    tool_call_count: int
    top_picks: list[dict]


@tool
def web_search(query: str) -> str:
    """
    Search the web for gift candidates matching query.

    :param query: The search query
    :return: A string containing the search results
    """
    try:
        with console.status(f"[cyan]🔎 web_search({query!r})[/]"):
            results = DDGS().text(query, max_results=5)
        # compact lines, not a raw dict dump — a 3B model extracts from this far better
        return (
            "\n".join(
                f"- {r.get('title', '')} | {r.get('href', '')} | {r.get('body', '')[:150]}"
                for r in results
            )
            or "No results."
        )
    except Exception as e:
        console.print(f"[red]Error searching web: {e}[/]")
        return "Search failed. Please try again."


@tool
def add_to_shortlist(name: str, price: float, url: str) -> str:
    """
    Commit a candidate gift to the shortlist.

    :param name: The name of the gift
    :param price: The price of the gift
    :param url: The URL of the gift
    :return: A confirmation message
    """
    return f"Added {name} (${price}) to shortlist"


MAX_INTERVIEW_QUESTIONS = 3


def recipient_interview(state: GiftScoutState) -> dict:
    """
    Conduct an LLM-driven interview about the gift recipient.

    Asks up to 3 questions, generating follow-up questions based on
    previous answers. Uses interrupt() for human-in-the-loop input.

    :param state: The current GiftScoutState
    :return: The updated state with interview history and recipient profile
    """
    llm = ChatOllama(model="llama3.2")
    history = state.get("interview_history", [])
    count = state.get("question_count", 0)

    if count >= MAX_INTERVIEW_QUESTIONS:
        profile = _compile_profile(history)
        return {"recipient_profile": profile}

    if count == 0:
        question = "Who's the gift for? (e.g. my sister, my boss, a friend)"
    else:
        context = "\n".join(history)
        prompt = (
            f"You are interviewing someone about a gift recipient. "
            f"Here's what you know so far:\n{context}\n\n"
            f"Ask ONE short follow-up question to learn more about the recipient "
            f"(interests, age, budget, relationship, occasion, etc.). "
            f"Return only the question, nothing else."
        )
        with console.status("[cyan]💬 crafting follow-up question...[/]"):
            response = llm.invoke(prompt)
        question = str(response.content).strip()

    answer = interrupt({"question": question, "question_number": count + 1})
    answer = answer if answer else ""

    history = history + [f"Q: {question}\nA: {answer}"]
    count += 1

    if count >= MAX_INTERVIEW_QUESTIONS:
        profile = _compile_profile(history)
        return {
            "interview_history": history,
            "question_count": count,
            "recipient_profile": profile,
        }

    return {"interview_history": history, "question_count": count}


def _compile_profile(history: list[str]) -> str:
    """
    Compile interview Q&A history into a recipient profile string.

    :param history: List of 'Q: ...\nA: ...' strings
    :return: A summary string for use in brainstorming
    """
    llm = ChatOllama(model="llama3.2")
    context = "\n".join(history)
    prompt = (
        f"Summarize the following interview about a gift recipient into a "
        f"concise profile (1-2 sentences). Include name, age, interests, "
        f"budget, and any other relevant details mentioned.\n\n{context}"
    )
    with console.status("[cyan]📝 compiling recipient profile...[/]"):
        response = llm.invoke(prompt)
    return str(response.content).strip()


def brainstorm(state: GiftScoutState) -> dict:
    """
    Brainstorm directions for gift ideas.

    :param state: The current GiftScoutState
    :return: The updated state with brainstormed directions
    """
    llm = ChatOllama(model="llama3.2")

    prompt = f"Brainstorm 3 gift ideas for: {state['recipient_profile']}. Return as a simple list, one per line."
    with console.status("[cyan]💡 brainstorming directions...[/]"):
        response = llm.invoke(prompt)

    # strip any numbering/bullet (1. - * •) the model added itself
    lines = [
        re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line.strip())
        for line in str(response.content).split("\n")
    ]
    # prefer lines that aren't intro/outro headers, but never return nothing
    directions = [line for line in lines if line and not line.endswith(":")] or [
        line for line in lines if line
    ]

    return {"directions": directions[:3]}


def approval_gate(state: GiftScoutState) -> dict:
    """
    Get approval for the brainstormed directions.

    :param state: The current GiftScoutState
    :return: The updated state with approved directions
    """
    decision = interrupt(
        {
            "directions": state["directions"],
            "prompt": "approve or edit these directions",
        }
    )
    return {
        "directions": decision.get("directions", state["directions"])
        if decision
        else state["directions"]
    }


def agent(state: GiftScoutState) -> dict:
    """
    Make a tool call to search or add to shortlist.

    :param state: The current GiftScoutState
    :return: The updated state with tool call count incremented
    """
    llm = ChatOllama(model="llama3.2").bind_tools([web_search, add_to_shortlist])

    # ponytail: steer the 3B model turn by turn — the graph already knows whether
    # the next move is search or commit, so say it outright instead of hoping the
    # model invents the ReAct loop itself (it was committing 'null' prices).
    shortlist = state.get("shortlist", [])
    direction = state["directions"][len(shortlist) % len(state["directions"])]
    last = state["messages"][-1] if state["messages"] else None
    fresh_results = isinstance(last, ToolMessage) and last.name == "web_search"

    if fresh_results:
        instruction = (
            f"Web search results:\n{last.content}\n\n"
            f"Pick the single best product for '{direction}' and call add_to_shortlist "
            "with its name, its url from the results above, and price as a plain "
            "number like 24.99 (from the results, or your best realistic estimate)."
        )
    else:
        instruction = (
            f"Call web_search with a short shopping query (include a word like 'buy' "
            f"or 'price') to find a product for: {direction}"
        )

    system = (
        "system",
        "You are Gift Scout, an AI shopping buddy. Do exactly what the user asks, using tools.",
    )
    with console.status("[cyan]🛒 scout is deciding its next move...[/]"):
        # fresh, tiny context each turn — long histories confuse small models
        response = llm.invoke([system, ("user", instruction)])

    updates = {
        "messages": [response],
        "tool_call_count": state.get("tool_call_count", 0) + 1,
    }
    for call in response.tool_calls or []:
        if call["name"] == "add_to_shortlist":
            args = call["args"]
            # lenient: pull the first number out of whatever the model sends
            # ("$50", "50 USD", "1,299.00") instead of rejecting on a stray "$".
            match = re.search(
                r"\d+(\.\d+)?", str(args.get("price", "")).replace(",", "")
            )
            name = args.get("name")
            if not name or not match or any(i["name"] == name for i in shortlist):
                console.print(f"[yellow]agent:[/] skipping bad/duplicate call: {args}")
                continue
            url = args.get("url") or ""
            # small models often hallucinate or drop the URL — pull the real
            # one from the web_search ToolMessage by matching the item name
            if (not url or not url.startswith("http")) and fresh_results:
                for line in last.content.split("\n"):
                    parts = line.split(" | ")
                    if len(parts) >= 2 and name.lower() in parts[0].lower():
                        url = parts[1].strip()
                        break
            item = {
                "name": name,
                "price": float(match.group()),
                "url": url,
            }
            console.print(
                f"[green]➕ add_to_shortlist:[/] {name} (${item['price']:.2f})"
            )
            updates["shortlist"] = updates.get("shortlist", shortlist) + [item]

    return updates


def rank(state: GiftScoutState) -> dict:
    """
    Rank the shortlist and pick the top 3.

    :param state: The current GiftScoutState
    :return: The updated state with top picks
    """
    shortlist = state.get("shortlist", [])

    llm = ChatOllama(model="llama3.2")
    ranked = []

    for item in shortlist:
        prompt = (
            f"In one short sentence: why is '{item['name']}' (${item['price']}) a good "
            f"gift for {state['recipient_profile']}?"
        )
        with console.status(f"[cyan]🏆 ranking: {item['name']}...[/]"):
            why = llm.invoke(prompt).content
        ranked.append(
            {
                **item,
                "why_it_fits": str(why),
                "over_budget": item["price"] > 100,  # set budget threshold
            }
        )

    return {"top_picks": ranked[:SHORTLIST_TARGET]}


def route_after_agent(state: GiftScoutState) -> str:
    """
    Route to tools on a pending call, else rank — capped so a shaky small
    model can't loop forever without ever committing 3 items.

    :param state: The current GiftScoutState
    :return: The next node to visit
    """
    if (
        len(state.get("shortlist", [])) >= SHORTLIST_TARGET
        or state.get("tool_call_count", 0) >= MAX_TOOL_CALLS
    ):
        return "rank"
    # tool call -> run it; text-only -> nudge the model to try again (not rank),
    # so a shaky small model gets its full call budget instead of one shot.
    return "tools" if state["messages"][-1].tool_calls else "agent"


def route_after_interview(state: GiftScoutState) -> str:
    """
    Loop back for more interview questions until we hit the max,
    then proceed to brainstorm.

    :param state: The current GiftScoutState
    :return: The next node to visit
    """
    if state.get("question_count", 0) >= MAX_INTERVIEW_QUESTIONS:
        return "brainstorm"
    return "recipient_interview"


def build_graph(checkpointer):
    """
    Build the Gift Scout graph with all nodes and edges.

    :param checkpointer: The checkpointer to use for durable execution
    :return: The compiled graph
    """
    graph = StateGraph(GiftScoutState)
    graph.add_node("recipient_interview", recipient_interview)
    graph.add_node("brainstorm", brainstorm)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode([web_search, add_to_shortlist]))
    graph.add_node("rank", rank)

    graph.add_edge(START, "recipient_interview")
    graph.add_conditional_edges(
        "recipient_interview",
        route_after_interview,
        {"brainstorm": "brainstorm", "recipient_interview": "recipient_interview"},
    )
    graph.add_edge("brainstorm", "approval_gate")
    graph.add_edge("approval_gate", "agent")
    graph.add_conditional_edges(
        "agent", route_after_agent, {"tools": "tools", "agent": "agent", "rank": "rank"}
    )
    graph.add_edge("tools", "agent")
    graph.add_edge("rank", END)

    return graph.compile(checkpointer=checkpointer)


def main():
    with SqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app = build_graph(checkpointer)
        # Fresh thread per run so a stale checkpoint never replays old
        # output; kill-and-resume within one run still works (interrupt loop below
        # reuses this same config). To resume a specific crashed run instead,
        # hardcode its thread_id here.
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}

        console.print(
            Panel.fit(
                "🎁 [bold magenta]GIFT SCOUT[/] — your AI shopping buddy\n"
                "[dim]brainstorms → you approve → it shops → top 3 picks[/]",
                border_style="magenta",
            )
        )
        initial_state = {
            "recipient_profile": "",
            "interview_history": [],
            "question_count": 0,
            "directions": [],
            "messages": [],
            "shortlist": [],
            "tool_call_count": 0,
            "top_picks": [],
        }

        result = app.invoke(initial_state, config)
        while "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            if "question" in payload:
                console.print(
                    f"\n[bold cyan]Q{payload['question_number']}:[/] {payload['question']}"
                )
                answer = Prompt.ask("Your answer")
                result = app.invoke(Command(resume=answer), config)
            elif "directions" in payload:
                console.print("\n[bold cyan]Proposed gift directions:[/]")
                for i, d in enumerate(payload["directions"], 1):
                    console.print(f"  {i}. {d}")
                edit = Prompt.ask(
                    "Edit directions (comma-separated) or Enter to approve", default=""
                )
                if edit:
                    payload = {
                        **payload,
                        "directions": [d.strip() for d in edit.split(",") if d.strip()],
                    }
                result = app.invoke(Command(resume=payload), config)
            else:
                break

        if not result.get("top_picks"):
            console.print("[yellow]Scout came back empty-handed — try rerunning.[/]")
            return

        table = Table(title="Top Picks")
        for col in ("Name", "Price", "URL", "Why it fits", "Over budget"):
            table.add_column(col)
        for pick in result.get("top_picks", []):
            table.add_row(
                pick["name"],
                f"${pick['price']:.2f}",
                pick.get("url", "") or "—",
                pick["why_it_fits"],
                "🚩" if pick["over_budget"] else "",
            )
        console.print(table)


if __name__ == "__main__":
    main()
