from pathlib import Path
import sys
import tempfile

from src.renderer import render_graph
from src.repl import ReplApp
from src.traversal import TraversalPlan, traverse
from src.vault import load_vault


def self_check() -> None:
    root = Path(__file__).parent
    graph = load_vault(root / "example-vault")
    result = traverse(
        graph,
        TraversalPlan(
            start_nodes=["job-queue"],
            relations=["decided_by", "supersedes", "caused_by"],
            direction="outbound",
        ),
    )
    assert len(result.nodes) == 4
    with tempfile.TemporaryDirectory() as directory:
        render_graph(graph, result.path, Path(directory) / "graph.html")
    print("self-check OK")


def main() -> None:
    ReplApp(Path(__file__).parent).run()


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
    else:
        main()
