from src.models import Edge, Graph, Node
from src.traversal import TraversalPlan, traverse


def graph() -> Graph:
    return Graph(
        nodes={
            "job-queue": Node(id="job-queue", kind="component", body="", links=[]),
            "adr-007": Node(id="adr-007", kind="decision", body="", links=[]),
            "adr-003": Node(id="adr-003", kind="decision", body="", links=[]),
        },
        edges=[
            Edge(source="job-queue", relation="decided_by", target="adr-007"),
            Edge(source="adr-007", relation="supersedes", target="adr-003"),
        ],
        relations={"decided_by": "", "supersedes": ""},
    )


def test_traverse_follows_requested_outbound_relations() -> None:
    result = traverse(
        graph(),
        TraversalPlan(
            start_nodes=["job-queue"],
            relations=["decided_by", "supersedes"],
            direction="outbound",
        ),
    )

    assert [node.id for node in result.nodes] == ["job-queue", "adr-007", "adr-003"]
    assert [edge.relation for edge in result.path] == ["decided_by", "supersedes"]


def test_traverse_skips_a_relation_with_no_edge_instead_of_abandoning_the_plan() -> None:
    # The planner sometimes prefixes a speculative hop. job-queue has no
    # depends_on edge, but the rest of the plan still walks the real chain.
    result = traverse(
        graph(),
        TraversalPlan(
            start_nodes=["job-queue"],
            relations=["depends_on", "decided_by", "supersedes"],
            direction="outbound",
        ),
    )

    assert [node.id for node in result.nodes] == ["job-queue", "adr-007", "adr-003"]
    assert [edge.relation for edge in result.path] == ["decided_by", "supersedes"]


def test_traverse_supports_inbound_edges() -> None:
    result = traverse(
        graph(),
        TraversalPlan(
            start_nodes=["adr-007"], relations=["decided_by"], direction="inbound"),
    )

    assert [node.id for node in result.nodes] == ["adr-007", "job-queue"]
