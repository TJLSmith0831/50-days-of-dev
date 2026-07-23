from __future__ import annotations

import os
import sys
import traceback
from typing import Literal

from dotenv import load_dotenv
import uvicorn.config

if not hasattr(uvicorn.config, "LoopSetupType"):
    setattr(
        uvicorn.config,
        "LoopSetupType",
        Literal["none", "auto", "asyncio", "uvloop"],
    )

from beeai_framework.adapters.acp import ACPServer, ACPServerConfig
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.errors import FrameworkError
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.search.duckduckgo import DuckDuckGoSearchTool


load_dotenv()


def build_llm() -> ChatModel:
    return ChatModel.from_name(os.getenv("DAY12_MODEL", "openai:gpt-4.1-mini"))


def build_researcher() -> ReActAgent:
    return ReActAgent(
        llm=build_llm(),
        tools=[DuckDuckGoSearchTool()],
        memory=UnconstrainedMemory(),
    )


def build_writer() -> ReActAgent:
    return ReActAgent(
        llm=build_llm(),
        tools=[],
        memory=UnconstrainedMemory(),
    )


def build_critic() -> ReActAgent:
    return ReActAgent(
        llm=build_llm(),
        tools=[],
        memory=UnconstrainedMemory(),
    )


def main() -> None:
    server = ACPServer(
        config=ACPServerConfig(port=int(os.getenv("ACP_PORT", "8000")))
    )
    server.register(
        build_researcher(),
        name="researcher",
        description="Researches a topic with web search.",
        tags=["day-12", "research"],
    )
    server.register(
        build_writer(),
        name="writer",
        description="Drafts content from the research findings.",
        tags=["day-12", "writing"],
    )
    server.register(
        build_critic(),
        name="critic",
        description="Reviews a draft and suggests improvements.",
        tags=["day-12", "critique"],
    )
    server.serve()


if __name__ == "__main__":
    try:
        main()
    except FrameworkError as exc:
        traceback.print_exc()
        sys.exit(exc.explain())
