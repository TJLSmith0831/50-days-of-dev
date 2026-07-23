from __future__ import annotations

import argparse
import asyncio
import os

from dotenv import load_dotenv

from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart, Run

from day12_acp import PipelineResult, format_pipeline_report, run_pipeline


load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover ACP agents and run the researcher -> writer -> critic pipeline."
    )
    parser.add_argument("request", help="Natural language request for the ACP workflow")
    return parser.parse_args()


def make_text_message(text: str) -> Message:
    return Message(parts=[MessagePart(content=text, content_type="text/plain")])


def print_event(kind: str, stage: str, text: str) -> None:
    if kind == "stage_start":
        print(f"\n[{stage}] starting...", flush=True)
        return
    if kind == "stage_error":
        print(f"[{stage}] retrying after error: {text}", flush=True)
        return
    print(f"[{stage}] {text}", flush=True)


async def list_agents(client: Client) -> list[str]:
    names: list[str] = []
    async for manifest in client.agents():
        names.append(manifest.name)
    return names


async def run_agent(client: Client, agent: str, payload: list[Message]) -> Run:
    input_messages = []
    for message in payload:
        message_dict = message.model_dump(mode="json")
        role = message_dict.get("role", "user")
        message_dict["parts"] = [
            {
                **part,
                "role": role,
            }
            for part in message_dict["parts"]
        ]
        input_messages.append(message_dict)

    response = await client.client.post(
        "/runs",
        json={
            "agent_name": agent,
            "input": input_messages,
            "mode": "sync",
        },
    )
    response.raise_for_status()
    return Run.model_validate(response.json())


async def run(request: str) -> PipelineResult:
    base_url = os.getenv("ACP_BASE_URL", "http://127.0.0.1:8000")
    async with Client(base_url=base_url) as client:
        discovered = await list_agents(client)
        print("Discovered agents:", ", ".join(discovered), flush=True)
        return await run_pipeline(
            client,
            request,
            event_sink=print_event,
            message_factory=make_text_message,
            runner=lambda agent, payload: run_agent(client, agent, payload),
        )


def main() -> None:
    args = parse_args()
    result = asyncio.run(run(args.request))
    print("\n=== Final Report ===\n", flush=True)
    print(format_pipeline_report(args.request, result.outputs), flush=True)


if __name__ == "__main__":
    main()
