from pathlib import Path

import yaml
from pydantic import ValidationError

from src.models import Edge, Graph, Link, Node


class VaultValidationError(Exception):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


def load_vault(vault_dir: Path) -> Graph:
    schema = yaml.safe_load((vault_dir / "graph.yaml").read_text())
    relations = schema["relations"]
    nodes: dict[str, Node] = {}
    errors: list[str] = []

    for note_path in sorted(vault_dir.glob("*.md")):
        try:
            frontmatter, body = split_frontmatter(note_path.read_text())
            links = [Link.model_validate(link) for link in frontmatter["links"]]
            node = Node(
                id=frontmatter["id"],
                kind=frontmatter["kind"],
                body=body.strip(),
                links=links,
            )
        except (KeyError, TypeError, ValidationError, ValueError, yaml.YAMLError):
            errors.append("invalid frontmatter")
            continue

        if node.id in nodes:
            errors.append(f"duplicate node id: {node.id}")
            continue
        nodes[node.id] = node

    for node in nodes.values():
        for link in node.links:
            if link.relation not in relations:
                errors.append(f"unknown relation: {link.relation}")
            if link.target not in nodes:
                errors.append(f"unknown link target: {link.target}")

    if errors:
        raise VaultValidationError(errors)

    edges = [
        Edge(source=node.id, relation=link.relation, target=link.target)
        for node in nodes.values()
        for link in node.links
    ]
    return Graph(nodes=nodes, edges=edges, relations=relations)


def split_frontmatter(content: str) -> tuple[dict, str]:
    _, raw_frontmatter, body = content.split("---", 2)
    return yaml.safe_load(raw_frontmatter), body
