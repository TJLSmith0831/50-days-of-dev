from src.llm import plan_question, synthesize_answer
from src.models import Edge, Graph, Link, Node
from src.traversal import TraversalPlan, TraversalResult


class FakeClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.last_prompt = ""
        self.models: list[str] = []
        self.formats: list[str | None] = []
        self.thinks: list[bool | None] = []

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format: str | None = None,
        think: bool | None = None,
    ) -> dict:
        self.last_prompt = messages[-1]["content"]
        self.models.append(model)
        self.formats.append(format)
        self.thinks.append(think)
        return {"message": {"content": self.content}}


def graph() -> Graph:
    return Graph(
        nodes={
            "job-queue": Node(
                id="job-queue",
                kind="component",
                body="Job runner.",
                links=[Link(relation="decided_by", target="adr-007")],
            ),
            "adr-007": Node(id="adr-007", kind="decision", body="Use Postgres.", links=[]),
            "hidden": Node(id="hidden", kind="incident", body="Do not disclose.", links=[]),
        },
        edges=[Edge(source="job-queue", relation="decided_by", target="adr-007")],
        relations={"decided_by": "governed by a decision"},
    )


def test_plan_question_accepts_known_graph_values() -> None:
    client = FakeClient(
        '{"start_nodes":["job-queue"],"relations":["decided_by"],"direction":"outbound"}'
    )

    plan = plan_question(client, "Why was Redis dropped?", graph())

    assert plan == TraversalPlan(
        start_nodes=["job-queue"], relations=["decided_by"], direction="outbound"
    )
    assert "Job runner." not in client.last_prompt
    assert client.models == ["qwen3:14b"]
    # The planner sees which relation each node actually has, so it never has to
    # guess a first hop — but still no note body.
    assert '"relation": "decided_by", "target": "adr-007"' in client.last_prompt
    # Qwen3's reasoning pass is off: the schema plus the links leave nothing to
    # reason out, and leaving it on costs ~2 minutes per question.
    assert client.thinks == [False]


def test_plan_question_rejects_unknown_model_values() -> None:
    client = FakeClient(
        '{"start_nodes":["unknown"],"relations":["made_up"],"direction":"sideways"}'
    )

    assert plan_question(client, "Anything", graph()) is None


def test_synthesize_answer_receives_only_traversed_note_content() -> None:
    client = FakeClient("Redis was replaced. [adr-007]")
    result = TraversalResult(
        nodes=[graph().nodes["job-queue"], graph().nodes["adr-007"]],
        path=[graph().edges[0]],
    )

    answer = synthesize_answer(client, "Why was Redis dropped?", result)

    assert answer == "Redis was replaced. [adr-007]"
    assert "Job runner." in client.last_prompt
    assert "Use Postgres." in client.last_prompt
    assert "Do not disclose." not in client.last_prompt
    assert client.models == ["mistral:latest"]
    assert client.formats == [None]
