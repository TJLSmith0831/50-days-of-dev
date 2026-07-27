from typing import Literal

from pydantic import BaseModel

from src.models import Edge, Graph, Node


class TraversalPlan(BaseModel):
    start_nodes: list[str]
    relations: list[str]
    direction: Literal["inbound", "outbound"]


class TraversalResult(BaseModel):
    nodes: list[Node]
    path: list[Edge]


def traverse(graph: Graph, plan: TraversalPlan) -> TraversalResult:
    current_ids = plan.start_nodes
    nodes = [graph.nodes[node_id] for node_id in current_ids]
    path: list[Edge] = []

    for relation in plan.relations:
        next_ids: list[str] = []
        step_edges: list[Edge] = []
        for node_id in current_ids:
            matches = matching_edges(graph.edges, node_id, relation, plan.direction)
            for edge in matches:
                next_id = edge.target if plan.direction == "outbound" else edge.source
                if next_id not in next_ids:
                    next_ids.append(next_id)
                    step_edges.append(edge)
        # A relation with no matching edge from the current frontier is skipped,
        # not fatal. Breaking here threw the whole chain away whenever the
        # planner prefixed one speculative hop, which surfaces to the user as
        # "No grounded graph path found." even though the rest of the plan walks
        # fine. Skipping stays grounded: only edges that exist are followed.
        if not next_ids:
            continue
        path.extend(step_edges)
        nodes.extend(graph.nodes[node_id] for node_id in next_ids)
        current_ids = next_ids

    return TraversalResult(nodes=nodes, path=path)


def matching_edges(
    edges: list[Edge], node_id: str, relation: str, direction: str
) -> list[Edge]:
    if direction == "outbound":
        return [
            edge
            for edge in edges
            if edge.source == node_id and edge.relation == relation
        ]
    return [
        edge
        for edge in edges
        if edge.target == node_id and edge.relation == relation
    ]
