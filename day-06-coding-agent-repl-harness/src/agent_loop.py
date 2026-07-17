"""LangGraph-based agent loop with Ollama LLM and tool dispatch."""

from __future__ import annotations

from typing import Annotated, List

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing import TypedDict

from context_management import truncate_messages
from tools import ALL_TOOLS

SYSTEM_PROMPT = """\
You are a Spec Driven Design (SDD) writer harness. Your job: interview the user \
until you understand a change well enough to write a spec, then draft it.

Grilling is the default flow. Do NOT propose a spec until the design tree is \
resolved. Rules:

1. Ask ONE question at a time. Wait for the answer before asking the next. \
Multiple questions at once is bewildering.
2. For every question, state your recommended answer and one-line reason. \
Never ask "what do you want?" with no anchor.
3. If a question can be answered by exploring the codebase, use read_file / \
glob_files / grep_content instead of asking.
4. Walk one branch of the design tree at a time. Resolve dependencies before \
moving to the next branch.
5. Only draft the spec when there are no unresolved questions.
6. Be concise. Keep every reply under ~120 words; the final spec must fit on \
one screen (~25 lines).

You have read-only tools: read_file, glob_files, grep_content, web_search, \
openspec_cli. You CANNOT write or edit files. When the spec is ready, the \
user will hand off to Claude Code via /handoff.\
"""


class AgentState(TypedDict):
    """State for the SDD agent."""

    messages: Annotated[List[BaseMessage], add_messages]


def create_agent(model: str = "qwen3:14b"):
    """Create a LangGraph agent with tools and memory.

    :param model: Ollama model name
    :return: Compiled LangGraph agent (caller must supply checkpointer)
    """
    # ponytail: reasoning=False — qwen3 otherwise streams minutes of hidden
    # chain-of-thought before the first visible token (the "Thinking…" hang)
    llm = ChatOllama(model=model, temperature=0.1, reasoning=False)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def should_use_tools(state: AgentState) -> str:
        """Route to tools if the last message has tool calls.

        :param state: Current agent state
        :return: "tools" or END
        """
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    def call_model(state: AgentState):
        """Invoke the LLM with system prompt + conversation history.

        :param state: Current agent state
        :return: New response message
        """
        try:
            msgs, _ = truncate_messages(state["messages"])
            response = llm_with_tools.invoke(
                [SystemMessage(content=SYSTEM_PROMPT)] + msgs
            )
            return {"messages": [response]}
        except Exception as e:
            from langchain_core.messages import AIMessage

            return {"messages": [AIMessage(content=f"[Error: {e}]")]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_use_tools, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow
