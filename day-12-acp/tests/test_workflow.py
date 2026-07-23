import asyncio
import pytest

from day12_acp import (
    MissingAgentError,
    build_stage_prompt,
    ensure_required_agents,
    extract_text_from_messages,
    format_pipeline_report,
    run_pipeline,
)


class FakePart:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeMessage:
    def __init__(self, *parts: str) -> None:
        self.parts = [FakePart(part) for part in parts]


class FakeRun:
    def __init__(self, text: str) -> None:
        self.output = [FakeMessage(text)]


class FakeManifest:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description


class FakeClient:
    def __init__(self) -> None:
        self.run_calls: list[tuple[str, list[str]]] = []

    async def agents(self):
        for manifest in [
            FakeManifest("researcher", "Finds source material"),
            FakeManifest("writer", "Drafts content"),
            FakeManifest("critic", "Reviews the draft"),
        ]:
            yield manifest

    async def run_sync(self, *, agent: str, payload: list[str] | None = None, **kwargs):
        if payload is None:
            payload = kwargs["input"]
        self.run_calls.append((agent, payload))
        outputs = {
            "researcher": "research notes",
            "writer": "draft article",
            "critic": "critique feedback",
        }
        return FakeRun(outputs[agent])


class FlakyClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.failures = {"writer": 1}

    async def run_sync(self, *, agent: str, payload: list[str] | None = None, **kwargs):
        if payload is None:
            payload = kwargs["input"]
        remaining_failures = self.failures.get(agent, 0)
        if remaining_failures:
            self.run_calls.append((agent, payload))
            self.failures[agent] = remaining_failures - 1
            raise RuntimeError(f"temporary failure in {agent}")
        return await super().run_sync(agent=agent, payload=payload)


def test_run_pipeline_discovers_agents_and_chains_outputs() -> None:
    client = FakeClient()
    events: list[tuple[str, str, str]] = []

    result = asyncio.run(
        run_pipeline(
            client,
            "research and write about quantum computing",
            event_sink=lambda kind, stage, text: events.append((kind, stage, text)),
            message_factory=lambda text: text,
        )
    )

    assert result.agent_names == ["researcher", "writer", "critic"]
    assert result.outputs["researcher"] == "research notes"
    assert result.outputs["writer"] == "draft article"
    assert result.outputs["critic"] == "critique feedback"
    assert client.run_calls[0] == (
        "researcher",
        [build_stage_prompt("researcher", "research and write about quantum computing")],
    )
    assert client.run_calls[1] == (
        "writer",
        [
            build_stage_prompt(
                "writer",
                "research and write about quantum computing",
                previous_output="research notes",
            )
        ],
    )
    assert client.run_calls[2] == (
        "critic",
        [
            build_stage_prompt(
                "critic",
                "research and write about quantum computing",
                previous_output="draft article",
            )
        ],
    )
    assert events == [
        ("stage_start", "researcher", ""),
        ("stage_complete", "researcher", "research notes"),
        ("stage_start", "writer", ""),
        ("stage_complete", "writer", "draft article"),
        ("stage_start", "critic", ""),
        ("stage_complete", "critic", "critique feedback"),
    ]


def test_run_pipeline_retries_once_after_transient_failure() -> None:
    client = FlakyClient()
    events: list[tuple[str, str, str]] = []

    result = asyncio.run(
        run_pipeline(
            client,
            "research and write about ACP",
            event_sink=lambda kind, stage, text: events.append((kind, stage, text)),
            message_factory=lambda text: text,
        )
    )

    assert result.outputs["writer"] == "draft article"
    assert [call[0] for call in client.run_calls].count("writer") == 2
    assert ("stage_error", "writer", "temporary failure in writer") in events


def test_run_pipeline_supports_custom_runner() -> None:
    client = object()
    calls: list[tuple[str, list[str]]] = []

    async def discover() -> list[FakeManifest]:
        return [
            FakeManifest("researcher"),
            FakeManifest("writer"),
            FakeManifest("critic"),
        ]

    async def runner(agent: str, payload: list[str]) -> FakeRun:
        calls.append((agent, payload))
        outputs = {
            "researcher": "notes",
            "writer": "draft",
            "critic": "review",
        }
        return FakeRun(outputs[agent])

    result = asyncio.run(
        run_pipeline(
            client,
            "research and write about ACP",
            message_factory=lambda text: text,
            agent_discoverer=discover,
            runner=runner,
        )
    )

    assert result.outputs == {
        "researcher": "notes",
        "writer": "draft",
        "critic": "review",
    }
    assert [agent for agent, _payload in calls] == ["researcher", "writer", "critic"]


def test_ensure_required_agents_raises_for_missing_agent() -> None:
    with pytest.raises(MissingAgentError) as exc:
        ensure_required_agents(["researcher", "writer"])

    assert "critic" in str(exc.value)


def test_extract_text_from_messages_concatenates_parts() -> None:
    messages = [FakeMessage("first", "second"), {"parts": [{"content": "third"}]}]

    assert extract_text_from_messages(messages) == "firstsecond\n\nthird"


def test_extract_text_from_messages_joins_streamed_token_parts() -> None:
    messages = [FakeMessage("Hello", "!", " Hope", " you're", " well")]

    assert extract_text_from_messages(messages) == "Hello! Hope you're well"


def test_format_pipeline_report_includes_each_stage() -> None:
    report = format_pipeline_report(
        user_request="research and write about ACP",
        outputs={
            "researcher": "notes",
            "writer": "draft",
            "critic": "review",
        },
    )

    assert "Request: research and write about ACP" in report
    assert "Researcher Output" in report
    assert "Writer Output" in report
    assert "Critic Output" in report
    assert "review" in report
