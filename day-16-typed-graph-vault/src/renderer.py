import math
from html import escape
from pathlib import Path

from src.models import Edge, Graph

NODE_RADIUS = 52
# The arrowhead has to clear the circle it points at, or the node fill (drawn
# after the edges) hides it and the graph reads as undirected — which is the one
# thing a typed graph must not do.
ARROW_GAP = 8


def endpoints(
    source: tuple[float, float], target: tuple[float, float]
) -> tuple[float, float, float, float]:
    """Shrink a centre-to-centre line back to the two circle rims."""
    dx, dy = target[0] - source[0], target[1] - source[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    return (
        source[0] + ux * NODE_RADIUS,
        source[1] + uy * NODE_RADIUS,
        target[0] - ux * (NODE_RADIUS + ARROW_GAP),
        target[1] - uy * (NODE_RADIUS + ARROW_GAP),
    )


def render_graph(graph: Graph, highlighted_path: list[Edge], output_path: Path) -> Path:
    highlighted = {(edge.source, edge.relation, edge.target) for edge in highlighted_path}
    positions = {node_id: (100 + index * 220, 120 + (index % 2) * 180) for index, node_id in enumerate(graph.nodes)}
    svg_edges = []
    for edge in graph.edges:
        is_hot = (edge.source, edge.relation, edge.target) in highlighted
        classes = "edge highlighted" if is_hot else "edge"
        # A separate marker per state: SVG markers do not inherit the line's
        # stroke in every browser, so the colour is baked into the marker.
        marker = "arrow-hot" if is_hot else "arrow"
        x1, y1, x2, y2 = endpoints(positions[edge.source], positions[edge.target])
        label_x = (x1 + x2) / 2
        label_y = (y1 + y2) / 2 - 10
        svg_edges.append(
            f'<line class="{classes}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" marker-end="url(#{marker})"/>'
            f'<text class="label" x="{label_x:.1f}" y="{label_y:.1f}">{escape(edge.relation)}</text>'
        )
    svg_nodes = [
        f'<g><circle class="node" cx="{x}" cy="{y}" r="{NODE_RADIUS}"/><text x="{x}" y="{y}">{escape(node_id)}</text></g>'
        for node_id, (x, y) in positions.items()
    ]
    markers = (
        '<marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">'
        '<polygon points="0 0, 10 3.5, 0 7" fill="#887799"/></marker>'
        '<marker id="arrow-hot" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto" markerUnits="strokeWidth">'
        '<polygon points="0 0, 7 2.5, 0 5" fill="#e35d3b"/></marker>'
    )
    html = f'''<!doctype html><html><head><style>
body{{font-family:system-ui;margin:0;padding:2rem}}svg{{width:100%;min-height:420px;border:1px solid #ddd}}.edge{{stroke:#879;stroke-width:2}}.highlighted{{stroke:#e35d3b;stroke-width:5}}.node{{fill:#eef5ff;stroke:#2563eb;stroke-width:2}}text{{text-anchor:middle;font-size:13px;fill:#182230}}.label{{paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round;font-weight:600}}
</style></head><body><h1>Typed Graph Vault</h1><svg viewBox="0 0 900 500"><defs>{markers}</defs>{''.join(svg_edges)}{''.join(svg_nodes)}</svg></body></html>'''
    output_path.write_text(html)
    return output_path
