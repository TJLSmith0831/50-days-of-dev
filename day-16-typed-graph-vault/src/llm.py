import json
from typing import Any

from src.models import Graph
from src.traversal import TraversalPlan, TraversalResult

PLANNER_MODEL = "qwen3:14b"
ANSWER_MODEL = "mistral:latest"


def plan_question(client: Any, question: str, graph: Graph) -> TraversalPlan | None:
    # Each node carries its own outgoing links. Without them the planner knows
    # the relation vocabulary but not which node actually has which relation, so
    # it guesses — and a guessed first hop that matches no edge ends the
    # traversal with an empty path. Still IDs, kinds and relation names only:
    # no note body reaches the planner.
    catalog = [
        {
            "id": node.id,
            "kind": node.kind,
            "links": [{"relation": link.relation, "target": link.target} for link in node.links],
        }
        for node in graph.nodes.values()
    ]
    prompt = (
        "Map the question to a graph traversal. Return JSON only with start_nodes, "
        "relations, and direction. Use exact IDs and exact relation names from the "
        "catalog. relations is an ordered list and can contain multiple hops. Every "
        "relation must exist as an outgoing link on the node the hop starts from, so "
        "walk the links in the catalog and list the relations in the order they are "
        "actually traversed. direction "
        "must be inbound or outbound. Example: {\"start_nodes\":[\"job-queue\"],"
        "\"relations\":[\"decided_by\",\"supersedes\",\"caused_by\"],"
        "\"direction\":\"outbound\"}. "
        f"Question: {question}\nNodes: {json.dumps(catalog)}\n"
        f"Relations: {json.dumps(graph.relations)}"
    )
    content = chat_content(
        client,
        prompt,
        model=PLANNER_MODEL,
        response_format=TraversalPlan.model_json_schema(),
        # Qwen3 is a hybrid reasoning model: left on, it spends ~2 minutes
        # thinking before emitting a plan that the schema already constrains.
        # The catalog now contains the links, so there is nothing to reason out.
        think=False,
    )
    try:
        plan = TraversalPlan.model_validate_json(content)
    except ValueError:
        return None

    if (
        not plan.start_nodes
        or not plan.relations
        or any(node_id not in graph.nodes for node_id in plan.start_nodes)
        or any(relation not in graph.relations for relation in plan.relations)
    ):
        return None
    return plan


def synthesize_answer(client: Any, question: str, result: TraversalResult) -> str:
    notes = [
        {"id": node.id, "kind": node.kind, "body": node.body}
        for node in result.nodes
    ]
    path = [edge.model_dump() for edge in result.path]
    prompt = (
        "Answer only from the supplied notes. Cite each claim with note IDs in square "
        "brackets. If the notes are insufficient, say No grounded graph path found. "
        f"Question: {question}\nPath: {json.dumps(path)}\nNotes: {json.dumps(notes)}"
    )
    return chat_content(client, prompt, model=ANSWER_MODEL)


def chat_content(
    client: Any,
    prompt: str,
    *,
    model: str,
    response_format: str | dict[str, Any] | None = None,
    think: bool | None = None,
) -> str:
    request: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if response_format is not None:
        request["format"] = response_format
    if think is not None:
        request["think"] = think
    response = client.chat(**request)
    if isinstance(response, dict):
        return response["message"]["content"]
    return response.message.content or ""
