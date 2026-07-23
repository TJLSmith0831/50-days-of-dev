from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

REQUIRED_AGENTS = ("researcher", "writer", "critic")


class MissingAgentError(RuntimeError):
    pass


@dataclass(slots=True)
class PipelineResult:
    agent_names: list[str]
    outputs: dict[str, str]


def ensure_required_agents(agent_names: list[str]) -> list[str]:
    missing = [name for name in REQUIRED_AGENTS if name not in agent_names]
    if missing:
        raise MissingAgentError(
            f"Missing required ACP agents: {', '.join(missing)}"
        )
    return list(REQUIRED_AGENTS)


def build_stage_prompt(stage: str, user_request: str, previous_output: str | None = None) -> str:
    if stage == "researcher":
        return (
            "You are the researcher agent. Gather concise, current findings for this request: "
            f"{user_request}"
        )
    if stage == "writer":
        return (
            "You are the writer agent. Draft a readable response for the user request using this research:\n"
            f"Request: {user_request}\n"
            f"Research: {previous_output or ''}"
        )
    if stage == "critic":
        return (
            "You are the critic agent. Review the draft and suggest improvements.\n"
            f"Request: {user_request}\n"
            f"Draft: {previous_output or ''}"
        )
    raise ValueError(f"Unsupported stage: {stage}")


def extract_text_from_messages(messages: list[Any]) -> str:
    message_texts: list[str] = []
    for message in messages:
        parts = getattr(message, "parts", None)
        if parts is None and isinstance(message, dict):
            parts = message.get("parts", [])
        part_chunks: list[str] = []
        for part in parts or []:
            content = getattr(part, "content", None)
            if content is None and isinstance(part, dict):
                content = part.get("content")
            if content:
                part_chunks.append(str(content))
        # A single message's parts are streamed token fragments (e.g. "Hello", "!", " there")
        # that concatenate directly; separate messages are joined as paragraphs.
        message_texts.append("".join(part_chunks))
    return "\n\n".join(message_texts)


def format_pipeline_report(user_request: str, outputs: dict[str, str]) -> str:
    return "\n\n".join(
        [
            f"Request: {user_request}",
            f"Researcher Output\n{outputs.get('researcher', '')}",
            f"Writer Output\n{outputs.get('writer', '')}",
            f"Critic Output\n{outputs.get('critic', '')}",
        ]
    )


async def discover_agent_names(client: Any) -> list[str]:
    names: list[str] = []
    async for manifest in client.agents():
        names.append(manifest.name)
    return names


async def run_pipeline(
    client: Any,
    user_request: str,
    event_sink: Callable[[str, str, str], None] | None = None,
    message_factory: Callable[[str], Any] | None = None,
    agent_discoverer: Callable[[], Awaitable[list[Any]]] | None = None,
    runner: Callable[[str, list[Any]], Awaitable[Any]] | None = None,
) -> PipelineResult:
    if message_factory is None:
        def message_factory(text: str) -> str:
            return text

    if agent_discoverer is None:
        async def agent_discoverer() -> list[Any]:
            manifests: list[Any] = []
            async for manifest in client.agents():
                manifests.append(manifest)
            return manifests

    if runner is None:
        async def runner(agent: str, payload: list[Any]) -> Any:
            return await client.run_sync(agent=agent, input=payload)

    manifests = await agent_discoverer()
    agent_names = ensure_required_agents([manifest.name for manifest in manifests])
    outputs: dict[str, str] = {}

    for stage in agent_names:
        if event_sink is not None:
            event_sink("stage_start", stage, "")
        previous_output = None
        if stage == "writer":
            previous_output = outputs.get("researcher")
        elif stage == "critic":
            previous_output = outputs.get("writer")
        prompt = build_stage_prompt(stage, user_request, previous_output)
        payload = [message_factory(prompt)]
        try:
            run = await runner(stage, payload)
        except RuntimeError as exc:
            if event_sink is not None:
                event_sink("stage_error", stage, str(exc))
            run = await runner(stage, payload)
        text = extract_text_from_messages(run.output)
        outputs[stage] = text
        if event_sink is not None:
            event_sink("stage_complete", stage, text)

    return PipelineResult(agent_names=agent_names, outputs=outputs)
