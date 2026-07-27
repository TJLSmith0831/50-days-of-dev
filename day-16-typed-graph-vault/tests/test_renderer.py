import math
from pathlib import Path

from src.models import Edge, Graph, Node
from src.renderer import ARROW_GAP, NODE_RADIUS, endpoints, render_graph


def graph() -> Graph:
    return Graph(
        nodes={
            "job-queue": Node(id="job-queue", kind="component", body="", links=[]),
            "adr-007": Node(id="adr-007", kind="decision", body="", links=[]),
        },
        edges=[Edge(source="job-queue", relation="decided_by", target="adr-007")],
        relations={"decided_by": "governed by a decision"},
    )


def test_render_graph_writes_standalone_svg_html(tmp_path: Path) -> None:
    output = render_graph(graph(), highlighted_path=[], output_path=tmp_path / "graph.html")

    html = output.read_text()
    assert "<svg" in html
    assert "job-queue" in html
    assert "decided_by" in html


def test_render_graph_marks_latest_traversal(tmp_path: Path) -> None:
    edge = graph().edges[0]

    html = render_graph(graph(), highlighted_path=[edge], output_path=tmp_path / "graph.html").read_text()

    assert 'class="edge highlighted"' in html
    # Highlighted edges get their own marker so the arrowhead matches the path
    # colour instead of the resting edge colour.
    assert 'marker-end="url(#arrow-hot)"' in html


def test_edges_stop_at_the_circle_rim_so_the_arrowhead_stays_visible() -> None:
    # A centre-to-centre line puts the arrowhead under the target node's fill,
    # which is drawn after the edges — the graph then reads as undirected.
    x1, y1, x2, y2 = endpoints((0, 0), (400, 0))

    assert (x1, y1) == (NODE_RADIUS, 0)
    assert x2 == 400 - NODE_RADIUS - ARROW_GAP
    assert math.isclose(y2, 0)


def test_endpoints_shortens_diagonal_edges_by_the_same_distance() -> None:
    x1, y1, x2, y2 = endpoints((100, 120), (320, 300))

    assert math.isclose(math.hypot(x1 - 100, y1 - 120), NODE_RADIUS)
    assert math.isclose(math.hypot(x2 - 320, y2 - 300), NODE_RADIUS + ARROW_GAP)
