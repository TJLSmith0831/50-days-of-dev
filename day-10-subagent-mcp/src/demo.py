"""Full workflow demo: advise -> research -> start_session -> code -> end_session.

Run with:
    PYTHONPATH=src uv run --no-project --with mcp --with ollama --with ddgs python src/demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TASK = "Build a CLI that greets the user by name using argparse."
SESSION_ID = "demo-greeting-cli"
HISTORY = """Turn 1: Followed the advisor's plan and wrote the argparse-based CLI directly.
Turn 2: Ran the CLI once, confirmed the greeting output, no rereads or backtracking."""


async def call(session: ClientSession, tool: str, **arguments: str) -> str:
    """Call an MCP tool and return its first text content block.

    :param session: Connected MCP client session.
    :param tool: Name of the tool to call.
    :param arguments: Keyword arguments to pass as the tool call's arguments.
    :return: The tool result's text.
    """
    result = await session.call_tool(tool, arguments)
    return result.content[0].text


async def main() -> None:
    """Spawn the subagent MCP server over stdio and run the full advise/research/session workflow."""
    src_dir = Path(__file__).resolve().parent
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(src_dir / "index.py")],
        env={"PYTHONPATH": str(src_dir)},
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            print(f"== advise: {TASK} ==")
            print(await call(session, "advise", task=TASK), "\n")

            print("== research: Python argparse greeting CLI best practices ==")
            print(
                await call(
                    session,
                    "research",
                    query="Python argparse greeting CLI best practices",
                ),
                "\n",
            )

            print(f"== start_session: {SESSION_ID} ==")
            print(await call(session, "start_session", session_id=SESSION_ID, goals=TASK), "\n")

            print("(...coding session happens here...)\n")

            print("== end_session ==")
            print(await call(session, "end_session", session_id=SESSION_ID, history=HISTORY), "\n")

    note_path = src_dir.parent / "critiques" / f"{SESSION_ID}.md"
    if note_path.exists():
        print("== critique note ==")
        print(note_path.read_text())
    else:
        print(f"critique note not found at {note_path}")


if __name__ == "__main__":
    asyncio.run(main())
