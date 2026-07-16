#!/usr/bin/env python3
"""Learning Chat Agent — conversational agent that adapts to user writing style across sessions using LangGraph memory and human-in-the-loop feedback."""

import argparse
import tempfile
import sqlite3
import uuid
from pathlib import Path
from typing import TypedDict, Annotated, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.panel import Panel

console = Console()


class AgentState(TypedDict):
    """State for the learning chat agent."""

    messages: Annotated[List[BaseMessage], add_messages]
    preferences: Annotated[List[str], "Learned user preferences"]
    sandbox_dir: Annotated[Optional[str], "Temporary directory for file operations"]


@tool
def write_file(content: str, filename: str) -> str:
    """Write content to a file in the sandbox directory.

    :param content: The content to write to the file
    :param filename: The name of the file to write
    :return: Success message with file path
    """
    import os
    sandbox = tempfile.gettempdir()
    
    # Ensure filename is just a name, not a path
    filename = os.path.basename(filename)
    if not filename or filename == '.':
        return "Error: Invalid filename provided"
    
    file_path = Path(sandbox) / filename
    file_path.write_text(content)
    return f"Written to {file_path}"


def create_learning_agent(model: str = "qwen3:14b"):
    """Create a LangGraph agent with memory and learning capabilities.

    :param model: Ollama model name
    :return: Compiled LangGraph agent
    """

    # Initialize Ollama LLM
    # tool_choice="auto" is required for qwen3:14b to enable native function calling
    llm = ChatOllama(model=model, temperature=0.1, tool_choice="auto")

    # Bind tools
    tools = [write_file]
    llm_with_tools = llm.bind_tools(tools)

    def should_use_tools(state: AgentState) -> str:
        """Determine if tools should be used.

        :param state: Current agent state
        :return: "tools" if tool calls present, END otherwise
        """
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    def call_model(state: AgentState):
        """Call the LLM with current state and preferences.

        :param state: Current agent state
        :return: New response message (add_messages reducer appends it)
        """
        preferences = state.get("preferences", [])

        system_prompt = "You are a helpful writing assistant. IMPORTANT: Only use the write_file tool when the user explicitly uses words like 'save', 'write to file', 'create file', or 'save to'. For all other questions including math, explanations, or general conversation, respond directly without calling any tools."
        if preferences:
            system_prompt += "\n\nUser preferences you have learned:\n"
            for pref in preferences:
                system_prompt += f"- {pref}\n"
            system_prompt += "\nApply these preferences to your responses."

        # System prompt is prepended per-call, not persisted in state
        response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + state["messages"])
        return {"messages": [response]}

    def extract_preference(state: AgentState):
        """Extract learning preferences from user feedback.

        :param state: Current agent state
        :return: Updated state with new preference if feedback detected
        """
        messages = state.get("messages", [])
        
        # Find the last HumanMessage in the conversation
        last_human = None
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_human = msg
                break
        
        if not last_human:
            return {}

        content = last_human.content.lower()

        # Check if this is feedback to learn from
        feedback_indicators = [
            "i prefer",
            "i like",
            "i want",
            "i'd rather",
            "too formal",
            "too casual",
            "too long",
            "too short",
            "don't use",
            "avoid",
            "never use",
            "always use",
        ]

        is_feedback = any(indicator in content for indicator in feedback_indicators)

        if is_feedback:
            # Store the feedback as a preference
            new_preferences = state.get("preferences", [])
            new_preferences.append(last_human.content)
            return {"preferences": new_preferences}

        # Return empty dict to preserve existing state
        return {}

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("extract_preference", extract_preference)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add edges - agent responds, then check for feedback
    workflow.add_conditional_edges(
        "agent", should_use_tools, {"tools": "tools", END: "extract_preference"}
    )
    workflow.add_edge("tools", "agent")
    workflow.add_edge("extract_preference", END)

    # Add memory - SqliteSaver provides file-based persistence across sessions
    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    memory = SqliteSaver(conn)

    return workflow.compile(checkpointer=memory)


def preflight_check(model: str) -> bool:
    """Check if Ollama is running and model is available.

    :param model: Ollama model name
    :return: True if available, False otherwise
    """
    try:
        llm = ChatOllama(model=model)
        llm.invoke("test")
        return True
    except Exception as e:
        console.print(
            Panel(
                f"[red]Ollama isn't responding.[/red] Start it with [cyan]ollama serve[/cyan] "
                f"and pull the model with [cyan]ollama pull {model}[/cyan].\n\n"
                f"[dim]{str(e)}[/dim]",
                title="Error",
                border_style="red",
            )
        )
        return False


def run_interactive_session(model: str, thread_id: str, fresh: bool = False):
    """Run an interactive chat session with the learning agent.

    :param model: Ollama model name
    :param thread_id: Thread ID for memory persistence
    :param fresh: Whether to clear memory before starting
    """

    if not preflight_check(model):
        return

    with console.status("[bold green]Loading agent..."):
        agent = create_learning_agent(model)

    console.print(
        Panel(
            f"[green]Learning Chat Agent[/green]\n\n"
            f"Model: {model}\n"
            f"Thread ID: {thread_id}\n"
            f"Memory: {'cleared' if fresh else 'persistent'}\n\n"
            "[yellow]Type 'quit' to exit, 'preferences' to see learned preferences[/yellow]",
            title="Session Started",
            border_style="green",
        )
    )

    # --fresh: use a new thread_id so no prior preferences are loaded
    if fresh:
        thread_id = f"{thread_id}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        try:
            user_input = console.input("\n[bold blue]You:[/bold blue] ")

            if user_input.lower() == "quit":
                console.print("[yellow]Session ended.[/yellow]")
                break

            if user_input.lower() == "preferences":
                state = agent.get_state(config)
                prefs = state.values.get("preferences", [])
                if prefs:
                    console.print("\n[bold]Learned preferences:[/bold]")
                    for i, pref in enumerate(prefs, 1):
                        console.print(f"  {i}. {pref}")
                else:
                    console.print("[yellow]No preferences learned yet.[/yellow]")
                continue

            prev_pref_count = len(agent.get_state(config).values.get("preferences", []))

            # Spinner while waiting for the first token, then stream tokens as they arrive
            first = True
            with console.status("[green]Thinking…", spinner="dots") as status:
                for msg_chunk, metadata in agent.stream(
                    {"messages": [HumanMessage(content=user_input)]},
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
            console.print()

            current_prefs = agent.get_state(config).values.get("preferences", [])
            if len(current_prefs) > prev_pref_count:
                console.print(f"\n[dim]✓ Preference learned: {current_prefs[-1]}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Session ended.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")


def main():
    parser = argparse.ArgumentParser(description="Learning Chat Agent")
    parser.add_argument(
        "--model",
        default="qwen3:14b",
        help="Ollama model to use (default: qwen3:14b)",
    )
    parser.add_argument(
        "--thread-id",
        default="default-user",
        help="Thread ID for memory persistence (default: default-user)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start with fresh memory (clears previous learning)",
    )
    parser.add_argument(
        "--self-check", action="store_true", help="Run preflight checks only"
    )

    args = parser.parse_args()

    if args.self_check:
        if preflight_check(args.model):
            console.print("[green]✓ Preflight checks passed[/green]")
        return

    run_interactive_session(args.model, args.thread_id, args.fresh)


if __name__ == "__main__":
    main()
