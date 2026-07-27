from pathlib import Path

from src.traversal import TraversalPlan, traverse
from src.vault import load_vault


def test_example_vault_has_causal_decision_path() -> None:
    project_root = Path(__file__).parent.parent
    graph = load_vault(project_root / "example-vault")

    result = traverse(
        graph,
        TraversalPlan(
            start_nodes=["job-queue"],
            relations=["decided_by", "supersedes", "caused_by"],
            direction="outbound",
        ),
    )

    assert [node.id for node in result.nodes] == [
        "job-queue",
        "adr-007-postgres-queue",
        "adr-003-redis-queue",
        "incident-2026-03-11",
    ]
