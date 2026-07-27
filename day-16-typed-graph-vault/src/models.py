from pydantic import BaseModel


class Link(BaseModel):
    relation: str
    target: str


class Node(BaseModel):
    id: str
    kind: str
    body: str
    links: list[Link]


class Edge(BaseModel):
    source: str
    relation: str
    target: str


class Graph(BaseModel):
    nodes: dict[str, Node]
    edges: list[Edge]
    relations: dict[str, str]
